import os
import uuid
import shutil
from datetime import datetime, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile, Header
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db

from app.packages.catalogo_y_tiendas.models import (
    Category, Season, Color, Size, Product, ProductVariant, ProductImage,
    ProductReview, WishlistItem, Wishlist, WishlistGroupItem, Coupon, SeasonalPromotion,
)
from app.packages.catalogo_y_tiendas.schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, SeasonCreate, SeasonResponse,
    ColorCreate, ColorResponse, SizeCreate, SizeResponse,
    ProductCreate, ProductUpdate, ProductResponse,
    ReviewCreate, ReviewResponse, ReviewSummary, ProductReviewsResponse,
    RatingSummaryItem, WishlistToggleResponse,
    ReviewModerationItem, ReviewModerateAction,
    WishlistCreate, WishlistUpdate, WishlistResponse, WishlistDetailResponse,
    BranchStockDetail, VariantBranchStock, ProductAvailabilityResponse,
    BranchOption, CatalogFilterOptionsResponse, ProductSearchResultItem, ProductSearchResponse,
    CouponCreate, CouponUpdate, CouponResponse, CouponValidateRequest, CouponValidateResponse,
    SeasonalPromotionCreate, SeasonalPromotionUpdate, SeasonalPromotionResponse,
)
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.inventario_y_proveedores.merchandise.models import Inventory
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
            .filter(ProductReview.product_id.in_(ids), ProductReview.status == "APPROVED")
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
    return prods

# --- Búsqueda y Disponibilidad por Sucursal (CU12) ---
@router.get("/filter-options", response_model=CatalogFilterOptionsResponse)
def get_catalog_filter_options(db: Session = Depends(get_db)):
    """[CU12] Opciones dinámicas para construir los filtros facetados de búsqueda."""
    price_stats = db.query(
        func.min(Product.base_price),
        func.max(Product.base_price)
    ).filter(Product.is_active == True).first()  # noqa: E712

    min_price = float(price_stats[0]) if price_stats and price_stats[0] is not None else 0.0
    max_price = float(price_stats[1]) if price_stats and price_stats[1] is not None else 1000.0
    if max_price <= min_price:
        max_price = min_price + 500.0

    categories = db.query(Category).order_by(Category.name.asc()).all()
    sizes = db.query(Size).order_by(Size.id.asc()).all()
    colors = db.query(Color).order_by(Color.name.asc()).all()
    seasons = db.query(Season).order_by(Season.name.asc()).all()
    branches = db.query(Branch).filter(Branch.is_active == True).order_by(Branch.name.asc()).all()  # noqa: E712

    branch_options = [
        BranchOption(id=b.id, name=b.name, code=b.code, city=b.city)
        for b in branches
    ]

    return CatalogFilterOptionsResponse(
        min_price=min_price,
        max_price=max_price,
        categories=categories,
        sizes=sizes,
        colors=colors,
        seasons=seasons,
        branches=branch_options,
    )


@router.get("/products/search", response_model=ProductSearchResponse)
def search_products(
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    season_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    size_id: Optional[int] = None,
    color_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    in_stock_only: bool = False,
    sort_by: Optional[str] = "newest",  # "newest", "price_asc", "price_desc", "rating"
    page: int = 1,
    limit: int = 12,
    db: Session = Depends(get_db),
):
    """[CU12] Búsqueda y filtrado facetado de catálogo con disponibilidad por sucursal."""
    query = (
        db.query(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .filter(Product.is_active == True)  # noqa: E712
    )

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            (Product.name.ilike(term)) |
            (Product.description.ilike(term)) |
            (Product.tags.ilike(term)) |
            (Product.material.ilike(term))
        )

    if category_id:
        child_cat_ids = [row[0] for row in db.query(Category.id).filter(Category.parent_id == category_id).all()]
        if child_cat_ids:
            query = query.filter(Product.category_id.in_([category_id] + child_cat_ids))
        else:
            query = query.filter(Product.category_id == category_id)

    if season_id:
        query = query.filter(Product.season_id == season_id)

    if min_price is not None:
        query = query.filter(Product.base_price >= min_price)

    if max_price is not None:
        query = query.filter(Product.base_price <= max_price)

    if size_id or color_id:
        variant_subquery = db.query(ProductVariant.product_id).filter(ProductVariant.is_active == True)  # noqa: E712
        if size_id:
            variant_subquery = variant_subquery.filter(ProductVariant.size_id == size_id)
        if color_id:
            variant_subquery = variant_subquery.filter(ProductVariant.color_id == color_id)
        query = query.filter(Product.id.in_(variant_subquery))

    all_matching = query.all()
    _attach_ratings(db, all_matching)

    # Calcular stock por sucursal y stock global para cada producto
    variant_ids = [v.id for p in all_matching for v in p.variants]
    stock_map: dict[tuple[int, int], int] = {}
    if variant_ids:
        inv_rows = (
            db.query(Inventory.branch_id, Inventory.variant_id, Inventory.stock_actual)
            .filter(Inventory.variant_id.in_(variant_ids))
            .all()
        )
        stock_map = {(r.branch_id, r.variant_id): int(r.stock_actual) for r in inv_rows}

    processed_items: List[ProductSearchResultItem] = []
    for prod in all_matching:
        p_var_ids = [v.id for v in prod.variants]

        total_stock = sum(
            qty for (b_id, v_id), qty in stock_map.items()
            if v_id in p_var_ids and qty > 0
        )

        branch_stock_val = None
        if branch_id is not None:
            branch_stock_val = sum(
                stock_map.get((branch_id, v_id), 0)
                for v_id in p_var_ids
            )

        if in_stock_only:
            if branch_id is not None and (branch_stock_val is None or branch_stock_val <= 0):
                continue
            elif branch_id is None and total_stock <= 0:
                continue

        item_dict = ProductResponse.model_validate(prod).model_dump()
        item_dict["branch_stock"] = branch_stock_val
        item_dict["total_stock"] = total_stock
        processed_items.append(ProductSearchResultItem(**item_dict))

    # Ordenamiento
    if sort_by == "price_asc":
        processed_items.sort(key=lambda x: x.base_price)
    elif sort_by == "price_desc":
        processed_items.sort(key=lambda x: x.base_price, reverse=True)
    elif sort_by == "rating":
        processed_items.sort(key=lambda x: (x.rating_avg, x.rating_count), reverse=True)
    else:  # newest
        processed_items.sort(key=lambda x: x.created_at, reverse=True)

    total = len(processed_items)
    page_size = max(1, limit)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    paged_items = processed_items[start : start + page_size]

    return ProductSearchResponse(
        items=paged_items,
        total=total,
        page=page,
        limit=page_size,
        total_pages=total_pages,
    )


@router.get("/products/{product_id}/branch-availability", response_model=ProductAvailabilityResponse)
def get_product_branch_availability(product_id: int, db: Session = Depends(get_db)):
    """[CU12] Desglose de disponibilidad y stock de cada variante por sucursal física."""
    prod = (
        db.query(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
        )
        .filter(Product.id == product_id)
        .first()
    )
    if not prod:
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    branches = db.query(Branch).filter(Branch.is_active == True).order_by(Branch.name.asc()).all()  # noqa: E712
    variant_ids = [v.id for v in prod.variants]

    inv_rows = (
        db.query(Inventory.branch_id, Inventory.variant_id, Inventory.stock_actual)
        .filter(Inventory.variant_id.in_(variant_ids))
        .all()
    )
    stock_lookup = {(r.branch_id, r.variant_id): int(r.stock_actual) for r in inv_rows}

    variant_results: List[VariantBranchStock] = []
    total_all = 0

    for v in prod.variants:
        b_details = []
        var_total = 0
        for b in branches:
            stk = stock_lookup.get((b.id, v.id), 0)
            var_total += stk
            b_details.append(
                BranchStockDetail(
                    branch_id=b.id,
                    branch_name=b.name,
                    branch_code=b.code,
                    city=b.city,
                    stock=stk,
                )
            )
        total_all += var_total
        variant_results.append(
            VariantBranchStock(
                variant_id=v.id,
                sku=v.sku,
                color_id=v.color.id,
                color_name=v.color.name,
                color_hex=v.color.hex_code,
                size_id=v.size.id,
                size_name=v.size.name,
                branches=b_details,
                total_stock=var_total,
            )
        )

    return ProductAvailabilityResponse(
        product_id=prod.id,
        product_name=prod.name,
        variants=variant_results,
        total_stock=total_all,
    )


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
# CU14 / CU14+ — Reseñas de prendas y Moderación
# ===================================================================
@router.get("/products/{product_id}/reviews", response_model=ProductReviewsResponse)
def list_reviews(
    product_id: int,
    db: Session = Depends(get_db),
    me: Optional[User] = Depends(get_optional_user),
):
    """[CU14] Lista las reseñas aprobadas de una prenda con su promedio y conteo (pública)"""
    if not db.query(Product.id).filter(Product.id == product_id).first():
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    me_id = me.id if me else None
    query = (
        db.query(ProductReview, User.first_name, User.last_name)
        .join(User, User.id == ProductReview.user_id)
        .filter(ProductReview.product_id == product_id)
    )

    if me_id:
        query = query.filter(
            (ProductReview.status == "APPROVED") | (ProductReview.user_id == me_id)
        )
    else:
        query = query.filter(ProductReview.status == "APPROVED")

    rows = query.order_by(ProductReview.created_at.desc()).all()

    items = [
        ReviewResponse(
            id=rv.id, rating=rv.rating, comment=rv.comment,
            author_name=f"{fn} {ln}".strip() or "Cliente",
            is_mine=(me_id is not None and rv.user_id == me_id),
            status=rv.status,
            created_at=rv.created_at,
        )
        for rv, fn, ln in rows
    ]
    # El promedio y conteo oficial solo considera las aprobadas
    approved_items = [i for i in items if i.status == "APPROVED"]
    count = len(approved_items)
    average = round(sum(i.rating for i in approved_items) / count, 1) if count else 0.0
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
        review.status = "APPROVED"
    else:
        review = ProductReview(
            product_id=product_id, user_id=current_user.id,
            rating=data.rating, comment=data.comment,
            status="APPROVED",
        )
        db.add(review)
    db.commit()
    db.refresh(review)

    log_event(db, current_user.id, action, "product_reviews", review.id,
              {"product_id": product_id, "rating": data.rating}, request.client.host)
    return ReviewResponse(
        id=review.id, rating=review.rating, comment=review.comment,
        author_name=f"{current_user.first_name} {current_user.last_name}".strip(),
        is_mine=True, status=review.status, created_at=review.created_at,
    )


@router.get("/admin/reviews", response_model=List[ReviewModerationItem])
def admin_list_reviews(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU14+] Listado administrativo de reseñas para moderación (SUPERADMIN)."""
    query = (
        db.query(ProductReview, Product.name.label("product_name"), User.first_name, User.last_name, User.email)
        .join(Product, Product.id == ProductReview.product_id)
        .join(User, User.id == ProductReview.user_id)
    )
    if status_filter:
        query = query.filter(ProductReview.status == status_filter.upper())
    rows = query.order_by(ProductReview.created_at.desc()).all()

    return [
        ReviewModerationItem(
            id=rv.id,
            product_id=rv.product_id,
            product_name=pname,
            user_id=rv.user_id,
            author_name=f"{fn} {ln}".strip() or "Cliente",
            author_email=email,
            rating=rv.rating,
            comment=rv.comment,
            status=rv.status,
            created_at=rv.created_at,
        )
        for rv, pname, fn, ln, email in rows
    ]


@router.put("/admin/reviews/{review_id}/moderate", response_model=ReviewModerationItem)
def admin_moderate_review(
    review_id: int,
    data: ReviewModerateAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU14+] Modera una reseña aprobándola o rechazándola (SUPERADMIN)."""
    rv = db.query(ProductReview).filter(ProductReview.id == review_id).first()
    if not rv:
        raise HTTPException(status_code=404, detail="Reseña no encontrada.")

    rv.status = data.status
    rv.moderated_at = func.now()
    rv.moderator_id = current_user.id
    db.commit()
    db.refresh(rv)

    log_event(db, current_user.id, "MODERATE", "product_reviews", rv.id,
              {"status": data.status}, request.client.host)

    prod = db.query(Product.name).filter(Product.id == rv.product_id).first()
    author = db.query(User).filter(User.id == rv.user_id).first()

    return ReviewModerationItem(
        id=rv.id,
        product_id=rv.product_id,
        product_name=prod[0] if prod else "Producto",
        user_id=rv.user_id,
        author_name=f"{author.first_name} {author.last_name}".strip() if author else "Cliente",
        author_email=author.email if author else "",
        rating=rv.rating,
        comment=rv.comment,
        status=rv.status,
        created_at=rv.created_at,
    )


# ===================================================================
# CU14 / CU14+ — Listas de Deseos (Wishlists Múltiples y Compartibles)
# ===================================================================

@router.get("/wishlist", response_model=List[ProductResponse])
def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14] Prendas marcadas como favoritas por el cliente (lista rápida/legacy)"""
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


@router.get("/wishlists", response_model=List[WishlistResponse])
def get_user_wishlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Listado de todas las listas de deseos creadas por el cliente con su conteo."""
    lists = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == current_user.id)
        .order_by(Wishlist.created_at.asc())
        .all()
    )
    if not lists:
        default_wl = Wishlist(
            user_id=current_user.id,
            name="Mis Favoritos",
            is_public=False,
            share_token=uuid.uuid4().hex[:16],
        )
        db.add(default_wl)
        db.commit()
        db.refresh(default_wl)
        lists = [default_wl]

    results = []
    for wl in lists:
        cnt = db.query(WishlistGroupItem).filter(WishlistGroupItem.wishlist_id == wl.id).count()
        results.append(
            WishlistResponse(
                id=wl.id,
                name=wl.name,
                is_public=wl.is_public,
                share_token=wl.share_token,
                created_at=wl.created_at,
                items_count=cnt,
            )
        )
    return results


@router.post("/wishlists", response_model=WishlistResponse, status_code=201)
def create_wishlist(
    data: WishlistCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Crea una nueva lista de deseos personalizada."""
    wl = Wishlist(
        user_id=current_user.id,
        name=data.name.strip(),
        is_public=data.is_public,
        share_token=uuid.uuid4().hex[:16],
    )
    db.add(wl)
    db.commit()
    db.refresh(wl)

    log_event(db, current_user.id, "INSERT", "wishlists", wl.id,
              {"name": wl.name, "is_public": wl.is_public}, request.client.host)

    return WishlistResponse(
        id=wl.id,
        name=wl.name,
        is_public=wl.is_public,
        share_token=wl.share_token,
        created_at=wl.created_at,
        items_count=0,
    )


@router.put("/wishlists/{wishlist_id}", response_model=WishlistResponse)
def update_wishlist(
    wishlist_id: int,
    data: WishlistUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Modifica el nombre o estado público de una lista de deseos."""
    wl = db.query(Wishlist).filter(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Lista de deseos no encontrada.")

    if data.name is not None:
        wl.name = data.name.strip()
    if data.is_public is not None:
        wl.is_public = data.is_public

    db.commit()
    db.refresh(wl)

    cnt = db.query(WishlistGroupItem).filter(WishlistGroupItem.wishlist_id == wl.id).count()
    log_event(db, current_user.id, "UPDATE", "wishlists", wl.id,
              {"name": wl.name, "is_public": wl.is_public}, request.client.host)

    return WishlistResponse(
        id=wl.id,
        name=wl.name,
        is_public=wl.is_public,
        share_token=wl.share_token,
        created_at=wl.created_at,
        items_count=cnt,
    )


@router.delete("/wishlists/{wishlist_id}", status_code=204)
def delete_wishlist(
    wishlist_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Elimina una lista de deseos y sus items asociados."""
    wl = db.query(Wishlist).filter(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Lista de deseos no encontrada.")

    db.delete(wl)
    db.commit()
    log_event(db, current_user.id, "DELETE", "wishlists", wishlist_id, {}, request.client.host)
    return None


@router.get("/wishlists/{wishlist_id}", response_model=WishlistDetailResponse)
def get_wishlist_detail(
    wishlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Obtiene el detalle de una lista de deseos con todas sus prendas."""
    wl = db.query(Wishlist).filter(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Lista de deseos no encontrada.")

    prods = (
        db.query(Product)
        .join(WishlistGroupItem, WishlistGroupItem.product_id == Product.id)
        .filter(WishlistGroupItem.wishlist_id == wl.id)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .order_by(WishlistGroupItem.created_at.desc())
        .all()
    )
    _attach_ratings(db, prods)

    return WishlistDetailResponse(
        id=wl.id,
        name=wl.name,
        is_public=wl.is_public,
        share_token=wl.share_token,
        created_at=wl.created_at,
        owner_name=f"{current_user.first_name} {current_user.last_name}".strip(),
        products=prods,
    )


@router.post("/wishlists/{wishlist_id}/items/{product_id}", status_code=201)
def add_item_to_wishlist(
    wishlist_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Agrega una prenda a una lista de deseos específica."""
    wl = db.query(Wishlist).filter(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Lista de deseos no encontrada.")

    if not db.query(Product.id).filter(Product.id == product_id).first():
        raise HTTPException(status_code=404, detail="Prenda no encontrada.")

    exists = db.query(WishlistGroupItem).filter(
        WishlistGroupItem.wishlist_id == wishlist_id,
        WishlistGroupItem.product_id == product_id,
    ).first()
    if not exists:
        item = WishlistGroupItem(wishlist_id=wishlist_id, product_id=product_id)
        db.add(item)
        db.commit()
        log_event(db, current_user.id, "INSERT", "wishlist_group_items", item.id,
                  {"wishlist_id": wishlist_id, "product_id": product_id}, request.client.host)

    return {"message": "Prenda añadida a la lista.", "product_id": product_id, "wishlist_id": wishlist_id}


@router.delete("/wishlists/{wishlist_id}/items/{product_id}", status_code=200)
def remove_item_from_wishlist(
    wishlist_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU14+] Elimina una prenda de una lista de deseos específica."""
    wl = db.query(Wishlist).filter(Wishlist.id == wishlist_id, Wishlist.user_id == current_user.id).first()
    if not wl:
        raise HTTPException(status_code=404, detail="Lista de deseos no encontrada.")

    deleted = db.query(WishlistGroupItem).filter(
        WishlistGroupItem.wishlist_id == wishlist_id,
        WishlistGroupItem.product_id == product_id,
    ).delete()
    db.commit()

    if deleted:
        log_event(db, current_user.id, "DELETE", "wishlist_group_items", product_id,
                  {"wishlist_id": wishlist_id, "product_id": product_id}, request.client.host)

    return {"message": "Prenda eliminada de la lista.", "product_id": product_id, "wishlist_id": wishlist_id}


@router.get("/wishlists/shared/{share_token}", response_model=WishlistDetailResponse)
def get_shared_wishlist(
    share_token: str,
    db: Session = Depends(get_db),
):
    """[CU14+] Consulta pública de una lista de deseos compartida por enlace (no requiere login si is_public=True)."""
    wl = db.query(Wishlist).filter(Wishlist.share_token == share_token).first()
    if not wl or not wl.is_public:
        raise HTTPException(status_code=404, detail="Lista de deseos pública no encontrada o es privada.")

    owner = db.query(User).filter(User.id == wl.user_id).first()
    prods = (
        db.query(Product)
        .join(WishlistGroupItem, WishlistGroupItem.product_id == Product.id)
        .filter(WishlistGroupItem.wishlist_id == wl.id)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.color),
            selectinload(Product.variants).selectinload(ProductVariant.size),
            selectinload(Product.images),
            selectinload(Product.category),
            selectinload(Product.season),
        )
        .order_by(WishlistGroupItem.created_at.desc())
        .all()
    )
    _attach_ratings(db, prods)

    return WishlistDetailResponse(
        id=wl.id,
        name=wl.name,
        is_public=wl.is_public,
        share_token=wl.share_token,
        created_at=wl.created_at,
        owner_name=f"{owner.first_name} {owner.last_name}".strip() if owner else "Usuario",
        products=prods,
    )


# ===================================================================
# GESTIÓN DE PROMOCIONES Y CUPONES (CU13)
# ===================================================================

@router.get("/coupons", response_model=List[CouponResponse])
def list_coupons(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check)
):
    """[CU13] Lista todos los cupones creados (Solo SUPERADMIN)."""
    return db.query(Coupon).order_by(Coupon.created_at.desc()).all()


@router.post("/coupons", response_model=CouponResponse, status_code=201)
def create_coupon(
    data: CouponCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Crea un nuevo cupón de descuento."""
    normalized_code = data.code.strip().upper()
    existing = db.query(Coupon).filter(Coupon.code == normalized_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="El código de cupón ya existe.")

    if data.valid_until <= data.valid_from:
        raise HTTPException(status_code=400, detail="La fecha de expiración debe ser posterior a la fecha de inicio.")

    coupon = Coupon(
        code=normalized_code,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        min_purchase_amount=data.min_purchase_amount,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        max_uses=data.max_uses,
        used_count=0,
        is_active=data.is_active,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    log_event(db, current_user.id, "INSERT", "coupons", coupon.id, {"code": coupon.code}, request.client.host)
    return coupon


@router.put("/coupons/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Actualiza un cupón existente."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado.")

    if data.code is not None:
        normalized_code = data.code.strip().upper()
        existing = db.query(Coupon).filter(Coupon.code == normalized_code, Coupon.id != coupon_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="El código de cupón ya existe.")
        coupon.code = normalized_code

    if data.discount_type is not None:
        coupon.discount_type = data.discount_type
    if data.discount_value is not None:
        coupon.discount_value = data.discount_value
    if data.min_purchase_amount is not None:
        coupon.min_purchase_amount = data.min_purchase_amount
    if data.valid_from is not None:
        coupon.valid_from = data.valid_from
    if data.valid_until is not None:
        coupon.valid_until = data.valid_until
    if data.max_uses is not None:
        coupon.max_uses = data.max_uses
    if data.is_active is not None:
        coupon.is_active = data.is_active

    if coupon.valid_until <= coupon.valid_from:
        raise HTTPException(status_code=400, detail="La fecha de expiración debe ser posterior a la fecha de inicio.")

    db.commit()
    db.refresh(coupon)
    log_event(db, current_user.id, "UPDATE", "coupons", coupon.id, {"code": coupon.code}, request.client.host)
    return coupon


@router.delete("/coupons/{coupon_id}", status_code=204)
def delete_coupon(
    coupon_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Elimina un cupón."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado.")
    db.delete(coupon)
    db.commit()
    log_event(db, current_user.id, "DELETE", "coupons", coupon_id, {"code": coupon.code}, request.client.host)
    return None


@router.post("/coupons/validate", response_model=CouponValidateResponse)
def validate_coupon(
    data: CouponValidateRequest,
    db: Session = Depends(get_db),
):
    """[CU13] Valida un código de cupón contra el monto del pedido (para carrito / checkout)."""
    normalized_code = data.code.strip().upper()
    coupon = db.query(Coupon).filter(Coupon.code == normalized_code).first()

    if not coupon:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message="El código de cupón no existe.",
        )

    if not coupon.is_active:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message="Este cupón se encuentra desactivado.",
        )

    now = datetime.now(coupon.valid_from.tzinfo) if coupon.valid_from.tzinfo else datetime.now()
    if now < coupon.valid_from:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message="Este cupón aún no está vigente.",
        )

    if now > coupon.valid_until:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message="Este cupón ha expirado.",
        )

    if coupon.used_count >= coupon.max_uses:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message="Este cupón alcanzó su límite máximo de usos.",
        )

    cart_total = float(data.cart_total)
    min_amount = float(coupon.min_purchase_amount)
    if cart_total < min_amount:
        return CouponValidateResponse(
            valid=False,
            code=normalized_code,
            message=f"La compra mínima para este cupón es de Bs. {min_amount:.2f}.",
        )

    # Calcular descuento
    disc_val = float(coupon.discount_value)
    if coupon.discount_type == "PORCENTAJE":
        discount_amount = round(cart_total * (disc_val / 100.0), 2)
    else:  # MONTO_FIJO
        discount_amount = min(cart_total, disc_val)

    new_total = max(0.0, round(cart_total - discount_amount, 2))

    return CouponValidateResponse(
        valid=True,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=disc_val,
        discount_amount=discount_amount,
        new_total=new_total,
        message=f"Cupón aplicado con éxito. Descuento: Bs. {discount_amount:.2f}.",
    )


# --- Campañas de Temporada (CU13) ---

@router.get("/promotions", response_model=List[SeasonalPromotionResponse])
def list_promotions(db: Session = Depends(get_db)):
    """[CU13] Lista todas las ofertas de temporada."""
    return (
        db.query(SeasonalPromotion)
        .options(selectinload(SeasonalPromotion.category))
        .order_by(SeasonalPromotion.created_at.desc())
        .all()
    )


@router.post("/promotions", response_model=SeasonalPromotionResponse, status_code=201)
def create_promotion(
    data: SeasonalPromotionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Crea una campaña de temporada."""
    if data.end_date <= data.start_date:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio.")

    promo = SeasonalPromotion(
        name=data.name,
        description=data.description,
        discount_percent=data.discount_percent,
        category_id=data.category_id,
        start_date=data.start_date,
        end_date=data.end_date,
        is_active=data.is_active,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    log_event(db, current_user.id, "INSERT", "seasonal_promotions", promo.id, {"name": promo.name}, request.client.host)
    return promo


@router.put("/promotions/{promo_id}", response_model=SeasonalPromotionResponse)
def update_promotion(
    promo_id: int,
    data: SeasonalPromotionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Actualiza una campaña de temporada."""
    promo = db.query(SeasonalPromotion).filter(SeasonalPromotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")

    if data.name is not None:
        promo.name = data.name
    if data.description is not None:
        promo.description = data.description
    if data.discount_percent is not None:
        promo.discount_percent = data.discount_percent
    if data.category_id is not None:
        promo.category_id = data.category_id
    if data.start_date is not None:
        promo.start_date = data.start_date
    if data.end_date is not None:
        promo.end_date = data.end_date
    if data.is_active is not None:
        promo.is_active = data.is_active

    if promo.end_date <= promo.start_date:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio.")

    db.commit()
    db.refresh(promo)
    log_event(db, current_user.id, "UPDATE", "seasonal_promotions", promo.id, {"name": promo.name}, request.client.host)
    return promo


@router.delete("/promotions/{promo_id}", status_code=204)
def delete_promotion(
    promo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_check),
):
    """[CU13] Elimina una campaña de temporada."""
    promo = db.query(SeasonalPromotion).filter(SeasonalPromotion.id == promo_id).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promoción no encontrada.")
    db.delete(promo)
    db.commit()
    log_event(db, current_user.id, "DELETE", "seasonal_promotions", promo_id, {"name": promo.name}, request.client.host)
    return None
