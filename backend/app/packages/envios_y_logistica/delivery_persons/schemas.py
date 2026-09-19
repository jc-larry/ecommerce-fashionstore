"""Esquemas Pydantic para Repartidores (Delivery Persons) - CU05, CU29, CU30."""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class DeliveryPersonBase(BaseModel):
    vehicle_type: str = Field("MOTO", description="MOTO, BICICLETA, AUTO, TORITO")
    vehicle_plate: Optional[str] = None
    license_number: Optional[str] = None
    coverage_zone: str = Field("Santa Cruz - Anillos 1 al 4", description="Zona principal de entrega")
    phone: str


class DeliveryPersonCreate(DeliveryPersonBase):
    user_id: int


class DeliveryPersonUpdate(BaseModel):
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None
    license_number: Optional[str] = None
    coverage_zone: Optional[str] = None
    phone: Optional[str] = None
    is_available: Optional[bool] = None


class DeliveryPersonResponse(DeliveryPersonBase):
    id: int
    user_id: int
    is_available: bool
    rating: float
    total_deliveries: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FailedDeliveryReport(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Motivo: Cliente ausente, Dirección incorrecta, etc.")


class RescheduleDeliveryRequest(BaseModel):
    new_delivery_date: date
    new_delivery_time: str = Field(..., description="Formato HH:MM o franja horaria")
    notes: Optional[str] = None


class DeliveryConfirmation(BaseModel):
    # Foto de evidencia comprimida en el dispositivo (data:image/jpeg;base64,...).
    photo_data_url: str = Field(..., min_length=100, description="Foto de la entrega como data URL de imagen")
    received_by_name: str = Field(..., min_length=2, max_length=100, description="Nombre de quien recibió el pedido")
    notes: Optional[str] = Field(None, max_length=255)


class DeliveryStatusUpdate(BaseModel):
    status: str = Field(..., description="PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED")
    notes: Optional[str] = None
