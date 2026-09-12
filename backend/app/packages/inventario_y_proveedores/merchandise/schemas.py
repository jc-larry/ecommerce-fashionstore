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
    invoice_number: Optional[str] = Field(None, max_length=50)
    shipping_cost: Optional[float] = Field(0.0, ge=0.0)
    notes: Optional[str] = Field(None, max_length=255)
    details: List[PurchaseDetailCreate]

class PurchaseDetailResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_cost: float
    previous_avg_cost: Optional[float] = 0.0
    new_avg_cost: Optional[float] = 0.0

    class Config:
        from_attributes = True

class PurchaseOrderResponse(BaseModel):
    id: int
    supplier_id: int
    branch_id: int
    status: str
    invoice_number: Optional[str] = None
    shipping_cost: float = 0.0
    notes: Optional[str] = None
    total_amount: float = 0.0
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
    # Campos de exhibición (para POS/vitrina) — opcionales por compatibilidad.
    sku: Optional[str] = None
    product_name: Optional[str] = None
    color_name: Optional[str] = None
    size_name: Optional[str] = None
    image_url: Optional[str] = None
    sale_price: Optional[float] = None

    class Config:
        from_attributes = True


# --- Portal de Proveedor: disponibilidad de sus productos (solo lectura, sin costo/precio) ---
class SupplierProductAvailability(BaseModel):
    variant_id: int
    sku: Optional[str] = None
    product_name: Optional[str] = None
    color_name: Optional[str] = None
    size_name: Optional[str] = None
    branch_id: int
    branch_name: Optional[str] = None
    stock_actual: int


# --- CU37: Valoración de inventario / capital invertido ---
class InventoryValuationItem(BaseModel):
    branch_id: int
    branch_name: Optional[str] = None
    variant_id: int
    sku: Optional[str] = None
    product_name: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    size_name: Optional[str] = None
    image_url: Optional[str] = None
    stock_actual: int
    avg_cost: float
    valor: float  # stock_actual * avg_cost (costo promedio ponderado)
    sale_price: float = 0.0
    valor_venta: float = 0.0 # stock_actual * sale_price
    margen_bruto_unit: float = 0.0 # sale_price - avg_cost
    margen_bruto_percent: float = 0.0 # ((sale_price - avg_cost) / sale_price) * 100

    class Config:
        from_attributes = True

class InventoryValuationResponse(BaseModel):
    branch_id: Optional[int] = None  # None = valoración global (todas las sucursales)
    capital_invertido: float         # Σ (stock_actual * avg_cost)
    total_valor_venta: float = 0.0   # Σ (stock_actual * sale_price)
    utilidad_bruta_proyectada: float = 0.0 # total_valor_venta - capital_invertido
    margen_bruto_promedio_percent: float = 0.0 # (utilidad / total_valor_venta) * 100
    total_unidades: int = 0
    items: List[InventoryValuationItem]


# --- CU38: Ajustes de inventario (mermas, daños, pérdidas) ---
class InventoryAdjustmentCreate(BaseModel):
    branch_id: int
    variant_id: int
    quantity: int = Field(..., description="Negativo para merma/daño/pérdida; positivo para sobrante de conteo")
    reason: str = Field(..., pattern="^(MERMA|DANO|PERDIDA|CONTEO|MERMA_DEFECTO_FABRICA|MERMA_DANIO_TIENDA|MERMA_OBSOLESCENCIA|FALTANTE_INVENTARIO|SOBRANTE_INVENTARIO)$")
    note: Optional[str] = Field(None, max_length=255)

class InventoryAdjustmentResponse(BaseModel):
    ledger_id: int
    branch_id: int
    variant_id: int
    quantity: int
    reason: str
    reason_label: Optional[str] = None
    unit_cost: float          # costo promedio ponderado vigente al momento del ajuste
    financial_impact: float = 0.0 # Impacto financiero total en Bs (quantity * unit_cost)
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


# --- CU15: Transferencias entre sucursales ---
class StockTransferDetailCreate(BaseModel):
    variant_id: int
    quantity: int = Field(..., gt=0)

class StockTransferCreate(BaseModel):
    origin_branch_id: int
    destination_branch_id: int
    notes: Optional[str] = None
    details: List[StockTransferDetailCreate]

class StockTransferDetailResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    sku: Optional[str] = None
    product_name: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True

class StockTransferResponse(BaseModel):
    id: int
    transfer_number: str
    origin_branch_id: int
    origin_branch_name: str
    destination_branch_id: int
    destination_branch_name: str
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    details: List[StockTransferDetailResponse]

    class Config:
        from_attributes = True

class StockTransferStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(EN_TRANSITO|COMPLETADA|CANCELADA)$")
    notes: Optional[str] = None


# --- CU16: Alertas de Stock (Mínimo / Máximo) ---
class StockThresholdUpdate(BaseModel):
    stock_minimo: int = Field(..., ge=0)
    stock_maximo: int = Field(..., ge=1)

class StockAlertItem(BaseModel):
    branch_id: int
    branch_name: str
    variant_id: int
    product_name: str
    sku: str
    size: str
    color: str
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    alert_type: str  # 'QUIEBRE_STOCK' | 'SOBRESTOCK'
