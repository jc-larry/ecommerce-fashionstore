from pydantic import BaseModel, Field
from typing import Optional, List
# Importar response de usuario del paquete de Seguridad
from app.packages.seguridad_y_usuarios.schemas import UserDetailResponse

class BranchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: Optional[str] = None
    city: Optional[str] = "Santa Cruz"
    zone: Optional[str] = None
    address: str = Field(..., min_length=2, max_length=255)
    reference: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    opening_time: Optional[str] = "09:00"
    closing_time: Optional[str] = "21:00"
    days_open: Optional[str] = "Lunes a Sábado"
    has_fitting_room: Optional[bool] = True
    pickup_enabled: Optional[bool] = True
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = True

class BranchCreate(BranchBase):
    pass

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    city: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    reference: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    days_open: Optional[str] = None
    has_fitting_room: Optional[bool] = None
    pickup_enabled: Optional[bool] = None
    image_url: Optional[str] = None
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
