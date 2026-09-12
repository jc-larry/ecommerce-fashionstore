from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional, Any
from datetime import datetime


def _normalize_email(value: Optional[str]) -> Optional[str]:
    """El correo es único e insensible a mayúsculas: se guarda y se busca en minúsculas.

    Evita el caso clásico de "registré Juan@Correo.com y no puedo iniciar sesión con
    juan@correo.com": el registro (web) y el inicio de sesión (móvil) deben coordinar.
    """
    if value is None:
        return None
    return value.strip().lower()


# --- Autenticación ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

    _norm_email = field_validator("email", mode="before")(_normalize_email)

class UserRegister(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None

    _norm_email = field_validator("email", mode="before")(_normalize_email)
    password: str = Field(
        ..., 
        min_length=8,
        description="La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
    )

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    is_active: bool
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    is_central: bool = False

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    roles: List[str]
    user: UserResponse

class UserRecover(BaseModel):
    email: EmailStr

    _norm_email = field_validator("email", mode="before")(_normalize_email)

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(
        ..., 
        min_length=8,
        description="La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
    )

# --- Administración de Usuarios y Roles ---
class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(
        ...,
        min_length=8,
        description="La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial."
    )
    role_names: List[str] = []

    _norm_email = field_validator("email", mode="before")(_normalize_email)

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role_names: Optional[List[str]] = None

    _norm_email = field_validator("email", mode="before")(_normalize_email)

class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    is_active: bool
    roles: List[RoleResponse]
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    is_central: bool = False

    class Config:
        from_attributes = True

# --- Auditoría ---
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    table_name: str
    row_id: int
    new_values: Optional[Any]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
