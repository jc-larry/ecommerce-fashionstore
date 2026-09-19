"""Modelos para la gestión de Repartidores (Delivery Persons) - CU05, CU29, CU30."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Numeric, ForeignKey, DateTime, func, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.seguridad_y_usuarios.models import User


class DeliveryPerson(Base):
    """[CU05, CU29] Perfil operativo del repartidor de última milla."""
    __tablename__ = "delivery_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="MOTO", nullable=False)  # MOTO, BICICLETA, AUTO, TORITO
    vehicle_plate: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    license_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coverage_zone: Mapped[str] = mapped_column(String(100), default="Santa Cruz - Anillos 1 al 4", nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0, nullable=False)
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship("User")
