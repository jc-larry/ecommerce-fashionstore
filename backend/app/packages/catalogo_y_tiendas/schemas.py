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


# ---------- Reseñas y favoritos (CU14 / CU14+) ----------
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewResponse(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    author_name: str
    is_mine: bool = False
    status: str = "APPROVED"
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

class ReviewModerationItem(BaseModel):
    id: int
    product_id: int
    product_name: str
    user_id: int
    author_name: str
    author_email: str
    rating: int
    comment: Optional[str] = None
    status: str
    created_at: datetime

class ReviewModerateAction(BaseModel):
    status: str = Field(..., pattern="^(APPROVED|REJECTED)$")

class WishlistToggleResponse(BaseModel):
    product_id: int
    in_wishlist: bool

class WishlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    is_public: bool = False

class WishlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_public: Optional[bool] = None

class WishlistResponse(BaseModel):
    id: int
    name: str
    is_public: bool
    share_token: str
    created_at: datetime
    items_count: int = 0

class WishlistDetailResponse(BaseModel):
    id: int
    name: str
    is_public: bool
    share_token: str
    created_at: datetime
    owner_name: Optional[str] = None
    products: List[ProductResponse] = []


# ---------- Búsqueda y Disponibilidad por Sucursal (CU12) ----------
class BranchStockDetail(BaseModel):
    branch_id: int
    branch_name: str
    branch_code: Optional[str] = None
    city: Optional[str] = None
    stock: int

class VariantBranchStock(BaseModel):
    variant_id: int
    sku: str
    color_id: int
    color_name: str
    color_hex: str
    size_id: int
    size_name: str
    branches: List[BranchStockDetail] = []
    total_stock: int = 0

class ProductAvailabilityResponse(BaseModel):
    product_id: int
    product_name: str
    variants: List[VariantBranchStock] = []
    total_stock: int = 0

class BranchOption(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    city: Optional[str] = None

class CatalogFilterOptionsResponse(BaseModel):
    min_price: float
    max_price: float
    categories: List[CategoryResponse]
    sizes: List[SizeResponse]
    colors: List[ColorResponse]
    seasons: List[SeasonResponse]
    branches: List[BranchOption]

class ProductSearchResultItem(ProductResponse):
    branch_stock: Optional[int] = None
    total_stock: int = 0

class ProductSearchResponse(BaseModel):
    items: List[ProductSearchResultItem]
    total: int
    page: int
    limit: int
    total_pages: int


# ---------- Promociones y Cupones (CU13) ----------
class CouponBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=30)
    discount_type: str = Field("PORCENTAJE", pattern="^(PORCENTAJE|MONTO_FIJO)$")
    discount_value: float = Field(..., gt=0)
    min_purchase_amount: float = Field(0.0, ge=0)
    valid_from: datetime
    valid_until: datetime
    max_uses: int = Field(100, gt=0)
    is_active: bool = True

class CouponCreate(CouponBase):
    pass

class CouponUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=3, max_length=30)
    discount_type: Optional[str] = Field(None, pattern="^(PORCENTAJE|MONTO_FIJO)$")
    discount_value: Optional[float] = Field(None, gt=0)
    min_purchase_amount: Optional[float] = Field(None, ge=0)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None

class CouponResponse(CouponBase):
    id: int
    used_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class CouponValidateRequest(BaseModel):
    code: str
    cart_total: float = Field(..., ge=0)

class CouponValidateResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str = "PORCENTAJE"
    discount_value: float = 0.0
    discount_amount: float = 0.0
    new_total: float = 0.0
    message: str

class SeasonalPromotionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    discount_percent: int = Field(..., gt=0, le=100)
    category_id: Optional[int] = None
    start_date: date
    end_date: date
    is_active: bool = True

class SeasonalPromotionCreate(SeasonalPromotionBase):
    pass

class SeasonalPromotionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    discount_percent: Optional[int] = Field(None, gt=0, le=100)
    category_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None

class SeasonalPromotionResponse(SeasonalPromotionBase):
    id: int
    created_at: datetime
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True
