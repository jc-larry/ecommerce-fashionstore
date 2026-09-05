from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    image_url: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class SeasonBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    start_date: date
    end_date: date

class SeasonCreate(SeasonBase):
    pass

class SeasonResponse(SeasonBase):
    id: int

    class Config:
        from_attributes = True

class ColorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    hex_code: str = Field(..., min_length=4, max_length=7)

class ColorCreate(ColorBase):
    pass

class ColorResponse(ColorBase):
    id: int

    class Config:
        from_attributes = True

class SizeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=10)
    category_type: Optional[str] = None

class SizeCreate(SizeBase):
    pass

class SizeResponse(SizeBase):
    id: int

    class Config:
        from_attributes = True

class ProductImageBase(BaseModel):
    color_id: Optional[int] = None
    image_url: str
    is_primary: Optional[bool] = False

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageResponse(ProductImageBase):
    id: int

    class Config:
        from_attributes = True

class ProductVariantBase(BaseModel):
    color_id: int
    size_id: int
    sku: str
    price_override: Optional[float] = None
    is_active: Optional[bool] = True

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantResponse(ProductVariantBase):
    id: int
    color: ColorResponse
    size: SizeResponse

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    base_price: float
    compare_at_price: Optional[float] = None  # precio "antes" (null = sin oferta)
    category_id: int
    season_id: Optional[int] = None
    is_active: Optional[bool] = True
    material: Optional[str] = None
    neck_type: Optional[str] = None
    sleeve_length: Optional[str] = None
    tags: Optional[str] = None

class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []
    images: List[ProductImageCreate] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    compare_at_price: Optional[float] = None
    category_id: Optional[int] = None
    season_id: Optional[int] = None
    is_active: Optional[bool] = None
    material: Optional[str] = None
    neck_type: Optional[str] = None
    sleeve_length: Optional[str] = None
    tags: Optional[str] = None
    images: Optional[List[ProductImageCreate]] = None
    variants: Optional[List[ProductVariantCreate]] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    category: CategoryResponse
    season: Optional[SeasonResponse] = None
    variants: List[ProductVariantResponse] = []
    images: List[ProductImageResponse] = []
    # Calificaciones (CU14) — se rellenan en el router
    rating_avg: float = 0.0
    rating_count: int = 0
    # Descuento calculado a partir de compare_at_price / base_price
    discount_percent: int = 0

    class Config:
        from_attributes = True


# ---------- Reseñas y favoritos (CU14) ----------
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    author_name: str
    is_mine: bool = False
    created_at: datetime

class ReviewSummary(BaseModel):
    average: float = 0.0
    count: int = 0

class ProductReviewsResponse(BaseModel):
    summary: ReviewSummary
    items: List[ReviewResponse]

class RatingSummaryItem(BaseModel):
    product_id: int
    average: float
    count: int

class WishlistToggleResponse(BaseModel):
    product_id: int
    in_wishlist: bool
