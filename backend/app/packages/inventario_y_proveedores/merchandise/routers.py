from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db

from app.packages.inventario_y_proveedores.merchandise.models import PurchaseOrder, PurchaseDetail, Inventory, InventoryLedger
from app.packages.inventario_y_proveedores.merchandise.schemas import (
    PurchaseOrderCreate, PurchaseOrderResponse,
    InventoryResponse, InventoryLedgerResponse,
    InventoryValuationResponse, InventoryValuationItem,
    InventoryAdjustmentCreate, InventoryAdjustmentResponse,
)
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import Product, ProductVariant
from app.packages.inventario_y_proveedores.suppliers.models import Supplier
# Importar control de roles, usuario y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event

router = APIRouter(prefix="/api/v1/merchandise", tags=["merchandise"])

# Tanto SUPERADMIN como ENCARGADO pueden registrar compras e ingresos de stock (CU10)
staff_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO"])

@router.post("/intake", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def register_merchandise_intake(
    intake_data: PurchaseOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU10] Registra compras a proveedores e incrementa el stock físico de forma atómica (ACID)"""
    # [CU10 - Paso 3] / [DSC010 - Paso 3] +check_relations(proveedor_id, sucursal_id)
    # 1. Validar existencia del proveedor y de la sucursal
    supplier = db.query(Supplier).filter(Supplier.id == intake_data.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
        
    branch = db.query(Branch).filter(Branch.id == intake_data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    # 2. Registrar cabecera del ingreso
    # [CU10 - Paso 4] / [DSC010 - Paso 4] +insert_purchase(cabecera)
    purchase = PurchaseOrder(
        supplier_id=intake_data.supplier_id,
        branch_id=intake_data.branch_id,
        status="COMPLETADO"
    )
    db.add(purchase)
    db.flush()

    total_value = 0.0

    # 3. Procesar y persistir detalles e inventarios de manera transaccional
    for item in intake_data.details:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variante de producto con ID {item.variant_id} no encontrada.")

        # Crear fila de detalle de compra
        # [CU10 - Paso 5] / [DSC010 - Paso 5] +insert_detail(detalle)
        detail = PurchaseDetail(
            purchase_order_id=purchase.id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost
        )
        db.add(detail)
        total_value += (item.quantity * item.unit_cost)

        # Actualizar stock y COSTO PROMEDIO PONDERADO en la sucursal (CU10 / CU37)
        # [CU10 - Paso 6] / [DSC010 - Paso 6] +increment_stock(detalle)
        stock_record = db.query(Inventory).filter(
            Inventory.branch_id == purchase.branch_id,
            Inventory.variant_id == item.variant_id
        ).first()

        if not stock_record:
            # Primer ingreso: el costo promedio arranca en el costo del lote
            stock_record = Inventory(
                branch_id=purchase.branch_id,
                variant_id=item.variant_id,
                stock_actual=item.quantity,
                avg_cost=item.unit_cost,
                stock_minimo=5,
                stock_maximo=100
            )
            db.add(stock_record)
        else:
            # [CU10 - Paso 6b] / [DSC010] +update_avg_cost(variante)
            # Prorrateo: nuevo_avg = (stock_previo*avg_previo + cant*costo_lote) / (stock_previo + cant)
            stock_previo = stock_record.stock_actual
            avg_previo = float(stock_record.avg_cost or 0)
            nuevo_stock = stock_previo + item.quantity
            if nuevo_stock > 0:
                stock_record.avg_cost = round(
                    (stock_previo * avg_previo + item.quantity * item.unit_cost) / nuevo_stock, 2
                )
            stock_record.stock_actual = nuevo_stock

        # Registrar entrada en la bitácora física del libro de inventario (Inventory Ledger)
        ledger = InventoryLedger(
            branch_id=purchase.branch_id,
            variant_id=item.variant_id,
            quantity=item.quantity,
            movement_type="INGRESO",
            unit_cost=item.unit_cost,
            reference_id=f"OC-{purchase.id}"
        )
        db.add(ledger)

    db.commit()
    db.refresh(purchase)

    # Auditar el ingreso de mercadería en la bitácora general (CU36)
    log_event(
        db, current_user.id, "INSERT", "purchase_orders", purchase.id, 
        {"supplier_id": purchase.supplier_id, "branch_id": purchase.branch_id, "total_value": total_value}, 
        request.client.host
    )
    # [CU10 - Paso 7] / [DSC010 - Paso 7] +Ingreso Completado
    return purchase

@router.get("/inventory", response_model=List[InventoryResponse])
def get_inventory_levels(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU10] Consulta el stock de variantes actual global o por sucursal"""
    query = db.query(Inventory)
    if branch_id:
        query = query.filter(Inventory.branch_id == branch_id)
    return query.all()

@router.get("/ledger", response_model=List[InventoryLedgerResponse])
def get_inventory_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU10] Consulta el historial del libro diario de movimientos de inventario"""
    return db.query(InventoryLedger).order_by(InventoryLedger.created_at.desc()).all()


@router.get("/valuation", response_model=InventoryValuationResponse)
def get_inventory_valuation(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU37] Valoración del inventario / capital invertido por COSTO PROMEDIO PONDERADO.

    Capital invertido = Σ (stock_actual * avg_cost). Nunca se usa el último costo unitario.
    Ejemplo: 2 unidades compradas a 10 y a 14 -> avg_cost 12 -> valor 24 (no 28).
    """
    # [CU37 - Paso 3] / [DSC037 - Paso 3] +select_inventory(branch?)
    query = (
        db.query(Inventory, ProductVariant.sku, Product.name)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
    )
    if branch_id:
        query = query.filter(Inventory.branch_id == branch_id)

    items: List[InventoryValuationItem] = []
    capital = 0.0
    # [CU37 - Paso 4] / [DSC037 - Paso 4] +prorratear(costo_promedio)
    for inv, sku, product_name in query.all():
        avg = float(inv.avg_cost or 0)
        valor = round(inv.stock_actual * avg, 2)
        capital += valor
        items.append(InventoryValuationItem(
            branch_id=inv.branch_id,
            variant_id=inv.variant_id,
            sku=sku,
            product_name=product_name,
            stock_actual=inv.stock_actual,
            avg_cost=avg,
            valor=valor,
        ))

    # [CU37 - Paso 5] / [DSC037 - Paso 5] +Capital invertido
    return InventoryValuationResponse(
        branch_id=branch_id,
        capital_invertido=round(capital, 2),
        items=items,
    )


@router.post("/adjustments", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_201_CREATED)
def register_inventory_adjustment(
    data: InventoryAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check)
):
    """[CU38] Registra un ajuste de inventario (merma, daño, pérdida o sobrante de conteo).

    Descuenta/incrementa existencias y escribe un movimiento 'AJUSTE' en el libro mayor,
    valorado al costo promedio ponderado vigente. Las salidas NO alteran el costo promedio.
    """
    # [CU38 - Paso 3] / [DSC038 - Paso 3] +check_stock(variante, sucursal)
    if data.quantity == 0:
        raise HTTPException(status_code=400, detail="La cantidad del ajuste no puede ser cero.")

    stock_record = db.query(Inventory).filter(
        Inventory.branch_id == data.branch_id,
        Inventory.variant_id == data.variant_id
    ).first()
    if not stock_record:
        raise HTTPException(status_code=404, detail="No existe inventario para esa variante en la sucursal indicada.")

    if data.quantity < 0 and stock_record.stock_actual + data.quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para el ajuste (actual {stock_record.stock_actual}, ajuste {data.quantity})."
        )

    unit_cost = float(stock_record.avg_cost or 0)

    # [CU38 - Paso 4] / [DSC038 - Paso 4] +update_stock() + insert_ledger('AJUSTE')
    stock_record.stock_actual += data.quantity
    ledger = InventoryLedger(
        branch_id=data.branch_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
        movement_type="AJUSTE",
        unit_cost=unit_cost,
    )
    db.add(ledger)
    db.flush()
    ledger.reference_id = f"AJU-{ledger.id}"
    db.commit()
    db.refresh(ledger)

    # Auditar el ajuste en la bitácora general (CU36)
    log_event(
        db, current_user.id, "INSERT", "inventory_ledger", ledger.id,
        {"reason": data.reason, "quantity": data.quantity, "note": data.note,
         "branch_id": data.branch_id, "variant_id": data.variant_id},
        request.client.host
    )
    # [CU38 - Paso 5] / [DSC038 - Paso 5] +Ajuste registrado
    return InventoryAdjustmentResponse(
        ledger_id=ledger.id,
        branch_id=data.branch_id,
        variant_id=data.variant_id,
        quantity=data.quantity,
        reason=data.reason,
        unit_cost=unit_cost,
        stock_resultante=stock_record.stock_actual,
        reference_id=ledger.reference_id,
    )
