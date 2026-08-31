from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db

from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.branches.schemas import BranchCreate, BranchUpdate, BranchResponse, AssignEmployee
# Importar control de roles, usuario y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event

router = APIRouter(prefix="/api/v1/branches", tags=["branches"])

# Requiere rol SUPERADMIN para administrar sucursales y empleados (CU06 / CU09)
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])

@router.get("", response_model=List[BranchResponse])
def list_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU06] Lista todas las sucursales de la cadena"""
    return db.query(Branch).all()

@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    branch_data: BranchCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU06] Registra una nueva sucursal física"""
    # [CU06 - Paso 3] / [DSC006 - Paso 3] +check_exists(nombre)
    existing = db.query(Branch).filter(Branch.name == branch_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de la sucursal ya existe.")
        
    # [CU06 - Paso 4] / [DSC006 - Paso 4] +insert_branch(datos)
    branch = Branch(**branch_data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)

    # Auditar creación de sucursal (CU36)
    log_event(db, current_user.id, "INSERT", "branches", branch.id, {"name": branch.name}, request.client.host)
    # [CU06 - Paso 6] / [DSC006 - Paso 6] +Sucursal Creada
    return branch

@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU06] Actualiza los datos de una sucursal existente"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    old_vals = {"name": branch.name, "is_active": branch.is_active}

    for key, value in branch_data.model_dump(exclude_unset=True).items():
        setattr(branch, key, value)

    db.commit()
    db.refresh(branch)

    # Auditar modificación (CU36)
    log_event(db, current_user.id, "UPDATE", "branches", branch.id, {"old": old_vals, "new": {"name": branch.name, "is_active": branch.is_active}}, request.client.host)
    return branch

@router.delete("/{branch_id}", response_model=BranchResponse)
def deactivate_branch(
    branch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU06] Realiza la baja lógica (desactivación) de una sucursal"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    branch.is_active = False
    db.commit()

    # Auditar desactivación (CU36)
    log_event(db, current_user.id, "UPDATE", "branches", branch.id, {"deactivated": True, "name": branch.name}, request.client.host)
    return branch

@router.post("/{branch_id}/employees", response_model=BranchResponse)
def assign_employee_to_branch(
    branch_id: int,
    assignment: AssignEmployee,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU09] Asigna un cajero o encargado a una sucursal física"""
    # [CU09 - Paso 3] / [DSC009 - Paso 3] +check_exists(sucursal_id, usuario_id)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    user = db.query(User).filter(User.id == assignment.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario empleado no encontrado.")

    roles = [r.name for r in user.roles]
    if "ENCARGADO" not in roles and "CAJERO" not in roles:
        raise HTTPException(status_code=400, detail="El usuario asignado debe ser ENCARGADO o CAJERO.")

    if user in branch.employees:
        raise HTTPException(status_code=400, detail="El empleado ya se encuentra asignado a esta sucursal.")
    # [CU09 - Paso 4] / [DSC009 - Paso 4] +insert_assign(sucursal_id, usuario_id)
    branch.employees.append(user)
    db.commit()
    db.refresh(branch)

    # Auditar asignación de empleado (CU36)
    log_event(db, current_user.id, "INSERT", "branch_employees", branch.id, {"employee_id": user.id, "role": roles}, request.client.host)
    # [CU09 - Paso 6] / [DSC009 - Paso 6] +Asignación Completada
    return branch

@router.delete("/{branch_id}/employees/{user_id}", response_model=BranchResponse)
def remove_employee_from_branch(
    branch_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU09] Retira la asignación de un empleado de una sucursal física"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user not in branch.employees:
        raise HTTPException(status_code=404, detail="El empleado no está asignado a esta sucursal.")

    branch.employees.remove(user)
    db.commit()
    db.refresh(branch)

    # Auditar remoción de empleado (CU36)
    log_event(db, current_user.id, "DELETE", "branch_employees", branch.id, {"employee_id": user.id}, request.client.host)
    return branch
