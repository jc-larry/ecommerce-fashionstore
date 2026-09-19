"""Schemas Pydantic para el paquete Envíos y Logística."""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DeliveryZoneCreate(BaseModel):
    name: str = Field(..., max_length=100)
    city: str = Field(default="Santa Cruz", max_length=50)
    min_distance_km: float = Field(default=0.0, ge=0)
    max_distance_km: float = Field(..., gt=0)
    base_rate: float = Field(..., ge=0)
    estimated_hours: int = Field(default=24, ge=1)
    is_active: bool = True


class DeliveryZoneUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    min_distance_km: Optional[float] = None
    max_distance_km: Optional[float] = None
    base_rate: Optional[float] = None
    estimated_hours: Optional[int] = None
    is_active: Optional[bool] = None


class DeliveryZoneResponse(BaseModel):
    id: int
    name: str
    city: str
    min_distance_km: float
    max_distance_km: float
    base_rate: float
    estimated_hours: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DeliveryRateCalculateRequest(BaseModel):
    distance_km: float = Field(..., ge=0, description="Distancia estimada desde la sucursal de despacho")
    zone_id: Optional[int] = None


class DeliveryRateCalculateResponse(BaseModel):
    zone_id: Optional[int] = None
    zone_name: str
    rate: float
    estimated_hours: int
    distance_km: float


class ShipmentTrackingEventResponse(BaseModel):
    id: int
    status: str
    location: str
    description: str
    photo_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShipmentCreate(BaseModel):
    order_id: int
    zone_id: Optional[int] = None
    carrier_name: str = Field(default="Moto Express SCZ", max_length=100)
    carrier_phone: Optional[str] = Field(None, max_length=20)
    delivery_address: str = Field(..., max_length=255)
    recipient_name: str = Field(..., max_length=100)
    recipient_phone: str = Field(..., max_length=20)
    shipping_cost: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None


class ShipmentUpdateStatus(BaseModel):
    status: str = Field(..., description="DISPATCHED, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED")
    location: str = Field(default="En ruta", max_length=100)
    description: str = Field(..., max_length=255)


class ShipmentResponse(BaseModel):
    id: int
    tracking_number: str
    order_id: int
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    carrier_name: str
    carrier_phone: Optional[str] = None
    delivery_address: str
    recipient_name: str
    recipient_phone: str
    shipping_cost: float
    status: str
    dispatched_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Repartidor asignado y trazabilidad de tiempos
    delivery_person_id: Optional[int] = None
    delivery_person_name: Optional[str] = None
    claimed_at: Optional[datetime] = None
    delivery_date: Optional[date] = None
    delivery_time: Optional[str] = None
    delivery_attempts: int = 0
    failed_reason: Optional[str] = None
    # Evidencia de entrega
    delivery_photo_url: Optional[str] = None
    received_by_name: Optional[str] = None
    # Sucursal de origen (punto de recojo)
    origin_branch_id: Optional[int] = None
    origin_branch_name: Optional[str] = None
    origin_branch_address: Optional[str] = None
    origin_latitude: Optional[float] = None
    origin_longitude: Optional[float] = None
    events: List[ShipmentTrackingEventResponse] = []

    class Config:
        from_attributes = True
