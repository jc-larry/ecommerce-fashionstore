from pydantic import BaseModel, Field
from typing import Optional

class SupplierBase(BaseModel):
    nit: str = Field(..., min_length=5, max_length=20)
    name: str = Field(..., min_length=2, max_length=150)
    category: Optional[str] = "Telas y Textiles"
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = True

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    nit: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class SupplierResponse(SupplierBase):
    id: int

    class Config:
        from_attributes = True
