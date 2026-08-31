from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

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

class SizeCreate(SizeBase):
    pass

class SizeResponse(SizeBase):
    id: int

    class Config:
        from_attributes = True

class ProductImageBase(BaseModel):
    color_id: int
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
    category_id: int
    season_id: Optional[int] = None
    is_active: Optional[bool] = True

class ProductCreate(ProductBase):
    variants: List[ProductVariantCreate] = []
    images: List[ProductImageCreate] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    category_id: Optional[int] = None
    season_id: Optional[int] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    category: CategoryResponse
    season: Optional[SeasonResponse] = None
    variants: List[ProductVariantResponse] = []
    images: List[ProductImageResponse] = []

    class Config:
        from_attributes = True
