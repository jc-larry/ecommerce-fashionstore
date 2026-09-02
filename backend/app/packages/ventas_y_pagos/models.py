"""Modelos base del paquete Ventas y Pagos.

En el **Ciclo 1** solo se crean las tablas (respaldo del diagrama de clases del análisis:
jerarquías `MedioDePago` y `Comprobante`). Los routers / la lógica transaccional (carrito,
checkout, POS, facturación) llegan en el **Ciclo 2** (CU17–CU24).

Herencia modelada:
* `Payment` ⭅ `EfectivoPayment` / `TarjetaPayment` / `QRPayment` / `CreditoPayment`
  (herencia de tabla única — Single Table Inheritance — discriminador `payment_type`).
* `Invoice` con `doc_type` (`FACTURA` / `NOTA_ENTREGA`) e IVA 13 %.
"""
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant
from app.packages.seguridad_y_usuarios.models import User


class Order(Base):
    """[CU17-CU19] Cabecera de pedido (canal ONLINE o POS presencial)."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), default="ONLINE", nullable=False)  # 'ONLINE' | 'POS'
    status: Mapped[str] = mapped_column(String(20), default="PENDIENTE", nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship()
    branch: Mapped[Branch] = relationship()
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
    invoice: Mapped[Optional["Invoice"]] = relationship(
        "Invoice", back_populates="order", uselist=False
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="items")
    variant: Mapped[ProductVariant] = relationship()


class Payment(Base):
    """[CU18] Medio de pago — clase base de la jerarquía (Single Table Inheritance).

    `MedioDePago` ⭅ Efectivo / Tarjeta / QR / Crédito. El discriminador es `payment_type`.
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMADO", nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Columnas específicas de subtipos (anulables)
    cash_received: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    cash_change: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    card_brand: Mapped[Optional[str]] = mapped_column(String(20))
    card_last4: Mapped[Optional[str]] = mapped_column(String(4))
    gateway_reference: Mapped[Optional[str]] = mapped_column(String(80))
    qr_reference: Mapped[Optional[str]] = mapped_column(String(80))
    credit_due_date: Mapped[Optional[date]] = mapped_column(Date)

    order: Mapped[Order] = relationship("Order", back_populates="payments")

    __mapper_args__ = {
        "polymorphic_on": payment_type,
        "polymorphic_identity": "PAGO",
    }


class EfectivoPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "EFECTIVO"}


class TarjetaPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "TARJETA"}


class QRPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "QR"}


class CreditoPayment(Payment):
    __mapper_args__ = {"polymorphic_identity": "CREDITO"}


class Invoice(Base):
    """[CU20] Comprobante — `Comprobante` ⭅ Factura / NotaDeEntrega. IVA 13 %."""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), unique=True, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(15), nullable=False)  # 'FACTURA' | 'NOTA_ENTREGA'
    tax_rate: Mapped[float] = mapped_column(Numeric(4, 3), default=0.130, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    control_code: Mapped[Optional[str]] = mapped_column(String(40))  # solo FACTURA
    customer_nit: Mapped[Optional[str]] = mapped_column(String(20))
    customer_name: Mapped[Optional[str]] = mapped_column(String(150))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped[Order] = relationship("Order", back_populates="invoice")
