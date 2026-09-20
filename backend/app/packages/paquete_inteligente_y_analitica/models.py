"""Modelos del paquete Inteligente y Analítica (CU32, CU33, CU34, CU35, CU39).

Maneja registros del vestidor virtual con IA (IDM-VTON / Difusión / RA), sesiones,
historial de prendas probadas, capturas biométricas, chatbot asistente y analítica.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, ForeignKey, DateTime, func, Integer, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant
from app.packages.paquete_seguridad_usuarios.models import User


class ChatbotConversation(Base):
    """[CU33] Historial de interacciones con el Asistente Virtual / Estilista IA."""
    __tablename__ = "chatbot_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_token: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)  # 'USER' | 'BOT'
    message: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(50))
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[Optional[User]] = relationship()


class VirtualTryonSession(Base):
    """[CU32] Sesión interactiva del Vestidor Virtual (Web y Móvil)."""
    __tablename__ = "virtual_tryon_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_token: Mapped[str] = mapped_column(String(100), index=True, unique=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="WEB", nullable=False)  # 'WEB' | 'MOBILE'
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # 'ACTIVE' | 'FINISHED'
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional[User]] = relationship()
    items: Mapped[List["VirtualTryonItem"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    captures: Mapped[List["VirtualTryonCapture"]] = relationship(back_populates="session")


class VirtualTryonItem(Base):
    """[CU32] Registro de prendas y variantes probadas durante una sesión de vestidor virtual."""
    __tablename__ = "virtual_tryon_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("virtual_tryon_sessions.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    tested_size: Mapped[Optional[str]] = mapped_column(String(20))
    fit_feedback: Mapped[Optional[str]] = mapped_column(String(100))
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped[VirtualTryonSession] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
    variant: Mapped[Optional[ProductVariant]] = relationship()


class VirtualTryonCapture(Base):
    """[CU32] Capturas y síntesis fotorrealista generadas por IA (IDM-VTON / Difusión / RA)."""
    __tablename__ = "virtual_tryon_captures"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("virtual_tryon_sessions.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    photo_url: Mapped[str] = mapped_column(Text, nullable=False)
    original_photo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generation_model: Mapped[str] = mapped_column(String(100), default="IDM-VTON", nullable=False)  # 'IDM-VTON' | 'FASHN_AI' | 'AR_HYBRID'
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, default=0.92)
    recommended_size: Mapped[Optional[str]] = mapped_column(String(20))
    measurements_json: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped[Optional[VirtualTryonSession]] = relationship(back_populates="captures")
    user: Mapped[Optional[User]] = relationship()
    product: Mapped[Product] = relationship()
    variant: Mapped[Optional[ProductVariant]] = relationship()
