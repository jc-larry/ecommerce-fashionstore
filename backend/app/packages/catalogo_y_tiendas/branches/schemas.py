from pydantic import BaseModel, Field
from typing import Optional, List
# Importar response de usuario del paquete de Seguridad
from app.packages.seguridad_y_usuarios.schemas import UserDetailResponse

class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None

class BranchResponse(BranchBase):
    id: int
    employees: List[UserDetailResponse] = []

    class Config:
        from_attributes = True

class AssignEmployee(BaseModel):
    user_id: int
