"""Modelos de Ofertas de Proveedores y Solicitudes de Reposición (CU08, CU10)."""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Numeric, ForeignKey, DateTime, Date, func, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.packages.paquete_inventario_y_proveedores.suppliers.models import Supplier
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import ProductVariant
from app.packages.paquete_seguridad_usuarios.models import User


class SupplierOffer(Base):
    """[CU08] Prenda ofertada por un proveedor al Administrador General."""
    __tablename__ = "supplier_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="Prendas Casuales", nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    suggested_retail_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_quantity: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    sizes_available: Mapped[str] = mapped_column(String(100), default="S, M, L, XL", nullable=False)
    colors_available: Mapped[str] = mapped_column(String(100), default="Negro, Blanco, Azul", nullable=False)
    # Foto de portada elegida por el proveedor + galería completa (JSON de URLs o data URLs).
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Prenda del catálogo a la que Casa Matriz vinculó la oferta al aprobarla.
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    target_branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    # Estados: PENDING, APPROVED, REJECTED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    admin_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    supplier: Mapped[Supplier] = relationship()
    target_branch: Mapped[Optional[Branch]] = relationship()
    reviewed_by: Mapped[Optional[User]] = relationship()


class SupplierReorderRequest(Base):
    """[CU08, CU10] Solicitud del Administrador al Proveedor para pedir más unidades.
    
    El Administrador define OBLIGATORIAMENTE la sucursal de destino (target_branch_id)
    a la cual el proveedor debe entregar la mercadería.
    """
    __tablename__ = "supplier_reorder_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    # Estados: PENDING, ACCEPTED, SHIPPED, RECEIVED, CANCELLED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    supplier_notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    estimated_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    supplier: Mapped[Supplier] = relationship()
    variant: Mapped[ProductVariant] = relationship()
    target_branch: Mapped[Branch] = relationship()
    requested_by: Mapped[User] = relationship()


class SupplierProductStatus(Base):
    """Disponibilidad que el proveedor declara para una prenda del catálogo.

    DISPONIBLE, AGOTADO (temporalmente sin stock) o DESCONTINUADO (ya no la trae).
    Casa Matriz no puede pedir reposición de una prenda AGOTADA o DESCONTINUADA a ese proveedor.
    """
    __tablename__ = "supplier_product_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DISPONIBLE", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product_status"),)
