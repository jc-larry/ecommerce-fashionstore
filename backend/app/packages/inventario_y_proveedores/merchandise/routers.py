from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db

from app.packages.inventario_y_proveedores.merchandise.models import PurchaseOrder, PurchaseDetail, Inventory, InventoryLedger
from app.packages.inventario_y_proveedores.merchandise.schemas import (
    PurchaseOrderCreate, PurchaseOrderResponse, 
    InventoryResponse, InventoryLedgerResponse
)
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant
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

        # Actualizar stock en la sucursal (CU10)
        # [CU10 - Paso 6] / [DSC010 - Paso 6] +increment_stock(detalle)
        stock_record = db.query(Inventory).filter(
            Inventory.branch_id == purchase.branch_id,
            Inventory.variant_id == item.variant_id
        ).first()

        if not stock_record:
            stock_record = Inventory(
                branch_id=purchase.branch_id,
                variant_id=item.variant_id,
                stock_actual=item.quantity,
                stock_minimo=5,
                stock_maximo=100
            )
            db.add(stock_record)
        else:
            stock_record.stock_actual += item.quantity

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
