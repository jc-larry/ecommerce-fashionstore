from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db

from app.packages.inventario_y_proveedores.suppliers.models import Supplier
from app.packages.inventario_y_proveedores.suppliers.schemas import SupplierCreate, SupplierUpdate, SupplierResponse
# Importar control de roles, usuario y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])

# Requiere rol SUPERADMIN para administrar proveedores (CU08)
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])

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
