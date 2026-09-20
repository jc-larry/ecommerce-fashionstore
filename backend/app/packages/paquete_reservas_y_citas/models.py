"""Modelos del paquete Reservas y Citas (CU26, CU27, CU28).

Maneja el agendamiento de prendas para prueba física en sucursal (Fitting Room),
el control de stock apartado (HOLD), bandeja Kanban de preparación y conversión a POS.
"""
from datetime import datetime, timedelta, date
from typing import Optional, List

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Date, Boolean, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import ProductVariant
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_ventas_y_pagos.models import Order


class Reservation(Base):
    """[CU26, CU27, CU28] Reserva física de prendas en sucursal."""
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    # Estados: PENDING, PREPARING, READY, LATE, NO_SHOW, COMPLETED, CANCELLED, EXPIRED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    appointment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    appointment_time: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "HH:MM"
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    grace_period_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), default="TARJETA", nullable=True)  # 'TARJETA', 'PAYPAL', 'QR'
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Gateway transaction ID
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    completed_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    branch: Mapped[Branch] = relationship()
    completed_sale: Mapped[Optional[Order]] = relationship(foreign_keys=[completed_sale_id])
    items: Mapped[List["ReservationItem"]] = relationship(
        "ReservationItem", back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationItem(Base):
    """Detalle de prendas reservadas."""
    __tablename__ = "reservation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(String(100))

    reservation: Mapped[Reservation] = relationship(back_populates="items")
    variant: Mapped[ProductVariant] = relationship()
