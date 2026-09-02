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
    avg_cost: float
    stock_minimo: int
    stock_maximo: int

    class Config:
        from_attributes = True


# --- CU37: Valoración de inventario / capital invertido ---
class InventoryValuationItem(BaseModel):
    branch_id: int
    variant_id: int
    sku: Optional[str] = None
    product_name: Optional[str] = None
    stock_actual: int
    avg_cost: float
    valor: float  # stock_actual * avg_cost (costo promedio ponderado)

    class Config:
        from_attributes = True

class InventoryValuationResponse(BaseModel):
    branch_id: Optional[int] = None  # None = valoración global (todas las sucursales)
    capital_invertido: float         # Σ (stock_actual * avg_cost)
    items: List[InventoryValuationItem]


# --- CU38: Ajustes de inventario (mermas, daños, pérdidas) ---
class InventoryAdjustmentCreate(BaseModel):
    branch_id: int
    variant_id: int
    quantity: int = Field(..., description="Negativo para merma/daño/pérdida; positivo para sobrante de conteo")
    reason: str = Field(..., pattern="^(MERMA|DANO|PERDIDA|CONTEO)$")
    note: Optional[str] = Field(None, max_length=255)

class InventoryAdjustmentResponse(BaseModel):
    ledger_id: int
    branch_id: int
    variant_id: int
    quantity: int
    reason: str
    unit_cost: float          # costo promedio ponderado vigente al momento del ajuste
    stock_resultante: int
    reference_id: str

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
