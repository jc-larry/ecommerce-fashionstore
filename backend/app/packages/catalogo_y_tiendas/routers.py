import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile, Header
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db

from app.packages.catalogo_y_tiendas.models import (
    Category, Season, Color, Size, Product, ProductVariant, ProductImage,
    ProductReview, WishlistItem,
)
from app.packages.catalogo_y_tiendas.schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, SeasonCreate, SeasonResponse,
    ColorCreate, ColorResponse, SizeCreate, SizeResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    ReviewCreate, ReviewResponse, ReviewSummary, ProductReviewsResponse,
    RatingSummaryItem, WishlistToggleResponse,
)
# Importar control de roles y logueo de auditoría del paquete de Seguridad
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event, get_current_user
from app.packages.seguridad_y_usuarios.models import SessionToken
from app.packages.seguridad_y_usuarios.services import decode_access_token

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])

# Requiere rol SUPERADMIN para gestionar el catálogo (CU07)
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Devuelve el usuario si hay un token válido; None si no hay token (rutas públicas con extra si logueado)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    user_id = decode_access_token(token)
    if not user_id:
        return None
    session = db.query(SessionToken).filter(
        SessionToken.token == token, SessionToken.is_revoked == False  # noqa: E712
    ).first()
    if not session:
        return None
    return db.query(User).filter(User.id == int(user_id), User.is_active == True).first()  # noqa: E712


def _attach_ratings(db: Session, products: List[Product]) -> None:
    """Rellena rating_avg / rating_count / discount_percent en cada Product (para ProductResponse)."""
    ids = [p.id for p in products]
    ratings: dict[int, tuple] = {}
    if ids:
        rows = (
            db.query(
                ProductReview.product_id,
                func.avg(ProductReview.rating),
                func.count(ProductReview.id),
            )
            .filter(ProductReview.product_id.in_(ids))
            .group_by(ProductReview.product_id)
            .all()
        )
        ratings = {pid: (float(avg or 0), int(cnt or 0)) for pid, avg, cnt in rows}
    for p in products:
        avg, cnt = ratings.get(p.id, (0.0, 0))
        p.rating_avg = round(avg, 1)
        p.rating_count = cnt
        base = float(p.base_price or 0)
        cmp_price = float(p.compare_at_price) if p.compare_at_price else 0.0
        p.discount_percent = round((1 - base / cmp_price) * 100) if cmp_price > base > 0 else 0

@router.post("/upload-image")
def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(admin_check)
):
    """[CU07] Sube un archivo de imagen de prenda al servidor y devuelve su URL relativa"""
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido ({ext}). Use JPG, PNG o WEBP."
        )

    unique_name = f"{uuid.uuid4().hex}{ext}"
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    upload_dir = os.path.join(base_dir, "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    dest_path = os.path.join(upload_dir, unique_name)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"image_url": f"/uploads/products/{unique_name}"}

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

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU07] Actualiza una categoría (nombre, descripción o su foto de portada)"""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    log_event(db, current_user.id, "UPDATE", "categories", cat.id, {"name": cat.name}, request.client.host)
    return cat

@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    if cat.products:
        raise HTTPException(status_code=400, detail="No se puede eliminar la categoría porque contiene prendas asociadas.")
    if cat.subcategories:
        raise HTTPException(status_code=400, detail="No se puede eliminar porque contiene subcategorías.")
    db.delete(cat)
    db.commit()
    log_event(db, current_user.id, "DELETE", "categories", category_id, {"name": cat.name}, request.client.host)
    return None

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

@router.delete("/colors/{color_id}", status_code=204)
def delete_color(
    color_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    c = db.query(Color).filter(Color.id == color_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Color no encontrado.")
    db.delete(c)
    db.commit()
    log_event(db, current_user.id, "DELETE", "colors", color_id, {"name": c.name}, request.client.host)
    return None

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

@router.delete("/sizes/{size_id}", status_code=204)
def delete_size(
    size_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    s = db.query(Size).filter(Size.id == size_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Talla no encontrada.")
    db.delete(s)
    db.commit()
    log_event(db, current_user.id, "DELETE", "sizes", size_id, {"name": s.name}, request.client.host)
    return None

# --- Prendas (Products) ---
@router.get("/products", response_model=List[ProductResponse])
def list_products(db: Session = Depends(get_db)):
    """[CU07 / CU11] Lista el catálogo completo de prendas (el cliente filtra activos en el frontend)"""
    # [CU11 - Paso 3] / [DSC011 - Paso 3] +select_active() (aquí trae todos y filtra frontend, u obtiene filtrados)
    prods = (
        db.query(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .all()
    )
    _attach_ratings(db, prods)
    return prods

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """[CU11] Detalle de una prenda para la vista del cliente (galería, colores, tallas, reseñas)"""
    prod = (
        db.query(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")
    _attach_ratings(db, [prod])
    return prod

@router.get("/ratings-summary", response_model=List[RatingSummaryItem])
def ratings_summary(db: Session = Depends(get_db)):
    """[CU14] Promedio y conteo de reseñas por prenda (para pintar ★ en la grilla de la tienda)"""
    rows = (
        db.query(
            ProductReview.product_id,
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .group_by(ProductReview.product_id)
        .all()
    )
    return [
        RatingSummaryItem(product_id=pid, average=round(float(avg or 0), 1), count=int(cnt or 0))
        for pid, avg, cnt in rows
    ]

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
        compare_at_price=data.compare_at_price,
        category_id=data.category_id,
        season_id=data.season_id,
        is_active=data.is_active,
        material=data.material,
        neck_type=data.neck_type,
        sleeve_length=data.sleeve_length,
        tags=data.tags,
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
    _attach_ratings(db, [prod])
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

    update_data = data.model_dump(exclude_unset=True)
    images_data = update_data.pop("images", None)
    variants_data = update_data.pop("variants", None)

    for key, value in update_data.items():
        setattr(prod, key, value)

    if images_data is not None:
        db.query(ProductImage).filter(ProductImage.product_id == prod.id).delete()
        for img in data.images or []:
            db.add(ProductImage(
                product_id=prod.id,
                color_id=img.color_id,
                image_url=img.image_url,
                is_primary=img.is_primary or False
            ))

    # Reconciliar variantes (color·talla·SKU) — CU07 "medidas estándares"
    if variants_data is not None:
        incoming = data.variants or []
        keep_skus = {v.sku for v in incoming}
        existing = {v.sku: v for v in prod.variants}
        # 1. Desactivar (baja lógica) las que ya no vienen — conservan histórico de inventario
        for sku, var in existing.items():
            if sku not in keep_skus:
                var.is_active = False
        # 2. Insertar / reactivar las entrantes
        for v in incoming:
            if v.sku in existing:
                cur = existing[v.sku]
                cur.color_id, cur.size_id, cur.is_active = v.color_id, v.size_id, True
                cur.price_override = v.price_override
            else:
                dup = db.query(ProductVariant).filter(ProductVariant.sku == v.sku).first()
                if dup:
                    raise HTTPException(status_code=400, detail=f"El SKU '{v.sku}' ya existe en otra prenda.")
                db.add(ProductVariant(
                    product_id=prod.id, color_id=v.color_id, size_id=v.size_id,
                    sku=v.sku, price_override=v.price_override, is_active=True,
                ))

    db.commit()
    db.refresh(prod)

    # Auditar actualización de producto (CU36)
    log_event(db, current_user.id, "UPDATE", "products", prod.id, {"old": old_vals, "new": {"name": prod.name, "base_price": float(prod.base_price), "is_active": prod.is_active}}, request.client.host)
    _attach_ratings(db, [prod])
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
    db.refresh(prod)

    # Auditar desactivación de producto (CU36)
    log_event(db, current_user.id, "UPDATE", "products", prod.id, {"deactivated": True, "name": prod.name}, request.client.host)
    _attach_ratings(db, [prod])
    return prod


# ===================================================================
# CU14 — Reseñas de prendas
# ===================================================================
@router.get("/products/{product_id}/reviews", response_model=ProductReviewsResponse)
def list_reviews(
    product_id: int,
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_optional_user),
):
    """[CU14] Lista las reseñas de una prenda con su promedio y conteo (pública)"""
    if not db.query(Product.id).filter(Product.id == product_id).first():
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    rows = (
        db.query(ProductReview, User.first_name, User.last_name)
        .join(User, User.id == ProductReview.user_id)
        .filter(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
        .all()
    )
    me_id = me.id if me else None
    items = [
        ReviewResponse(
            id=rv.id, rating=rv.rating, comment=rv.comment,
            author_name=f"{fn} {ln}".strip() or "Cliente",
            is_mine=(me_id is not None and rv.user_id == me_id),
            created_at=rv.created_at,
        )
        for rv, fn, ln in rows
    ]
    count = len(items)
    average = round(sum(i.rating for i in items) / count, 1) if count else 0.0
    return ProductReviewsResponse(summary=ReviewSummary(average=average, count=count), items=items)


@router.post("/products/{product_id}/reviews", response_model=ReviewResponse, status_code=201)
def submit_review(
    product_id: int,
    data: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14] Crea o actualiza la reseña del cliente para esta prenda (una por prenda por cliente)"""
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    review = (
        db.query(ProductReview)
        .filter(ProductReview.product_id == product_id, ProductReview.user_id == current_user.id)
        .first()
    )
    action = "UPDATE" if review else "INSERT"
    if review:
        review.rating = data.rating
        review.comment = data.comment
    else:
        review = ProductReview(
            product_id=product_id, user_id=current_user.id,
            rating=data.rating, comment=data.comment,
        )
        db.add(review)
    db.commit()
    db.refresh(review)

    log_event(db, current_user.id, action, "product_reviews", review.id,
              {"product_id": product_id, "rating": data.rating}, request.client.host)
    return ReviewResponse(
        id=review.id, rating=review.rating, comment=review.comment,
        author_name=f"{current_user.first_name} {current_user.last_name}".strip(),
        is_mine=True, created_at=review.created_at,
    )


# ===================================================================
# CU14 — Favoritos (wishlist)
# ===================================================================
@router.get("/wishlist", response_model=List[ProductResponse])
def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14] Prendas marcadas como favoritas por el cliente"""
    prods = (
        db.query(Product)
        .join(WishlistItem, WishlistItem.product_id == Product.id)
        .filter(WishlistItem.user_id == current_user.id)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    _attach_ratings(db, prods)
    return prods


@router.post("/wishlist/{product_id}", response_model=WishlistToggleResponse)
def add_to_wishlist(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14] Marca una prenda como favorita (idempotente)"""
    if not db.query(Product.id).filter(Product.id == product_id).first():
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")
    exists = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id, WishlistItem.product_id == product_id
    ).first()
    if not exists:
        db.add(WishlistItem(user_id=current_user.id, product_id=product_id))
        db.commit()
        log_event(db, current_user.id, "INSERT", "wishlist_items", product_id,
                  {"product_id": product_id}, request.client.host)
    return WishlistToggleResponse(product_id=product_id, in_wishlist=True)


@router.delete("/wishlist/{product_id}", response_model=WishlistToggleResponse)
def remove_from_wishlist(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14] Quita una prenda de favoritos"""
    deleted = db.query(WishlistItem).filter(
        WishlistItem.user_id == current_user.id, WishlistItem.product_id == product_id
    ).delete()
    db.commit()
    if deleted:
        log_event(db, current_user.id, "DELETE", "wishlist_items", product_id,
                  {"product_id": product_id}, request.client.host)
    return WishlistToggleResponse(product_id=product_id, in_wishlist=False)
