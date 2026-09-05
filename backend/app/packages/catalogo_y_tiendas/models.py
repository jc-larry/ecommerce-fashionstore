from typing import List, Optional
from datetime import datetime, date
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, DateTime, SmallInteger,
    ForeignKey, UniqueConstraint, CheckConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    # Foto de portada de la categoría (círculo en la navegación de la tienda) — CU07 / CU11
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    # Taxonomía jerárquica (Categoría principal -> Subcategorías)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories: Mapped[List["Category"]] = relationship("Category", back_populates="parent")
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")

class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    products: Mapped[List["Product"]] = relationship("Product", back_populates="season")

class Color(Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hex_code: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)

class Size(Base):
    __tablename__ = "sizes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    # Tipo de curva: 'TOPS' (XS-XXL), 'BOTTOMS' (34-44), 'BOTTOMS_US' (24-34), 'GENERAL'
    category_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Precio "antes" para mostrar la oferta directa por prenda (null = sin oferta) — CU07 / CU13 (slice)
    compare_at_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Atributos de moda femenina para filtros y ficha técnica
    material: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    neck_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sleeve_length: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    season: Mapped[Optional["Season"]] = relationship("Season", back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images: Mapped[List["ProductImage"]] = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    reviews: Mapped[List["ProductReview"]] = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")

class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id", ondelete="RESTRICT"), nullable=False)
    size_id: Mapped[int] = mapped_column(ForeignKey("sizes.id", ondelete="RESTRICT"), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    price_override: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    color: Mapped["Color"] = relationship("Color")
    size: Mapped["Size"] = relationship("Size")

    __table_args__ = (
        UniqueConstraint("product_id", "color_id", "size_id", name="unique_product_color_size"),
    )

class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    color_id: Mapped[Optional[int]] = mapped_column(ForeignKey("colors.id", ondelete="SET NULL"), nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="images")
    color: Mapped[Optional["Color"]] = relationship("Color")


class ProductReview(Base):
    """[CU14] Reseña/calificación de una prenda por un cliente (una por prenda por cliente)."""
    __tablename__ = "product_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="reviews")

    __table_args__ = (
        UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )


class WishlistItem(Base):
    """[CU14] Prenda marcada como favorita por un cliente."""
    __tablename__ = "wishlist_items"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship("Product")
