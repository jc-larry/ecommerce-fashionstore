"""Modelos del paquete Notificaciones (CU40).

Maneja notificaciones in-app persistidas para los usuarios y enlaces con
alertas de pedidos, reservas, despachos y promociones.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.seguridad_y_usuarios.models import User


class InAppNotification(Base):
    """[CU40] Notificación in-app en buzón interno del usuario."""
    __tablename__ = "in_app_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # Tipos: RESERVATION, SHIPMENT, ORDER, SYSTEM, PROMOTION
    notification_type: Mapped[str] = mapped_column(String(30), default="SYSTEM", nullable=False)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship()
