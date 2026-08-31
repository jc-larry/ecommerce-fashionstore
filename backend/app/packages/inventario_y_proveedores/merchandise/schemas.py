from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PurchaseDetailCreate(BaseModel):
    variant_id: int
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0.0)

class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    branch_id: int
    details: List[PurchaseDetailCreate]

class PurchaseDetailResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_cost: float

    class Config:
        from_attributes = True

class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    branch_id: int
    status: str
    created_at: datetime
    details: List[PurchaseDetailResponse]

    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    branch_id: int
    variant_id: int
    stock_actual: int
    stock_minimo: int
    stock_maximo: int

    class Config:
        from_attributes = True

class InventoryLedgerResponse(BaseModel):
    id: int
    branch_id: int
    variant_id: int
    quantity: int
    movement_type: str
    unit_cost: float
    reference_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
