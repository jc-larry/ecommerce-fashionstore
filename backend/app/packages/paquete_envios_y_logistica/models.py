"""Modelos del paquete Envíos y Logística (CU29, CU30, CU31).

Maneja zonas de entrega por anillos/km, generación de guías de despacho,
asignación de transportistas y trazabilidad en tiempo real con hitos de tracking.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Date, func, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.paquete_ventas_y_pagos.models import Order
from app.packages.paquete_envios_y_logistica.delivery_persons.models import DeliveryPerson


class DeliveryZone(Base):
    """[CU31] Zona y tarifa de entrega por anillos y kilometraje."""
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), default="Santa Cruz", nullable=False)
    min_distance_km: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0, nullable=False)
    max_distance_km: Mapped[float] = mapped_column(Numeric(5, 2), default=5.0, nullable=False)
    base_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=15.0, nullable=False)  # En Bs.
    estimated_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Shipment(Base):
    """[CU29, CU30] Despacho y trazabilidad logística de pedidos."""
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    zone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("delivery_zones.id", ondelete="SET NULL"), nullable=True)
    delivery_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("delivery_persons.id", ondelete="SET NULL"), nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    carrier_name: Mapped[str] = mapped_column(String(100), default="Moto Express", nullable=False)
    carrier_phone: Mapped[Optional[str]] = mapped_column(String(20))
    delivery_address: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    # Estados: PENDING_DISPATCH, ASSIGNED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, FAILED_ATTEMPT, RESCHEDULED, RETURNED_TO_STORE
    status: Mapped[str] = mapped_column(String(30), default="PENDING_DISPATCH", nullable=False, index=True)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    # Evidencia de entrega: foto tomada por el repartidor (data URL comprimida) y quién recibió.
    delivery_photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_by_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order: Mapped[Order] = relationship()
    zone: Mapped[Optional[DeliveryZone]] = relationship()
    delivery_person: Mapped[Optional[DeliveryPerson]] = relationship()
    events: Mapped[List["ShipmentTrackingEvent"]] = relationship(
        "ShipmentTrackingEvent", back_populates="shipment", cascade="all, delete-orphan",
        order_by="ShipmentTrackingEvent.created_at.asc()"
    )


class ShipmentTrackingEvent(Base):
    """[CU30] Evento cronológico en la línea de tiempo de rastreo."""
    __tablename__ = "shipment_tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="Almacén Central", nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="events")
