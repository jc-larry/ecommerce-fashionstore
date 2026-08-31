from typing import List, Optional
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, Numeric, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant
from app.packages.inventario_y_proveedores.suppliers.models import Supplier

class Inventory(Base):
    __tablename__ = "inventory"

    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), primary_key=True)
    stock_actual: Mapped[int] = mapped_column(default=0, nullable=False)
    stock_minimo: Mapped[int] = mapped_column(default=5, nullable=False)
    stock_maximo: Mapped[int] = mapped_column(default=100, nullable=False)

    branch: Mapped[Branch] = relationship()
    variant: Mapped[ProductVariant] = relationship()

class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False) # Positivo para ingresos, negativo para salidas
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False) # 'INGRESO', 'VENTA', 'RESERVA', 'AJUSTE', 'TRANSFERENCIA'
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False) # Costo unitario ponderado
    reference_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # ID del documento de referencia
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    branch: Mapped[Branch] = relationship()
    variant: Mapped[ProductVariant] = relationship()

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETADO", nullable=False) # 'COMPLETADO', 'CANCELADO'
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    supplier: Mapped[Supplier] = relationship()
    branch: Mapped[Branch] = relationship()
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

    purchase_order: Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="details")
    variant: Mapped[ProductVariant] = relationship()
