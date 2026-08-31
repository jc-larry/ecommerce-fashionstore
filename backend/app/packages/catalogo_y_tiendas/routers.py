from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db

from app.packages.catalogo_y_tiendas.models import Category, Season, Color, Size, Product, ProductVariant, ProductImage
from app.packages.catalogo_y_tiendas.schemas import (
    CategoryCreate, CategoryResponse, SeasonCreate, SeasonResponse,
    ColorCreate, ColorResponse, SizeCreate, SizeResponse,
    ProductCreate, ProductUpdate, ProductResponse
)
# Importar control de roles y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])

# Requiere rol SUPERADMIN para gestionar el catálogo (CU07)
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])

# --- Categorías ---
@router.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()

@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(
    data: CategoryCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_event(db, current_user.id, "INSERT", "categories", cat.id, {"name": cat.name}, request.client.host)
    return cat

# --- Temporadas ---
@router.get("/seasons", response_model=List[SeasonResponse])
def list_seasons(db: Session = Depends(get_db)):
    return db.query(Season).all()

@router.post("/seasons", response_model=SeasonResponse, status_code=201)
def create_season(
    data: SeasonCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    season = Season(**data.model_dump())
    db.add(season)
    db.commit()
    db.refresh(season)
    log_event(db, current_user.id, "INSERT", "seasons", season.id, {"name": season.name}, request.client.host)
    return season

# --- Colores ---
@router.get("/colors", response_model=List[ColorResponse])
def list_colors(db: Session = Depends(get_db)):
    return db.query(Color).all()

@router.post("/colors", response_model=ColorResponse, status_code=201)
def create_color(
    data: ColorCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    color = Color(**data.model_dump())
    db.add(color)
    db.commit()
    db.refresh(color)
    log_event(db, current_user.id, "INSERT", "colors", color.id, {"name": color.name, "hex_code": color.hex_code}, request.client.host)
    return color

# --- Tallas ---
@router.get("/sizes", response_model=List[SizeResponse])
def list_sizes(db: Session = Depends(get_db)):
    return db.query(Size).all()

@router.post("/sizes", response_model=SizeResponse, status_code=201)
def create_size(
    data: SizeCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    size = Size(**data.model_dump())
    db.add(size)
    db.commit()
    db.refresh(size)
    log_event(db, current_user.id, "INSERT", "sizes", size.id, {"name": size.name}, request.client.host)
    return size

# --- Prendas (Products) ---
@router.get("/products", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """[CU07 / CU11] Lista el catálogo completo de prendas (el cliente filtra activos en el frontend)"""
    # [CU11 - Paso 3] / [DSC011 - Paso 3] +select_active() (aquí trae todos y filtra frontend, u obtiene filtrados)
    return db.query(Product).all()

@router.post("/products", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU07] Registra una nueva prenda con sus variantes e imágenes"""
    # [CU07 - Paso 3] / [DSC007 - Paso 3] +insert_product(datos)
    prod = Product(
        name=data.name,
        description=data.description,
        base_price=data.base_price,
        category_id=data.category_id,
        season_id=data.season_id,
        is_active=data.is_active
    )
    db.add(prod)
    db.flush()
    # [CU07 - Paso 4] / [DSC007 - Paso 4] +ID Producto (implícito)

    # [CU07 - Paso 5] / [DSC007 - Paso 5] +insert_variants(variantes)
    for var in data.variants:
        variant = ProductVariant(
            product_id=prod.id,
            color_id=var.color_id,
            size_id=var.size_id,
            sku=var.sku,
            price_override=var.price_override,
            is_active=var.is_active
        )
        db.add(variant)

    # Agregar imágenes asociadas
    for img in data.images:
        image = ProductImage(
            product_id=prod.id,
            color_id=img.color_id,
            image_url=img.image_url,
            is_primary=img.is_primary
        )
        db.add(image)

    db.commit()
    db.refresh(prod)

    # Auditar inserción de producto (CU36)
    log_event(db, current_user.id, "INSERT", "products", prod.id, {"name": prod.name, "variants_count": len(data.variants)}, request.client.host)
    # [CU07 - Paso 6] / [DSC007 - Paso 6] +Producto Creado
    return prod

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, 
    data: ProductUpdate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU07] Actualiza la información técnica de una prenda"""
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    old_vals = {"name": prod.name, "base_price": float(prod.base_price), "is_active": prod.is_active}

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(prod, key, value)

    db.commit()
    db.refresh(prod)

    # Auditar actualización de producto (CU36)
    log_event(db, current_user.id, "UPDATE", "products", prod.id, {"old": old_vals, "new": {"name": prod.name, "base_price": float(prod.base_price), "is_active": prod.is_active}}, request.client.host)
    return prod

@router.delete("/products/{product_id}", response_model=ProductResponse)
def deactivate_product(
    product_id: int, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU07] Realiza la baja lógica (desactivar) de una prenda del catálogo"""
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    prod.is_active = False
    db.commit()

    # Auditar desactivación de producto (CU36)
    log_event(db, current_user.id, "UPDATE", "products", prod.id, {"deactivated": True, "name": prod.name}, request.client.host)
    return prod
