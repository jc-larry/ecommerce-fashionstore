from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, Numeric, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

if TYPE_CHECKING:
    from app.packages.catalogo_y_tiendas.branches.models import Branch
    from app.packages.catalogo_y_tiendas.models import ProductVariant
    from app.packages.inventario_y_proveedores.suppliers.models import Supplier

class Inventory(Base):
    __tablename__ = "inventory"

    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True)
    stock_actual: Mapped[int] = mapped_column(default=0, nullable=False)
    # Costo promedio ponderado vigente por sucursal+variante (CU10 lo recalcula, CU37 lo consulta)
    avg_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(default=5, nullable=False)
    stock_maximo: Mapped[int] = mapped_column(default=100, nullable=False)

    branch: Mapped["Branch"] = relationship("Branch")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False) # Positivo para ingresos, negativo para salidas
    movement_type: Mapped[str] = mapped_column(String(30), nullable=False) # 'INGRESO', 'VENTA', 'RESERVA', 'AJUSTE', 'TRANSFERENCIA'
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False) # Costo unitario ponderado
    reference_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # ID del documento de referencia
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    branch: Mapped["Branch"] = relationship("Branch")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETADO", nullable=False) # 'COMPLETADO', 'CANCELADO'
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Factura / Nota de entrega proveedor
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False) # Flete prorrateable
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    supplier: Mapped["Supplier"] = relationship("Supplier")
    branch: Mapped["Branch"] = relationship("Branch")
    details: Mapped[List["PurchaseDetail"]] = relationship(
        "PurchaseDetail", 
        back_populates="purchase_order", 
        cascade="all, delete-orphan"
    )

class PurchaseDetail(Base):
    __tablename__ = "purchase_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    previous_avg_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), default=0.0, nullable=True)
    new_avg_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), default=0.0, nullable=True)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="details")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")


class StockTransfer(Base):
    """[CU15] Transferencia de mercadería entre sucursales con trazabilidad en libro mayor."""
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    origin_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    destination_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    received_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SOLICITADA", nullable=False)  # 'SOLICITADA', 'EN_TRANSITO', 'COMPLETADA', 'CANCELADA'
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    origin_branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[origin_branch_id])
    destination_branch: Mapped["Branch"] = relationship("Branch", foreign_keys=[destination_branch_id])
    details: Mapped[List["StockTransferDetail"]] = relationship(
        "StockTransferDetail", back_populates="transfer", cascade="all, delete-orphan"
    )


class StockTransferDetail(Base):
    """[CU15] Detalle de prendas y cantidades enviadas en una transferencia."""
    __tablename__ = "stock_transfer_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[int] = mapped_column(ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)

    transfer: Mapped["StockTransfer"] = relationship("StockTransfer", back_populates="details")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant")
