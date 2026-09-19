"""Schemas Pydantic para el paquete Reservas y Citas."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class ReservationItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(default=1, ge=1, le=3)
    notes: Optional[str] = None


class ReservationCreate(BaseModel):
    branch_id: int
    items: List[ReservationItemCreate] = Field(..., min_length=1, max_length=5)
    notes: Optional[str] = None
    appointment_date: Optional[date] = Field(None, description="Fecha agendada para acudir a la sucursal")
    appointment_time: Optional[str] = Field(None, description="Hora de la cita en formato HH:MM (ej: 10:30)")
    reserved_at: Optional[datetime] = None
    payment_method: Optional[str] = Field(default="TARJETA", description="TARJETA, PAYPAL, QR")
    payment_reference: Optional[str] = Field(default=None, description="ID de transacción o comprobante de pasarela")


class ReservationReschedule(BaseModel):
    new_date: date = Field(..., description="Nueva fecha de la cita")
    new_time: str = Field(..., description="Nueva hora de la cita en formato HH:MM")
    reason: Optional[str] = None


class ReservationStatusUpdate(BaseModel):
    status: str = Field(..., description="PENDING, PREPARING, READY, LATE, NO_SHOW, COMPLETED, CANCELLED, EXPIRED")


class ReservationConvertToPOSRequest(BaseModel):
    cash_shift_id: int = Field(..., description="Turno de caja ABIERTO del cajero en la sucursal de la reserva")
    payment_method: str = Field(default="EFECTIVO", description="EFECTIVO, TARJETA o QR (cobro del saldo en caja)")
    cash_received: Optional[float] = Field(None, ge=0, description="Efectivo recibido (solo EFECTIVO) para calcular el cambio")
    card_brand: Optional[str] = Field(None, max_length=20)
    card_last4: Optional[str] = Field(None, min_length=4, max_length=4)
    payment_reference: Optional[str] = Field(None, max_length=100, description="N° de voucher POS o referencia del QR")
    nit_ruc: Optional[str] = "0"
    business_name: Optional[str] = "SIN NOMBRE"
    selected_item_ids: Optional[List[int]] = Field(
        default=None,
        description="IDs de ReservationItem que el cliente efectivamente compra. Las prendas no marcadas se reponen inmediatamente al inventario disponible de la sucursal."
    )


class ReservationItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    unit_price: float
    notes: Optional[str] = None
    product_name: Optional[str] = None
    size_name: Optional[str] = None
    color_name: Optional[str] = None
    sku: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ReservationResponse(BaseModel):
    id: int
    reservation_code: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    branch_id: int
    branch_name: Optional[str] = None
    branch_address: Optional[str] = None
    status: str
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    reschedule_count: int = 0
    reserved_at: datetime
    expires_at: datetime
    notes: Optional[str] = None
    total_amount: float = 0.0
    deposit_amount: float = 0.0
    balance_due: float = 0.0
    payment_method: Optional[str] = "TARJETA"
    payment_reference: Optional[str] = None
    deposit_paid: bool = True
    completed_sale_id: Optional[int] = None
    items: List[ReservationItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True

