from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db

from app.packages.inventario_y_proveedores.suppliers.models import Supplier, supplier_employees
from app.packages.inventario_y_proveedores.suppliers.schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse, SupplierContactUpdate, AssignSupplierUser,
)
from app.packages.inventario_y_proveedores.merchandise.models import PurchaseOrder, PurchaseDetail, Inventory
from app.packages.inventario_y_proveedores.merchandise.schemas import SupplierProductAvailability
from app.packages.catalogo_y_tiendas.models import Product, ProductVariant, Color, Size
from app.packages.catalogo_y_tiendas.branches.models import Branch
# Importar control de roles, usuario y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event, get_supplier_scope, SupplierScope

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

# Requiere rol SUPERADMIN para administrar proveedores (CU08)
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])
# Portal de autoservicio del proveedor: la ruta la puede pisar SUPERADMIN, pero
# get_supplier_scope es quien de verdad exige el rol PROVEEDOR y su vínculo.
supplier_check = RoleChecker(allowed_roles=["SUPERADMIN", "PROVEEDOR"])

@router.get("", response_model=List[SupplierResponse])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU08] Lista todos los proveedores registrados"""
    return db.query(Supplier).all()

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier_data: SupplierCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU08] Registra un nuevo proveedor de mercadería"""
    # [CU08 - Paso 3] / [DSC008 - Paso 3] +check_exists(nit)
    existing = db.query(Supplier).filter(Supplier.nit == supplier_data.nit).first()
    if existing:
        raise HTTPException(status_code=400, detail="El NIT del proveedor ya se encuentra registrado.")

    # [CU08 - Paso 4] / [DSC008 - Paso 4] +insert_supplier(datos)
    supplier = Supplier(**supplier_data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    # Auditar adición de proveedor (CU36)
    log_event(db, current_user.id, "INSERT", "suppliers", supplier.id, {"nit": supplier.nit, "name": supplier.name}, request.client.host)
    # [CU08 - Paso 6] / [DSC008 - Paso 6] +Proveedor Creado
    return supplier

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    supplier_data: SupplierUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU08] Modifica los datos de un proveedor de mercadería"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    old_vals = {"nit": supplier.nit, "name": supplier.name}

    for key, value in supplier_data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)

    # Auditar edición de proveedor (CU36)
    log_event(db, current_user.id, "UPDATE", "suppliers", supplier.id, {"old": old_vals, "new": {"nit": supplier.nit, "name": supplier.name}}, request.client.host)
    return supplier

@router.delete("/{supplier_id}", response_model=SupplierResponse)
def delete_supplier(
    supplier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU08] Desactiva lógicamente un proveedor preservando integridad y trazabilidad"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    supplier.is_active = False
    db.commit()
    db.refresh(supplier)

    # Auditar desactivación de proveedor (CU36)
    log_event(db, current_user.id, "DEACTIVATE", "suppliers", supplier_id, {"nit": supplier.nit, "name": supplier.name, "status": "INACTIVE"}, request.client.host)
    return supplier

@router.patch("/{supplier_id}/toggle", response_model=SupplierResponse)
def toggle_supplier_status(
    supplier_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU08] Alterna el estado activo/inactivo de un proveedor"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    supplier.is_active = not bool(supplier.is_active)
    db.commit()
    db.refresh(supplier)

    action = "ACTIVATE" if supplier.is_active else "DEACTIVATE"
    log_event(db, current_user.id, action, "suppliers", supplier_id, {"nit": supplier.nit, "name": supplier.name, "is_active": supplier.is_active}, request.client.host)
    return supplier


# ===================================================================
# Rol PROVEEDOR — vinculación de usuarios (SUPERADMIN)
# ===================================================================

@router.post("/{supplier_id}/users", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def assign_supplier_user(
    supplier_id: int,
    data: AssignSupplierUser,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """Vincula un usuario con rol PROVEEDOR a una ficha de proveedor (portal de autoservicio)."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    user = db.query(User).filter(User.id == data.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o inactivo.")
    if "PROVEEDOR" not in [r.name for r in user.roles]:
        raise HTTPException(status_code=400, detail="El usuario debe tener el rol PROVEEDOR para vincularlo a un proveedor.")
    if any(u.id == user.id for u in supplier.users):
        raise HTTPException(status_code=400, detail="Este usuario ya está vinculado a este proveedor.")

    supplier.users.append(user)
    db.commit()
    db.refresh(supplier)

    log_event(db, current_user.id, "INSERT", "supplier_employees", supplier.id, {"supplier_id": supplier.id, "user_id": user.id}, request.client.host)
    return supplier


@router.delete("/{supplier_id}/users/{user_id}", response_model=SupplierResponse)
def remove_supplier_user(
    supplier_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """Desvincula un usuario PROVEEDOR de una ficha de proveedor."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    user = next((u for u in supplier.users if u.id == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Ese usuario no está vinculado a este proveedor.")

    supplier.users.remove(user)
    db.commit()
    db.refresh(supplier)

    log_event(db, current_user.id, "DELETE", "supplier_employees", supplier.id, {"supplier_id": supplier.id, "user_id": user_id}, request.client.host)
    return supplier


# ===================================================================
# Rol PROVEEDOR — portal de autoservicio
# ===================================================================

@router.get("/me", response_model=SupplierResponse)
def get_my_supplier_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_check),
    scope: SupplierScope = Depends(get_supplier_scope),
):
    """[Rol PROVEEDOR] Ficha de contacto del proveedor propio."""
    supplier = db.query(Supplier).filter(Supplier.id == scope.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")
    return supplier


@router.put("/me", response_model=SupplierResponse)
def update_my_supplier_profile(
    data: SupplierContactUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_check),
    scope: SupplierScope = Depends(get_supplier_scope),
):
    """[Rol PROVEEDOR] Actualiza solo los datos de contacto propios (nunca NIT/nombre/categoría/estado)."""
    supplier = db.query(Supplier).filter(Supplier.id == scope.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado.")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)

    log_event(db, current_user.id, "UPDATE", "suppliers", supplier.id, {"contact_update": data.model_dump(exclude_unset=True)}, request.client.host)
    return supplier


@router.get("/me/products", response_model=List[SupplierProductAvailability])
def get_my_supplied_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_check),
    scope: SupplierScope = Depends(get_supplier_scope),
):
    """[Rol PROVEEDOR] Disponibilidad actual (solo lectura) de las variantes que este
    proveedor ha suministrado alguna vez, según el historial de compras. No expone
    costo promedio ni precio de venta — el proveedor solo ve que su prenda sigue
    disponible, nunca cifras comerciales internas de la tienda."""
    variant_ids_subq = (
        db.query(PurchaseDetail.variant_id)
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseDetail.purchase_order_id)
        .filter(PurchaseOrder.supplier_id == scope.supplier_id)
        .distinct()
        .subquery()
    )

    rows = (
        db.query(Inventory, ProductVariant, Product, Color, Size, Branch)
        .join(ProductVariant, ProductVariant.id == Inventory.variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .outerjoin(Color, Color.id == ProductVariant.color_id)
        .outerjoin(Size, Size.id == ProductVariant.size_id)
        .join(Branch, Branch.id == Inventory.branch_id)
        .filter(Inventory.variant_id.in_(db.query(variant_ids_subq)))
        .all()
    )

    return [
        SupplierProductAvailability(
            variant_id=inv.variant_id,
            sku=variant.sku,
            product_name=prod.name,
            color_name=color.name if color else "Estándar",
            size_name=size.name if size else "Única",
            branch_id=inv.branch_id,
            branch_name=branch.name,
            stock_actual=inv.stock_actual,
        )
        for inv, variant, prod, color, size, branch in rows
    ]
