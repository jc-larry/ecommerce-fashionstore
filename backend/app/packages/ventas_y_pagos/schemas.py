from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date


# ===================================================================
# CU17 — Carrito Digital
# ===================================================================

class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int = Field(1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=0)


class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    subtotal: float
    sku: str
    product_name: str
    size: str
    color: str
    image_url: Optional[str] = None
    stock_available: int


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    subtotal: float
    items_count: int


# ===================================================================
# CU18, CU19, CU20 — Checkout Polimórfico, POS y Facturación IVA 13%
# ===================================================================

class EfectivoPaymentData(BaseModel):
    cash_received: float = Field(..., gt=0)


class TarjetaPaymentData(BaseModel):
    card_brand: str = Field(..., min_length=2, max_length=20)
    card_last4: str = Field(..., min_length=4, max_length=4)
    gateway_reference: Optional[str] = None


class QRPaymentData(BaseModel):
    qr_reference: Optional[str] = None


class CreditoPaymentData(BaseModel):
    credit_due_date: date


class CheckoutRequest(BaseModel):
    branch_id: int
    channel: str = Field("ONLINE", pattern="^(ONLINE|POS)$")
    payment_type: str = Field(..., pattern="^(EFECTIVO|TARJETA|QR|CREDITO)$")
    coupon_code: Optional[str] = None
    cash_payment: Optional[EfectivoPaymentData] = None
    card_payment: Optional[TarjetaPaymentData] = None
    qr_payment: Optional[QRPaymentData] = None
    credit_payment: Optional[CreditoPaymentData] = None
    doc_type: str = Field("FACTURA", pattern="^(FACTURA|NOTA_ENTREGA)$")
    customer_nit: Optional[str] = None
    customer_name: Optional[str] = None
    cash_shift_id: Optional[int] = None
    pos_items: Optional[List[CartItemAdd]] = None


class OrderItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    subtotal: float
    product_name: str
    sku: str
    size: str
    color: str

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    id: int
    payment_type: str
    amount: float
    status: str
    paid_at: datetime
    cash_received: Optional[float] = None
    cash_change: Optional[float] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    qr_reference: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    doc_type: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    control_code: Optional[str] = None
    customer_nit: Optional[str] = None
    customer_name: Optional[str] = None
    issued_at: datetime
    qr_payload: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    channel: str
    status: str
    subtotal: float
    discount_amount: float
    coupon_code: Optional[str] = None
    total_amount: float
    created_at: datetime
    items: List[OrderItemResponse]
    payments: List[PaymentResponse]
    invoice: Optional[InvoiceResponse] = None

    class Config:
        from_attributes = True


# ===================================================================
# CU23 — Arqueo de Caja
# ===================================================================

class CashShiftOpen(BaseModel):
    branch_id: int
    opening_amount: float = Field(..., ge=0)


class CashShiftClose(BaseModel):
    closing_amount_declared: float = Field(..., ge=0)
    notes: Optional[str] = None


class CashShiftResponse(BaseModel):
    id: int
    cashier_id: int
    cashier_name: str
    branch_id: int
    branch_name: str
    opening_amount: float
    closing_amount_declared: Optional[float] = None
    closing_amount_system: Optional[float] = None
    difference: Optional[float] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    notes: Optional[str] = None
    total_sales_count: int = 0
    total_cash_sales: float = 0.0

    class Config:
        from_attributes = True


# ===================================================================
# CU21 — Cotización
# ===================================================================

class QuotationCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=150)
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    valid_days: int = Field(7, ge=1, le=60)
    details: List[CartItemAdd]


class QuotationResponse(BaseModel):
    id: int
    quotation_number: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    total_amount: float
    valid_until: datetime
    status: str
    created_at: datetime
    items: List[OrderItemResponse]
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None

    class Config:
        from_attributes = True


class QuotationConvertRequest(BaseModel):
    branch_id: int
    cash_shift_id: Optional[int] = None
    payment_method: str = "EFECTIVO"
    customer_nit: Optional[str] = "0"
    customer_business_name: Optional[str] = None


# ===================================================================
# CU22 — Devoluciones y Cambios
# ===================================================================

class OrderReturnItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(..., gt=0)
    replacement_variant_id: Optional[int] = None


class OrderReturnCreate(BaseModel):
    order_id: int
    return_type: str = Field(..., pattern="^(DEVOLUCION_DINERO|CAMBIO_PRENDA)$")
    reason: str = Field(..., min_length=3, max_length=255)
    items: List[OrderReturnItemCreate]


class OrderReturnResponse(BaseModel):
    id: int
    return_number: str
    order_id: int
    return_type: str
    reason: str
    refund_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
