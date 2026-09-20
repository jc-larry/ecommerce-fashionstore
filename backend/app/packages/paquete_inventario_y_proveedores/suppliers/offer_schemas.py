"""Schemas Pydantic para Ofertas de Proveedores y Solicitudes de Reposición (CU08, CU10)."""
from datetime import datetime, date
import json
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

SUPPLIER_PRODUCT_STATUSES = ("DISPONIBLE", "AGOTADO", "DESCONTINUADO")
MAX_OFFER_PHOTOS = 6
MAX_PHOTO_LENGTH = 1_500_000


def _validate_photo(url: str) -> str:
    url = url.strip()
    if not (url.startswith("data:image/") or url.startswith("http") or url.startswith("/uploads/")):
        raise ValueError("Cada foto debe ser una imagen (data:image/...) o una URL.")
    if len(url) > MAX_PHOTO_LENGTH:
        raise ValueError("Una de las fotos es demasiado grande.")
    return url


# ===================================================================
# OFERTAS DE PRENDAS DEL PROVEEDOR (CU08)
# ===================================================================

class SupplierOfferCreate(BaseModel):
    # Para un PROVEEDOR se ignora y se usa su propio proveedor vinculado.
    supplier_id: Optional[int] = None
    product_name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=5)
    category: str = Field("Prendas Casuales", max_length=100)
    unit_cost: float = Field(..., gt=0, description="Precio unitario cobrado por el proveedor")
    suggested_retail_price: float = Field(..., gt=0, description="Precio sugerido de venta al público")
    min_order_quantity: int = Field(10, gt=0)
    available_quantity: int = Field(100, gt=0)
    sizes_available: str = Field("S, M, L, XL", max_length=100)
    colors_available: str = Field("Negro, Blanco, Azul", max_length=100)
    # Galería de fotos de la prenda y la que el proveedor eligió como portada.
    image_urls: List[str] = Field(default_factory=list, max_length=MAX_OFFER_PHOTOS)
    image_url: Optional[str] = None

    @field_validator("image_urls")
    @classmethod
    def _check_photos(cls, v: List[str]) -> List[str]:
        return [_validate_photo(u) for u in v if u and u.strip()]


class SupplierOfferReview(BaseModel):
    status: str = Field(..., description="APPROVED o REJECTED")
    target_branch_id: Optional[int] = Field(None, description="Sucursal destino asignada por el admin si aprueba")
    admin_notes: Optional[str] = None
    product_id: Optional[int] = Field(None, description="Prenda del catálogo que corresponde a esta oferta")


class SupplierOfferStatusUpdate(BaseModel):
    status: str = Field(..., description="DISPONIBLE, AGOTADO o DESCONTINUADO")
    available_quantity: Optional[int] = Field(None, ge=0)
    admin_notes: Optional[str] = None


class SupplierOfferResponse(BaseModel):
    id: int
    supplier_id: int
    product_name: str
    description: str
    category: str
    unit_cost: float
    suggested_retail_price: float
    min_order_quantity: int
    available_quantity: int
    sizes_available: str
    colors_available: str
    image_url: Optional[str]
    image_urls: List[str] = []
    product_id: Optional[int] = None
    target_branch_id: Optional[int]
    status: str
    admin_notes: Optional[str]
    reviewed_by_id: Optional[int]
    reviewed_at: Optional[datetime]
    created_at: datetime
    supplier_name: Optional[str] = None
    target_branch_name: Optional[str] = None

    class Config:
        from_attributes = True


# ===================================================================
# SOLICITUDES DE REPOSICIÓN (ADMIN -> PROVEEDOR) CON SUCURSAL DESTINO
# ===================================================================

class SupplierReorderCreate(BaseModel):
    supplier_id: int
    variant_id: int
    requested_quantity: int = Field(..., gt=0, description="Cantidad requerida")
    target_branch_id: int = Field(..., description="Sucursal de destino donde el proveedor debe entregar")
    unit_cost: float = Field(..., ge=0, description="Costo unitario acordado")


class SupplierReorderRespond(BaseModel):
    status: str = Field(..., description="ACCEPTED o REJECTED")
    estimated_delivery: Optional[date] = None
    supplier_notes: Optional[str] = None


class SupplierReorderResponse(BaseModel):
    id: int
    supplier_id: int
    variant_id: int
    requested_quantity: int
    target_branch_id: int
    unit_cost: float
    status: str
    requested_by_id: int
    supplier_notes: Optional[str]
    estimated_delivery: Optional[date]
    created_at: datetime
    updated_at: datetime
    code: Optional[str] = None
    supplier_name: Optional[str] = None
    product_name: Optional[str] = None
    variant_label: Optional[str] = None
    sku: Optional[str] = None
    target_branch_name: Optional[str] = None
    requested_by_name: Optional[str] = None
    product_id: Optional[int] = None
    product_image_url: Optional[str] = None

    class Config:
        from_attributes = True


class SupplierProductStatusUpdate(BaseModel):
    status: str = Field(..., description="DISPONIBLE, AGOTADO o DESCONTINUADO")


class SupplierProductStatusResponse(BaseModel):
    supplier_id: int
    product_id: int
    status: str
