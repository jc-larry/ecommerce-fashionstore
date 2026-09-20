"""Controlador REST para Ofertas de Proveedores y Solicitudes de Reposición (CU08, CU10).

Flujo de negocio:
- El PROVEEDOR oferta nuevos modelos de prendas a Casa Matriz (SupplierOffer).
- Casa Matriz (SUPERADMIN/ADMINISTRADOR) aprueba o rechaza la oferta.
- Casa Matriz solicita reposición de una variante a un proveedor, indicando la
  sucursal que la necesita (SupplierReorderRequest.target_branch_id).
- El PROVEEDOR acepta/rechaza la solicitud y la marca como enviada.
- El ENCARGADO de la sucursal destino confirma la recepción: el stock ingresa al inventario.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.paquete_notificaciones.service import (
    notificar, notificar_varios, personal_de_sucursal, usuarios_de_proveedor, TIPO_SISTEMA,
)
from app.packages.paquete_inventario_y_proveedores.suppliers.models import Supplier
from app.packages.paquete_inventario_y_proveedores.suppliers.offer_models import SupplierOffer, SupplierReorderRequest, SupplierProductStatus
from app.packages.paquete_inventario_y_proveedores.suppliers.offer_schemas import (
    SupplierOfferCreate,
    SupplierOfferReview,
    SupplierOfferStatusUpdate,
    SupplierOfferResponse,
    SupplierReorderCreate,
    SupplierReorderRespond,
    SupplierReorderResponse,
    SupplierProductStatusResponse,
    SUPPLIER_PRODUCT_STATUSES,
)
import json
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant, ProductImage
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_seguridad_usuarios.routers import get_current_user, RoleChecker, _resolve_branch_id

router = APIRouter(prefix="/api/v1/suppliers", tags=["Proveedores - Ofertas y Reposición"])

CENTRAL_ROLES = ("SUPERADMIN", "ADMINISTRADOR")

admin_or_super = RoleChecker(allowed_roles=list(CENTRAL_ROLES))
staff_or_admin = RoleChecker(allowed_roles=[*CENTRAL_ROLES, "ENCARGADO"])
supplier_or_admin = RoleChecker(allowed_roles=[*CENTRAL_ROLES, "PROVEEDOR"])


def _is_central(user: User) -> bool:
    return any(r.name in CENTRAL_ROLES for r in user.roles)


def _own_supplier(db: Session, user: User) -> Optional[Supplier]:
    return db.query(Supplier).filter(Supplier.users.any(User.id == user.id)).first()


def _require_own_supplier(db: Session, user: User) -> Supplier:
    supplier = _own_supplier(db, user)
    if not supplier:
        raise HTTPException(status_code=403, detail="Tu usuario no está vinculado a ningún proveedor.")
    return supplier


def product_cover_image(db: Session, product_id: int, color_id: Optional[int] = None) -> Optional[str]:
    """Foto de la prenda: la del color pedido si existe, si no la principal."""
    images = db.query(ProductImage).filter(ProductImage.product_id == product_id).all()
    if not images:
        return None
    images.sort(key=lambda i: (i.color_id != color_id if color_id else True, not i.is_primary, i.id))
    return images[0].image_url


def get_supplier_product_status(db: Session, supplier_id: int, product_id: int) -> str:
    """Estado declarado por el proveedor para la prenda (DISPONIBLE si nunca lo indicó)."""
    row = db.query(SupplierProductStatus).filter(
        SupplierProductStatus.supplier_id == supplier_id,
        SupplierProductStatus.product_id == product_id,
    ).first()
    if row:
        return row.status
    linked = db.query(SupplierOffer).filter(
        SupplierOffer.supplier_id == supplier_id,
        SupplierOffer.product_id == product_id,
        SupplierOffer.status.in_(["AGOTADO", "DESCONTINUADO"]),
    ).first()
    return linked.status if linked else "DISPONIBLE"


def set_supplier_product_status(db: Session, supplier_id: int, product_id: int, new_status: str) -> None:
    row = db.query(SupplierProductStatus).filter(
        SupplierProductStatus.supplier_id == supplier_id,
        SupplierProductStatus.product_id == product_id,
    ).first()
    if row:
        row.status = new_status
    else:
        db.add(SupplierProductStatus(supplier_id=supplier_id, product_id=product_id, status=new_status))


def _offer_response(offer: SupplierOffer) -> SupplierOfferResponse:
    payload = {c.name: getattr(offer, c.name) for c in offer.__table__.columns}
    payload["image_urls"] = json.loads(offer.image_urls) if offer.image_urls else ([offer.image_url] if offer.image_url else [])
    data = SupplierOfferResponse.model_validate(payload)
    data.supplier_name = offer.supplier.name if offer.supplier else None
    data.target_branch_name = offer.target_branch.name if offer.target_branch else None
    return data


def _reorder_response(reorder: SupplierReorderRequest, db: Optional[Session] = None) -> SupplierReorderResponse:
    data = SupplierReorderResponse.model_validate(reorder)
    variant = reorder.variant
    data.code = f"RP-{reorder.id:04d}"
    data.supplier_name = reorder.supplier.name if reorder.supplier else None
    data.target_branch_name = reorder.target_branch.name if reorder.target_branch else None
    if reorder.requested_by:
        data.requested_by_name = f"{reorder.requested_by.first_name} {reorder.requested_by.last_name}".strip()
    if variant:
        data.sku = variant.sku
        data.product_name = variant.product.name if variant.product else None
        parts = [p for p in (variant.size.name if variant.size else None, variant.color.name if variant.color else None) if p]
        data.variant_label = " / ".join(parts) or None
        data.product_id = variant.product_id
        if db is not None:
            data.product_image_url = product_cover_image(db, variant.product_id, variant.color_id)
    return data


def _nombre_variante(db: Session, variant_id: int) -> str:
    """'Prenda (talla/color)' para los mensajes de notificación."""
    v = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not v:
        return f"variante #{variant_id}"
    nombre = v.product.name if v.product else "Prenda"
    return f"{nombre} ({v.size.name if v.size else '-'}/{v.color.name if v.color else '-'})"


def _central_ids(db: Session) -> list:
    """Usuarios activos de Casa Matriz."""
    return [u.id for u in db.query(User).filter(User.is_active == True).all()
            if any(r.name in CENTRAL_ROLES for r in u.roles)]


def _get_reorder(db: Session, reorder_id: int) -> SupplierReorderRequest:
    reorder = db.query(SupplierReorderRequest).filter(SupplierReorderRequest.id == reorder_id).first()
    if not reorder:
        raise HTTPException(status_code=404, detail="Solicitud de reposición no encontrada")
    return reorder


def _check_supplier_owns(db: Session, user: User, reorder: SupplierReorderRequest) -> None:
    """Un PROVEEDOR solo puede actuar sobre solicitudes dirigidas a su propio proveedor."""
    if _is_central(user):
        return
    supplier = _require_own_supplier(db, user)
    if reorder.supplier_id != supplier.id:
        raise HTTPException(status_code=403, detail="Esta solicitud de reposición no está dirigida a tu empresa.")


# ===================================================================
# OFERTAS DE PRENDAS DEL PROVEEDOR AL ADMIN (CU08)
# ===================================================================

@router.post("/offers", response_model=SupplierOfferResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_offer(
    data: SupplierOfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_or_admin),
):
    """[CU08] El proveedor oferta un nuevo modelo de prenda a Casa Matriz.

    Un PROVEEDOR siempre oferta a nombre de su propio proveedor vinculado (se ignora
    cualquier supplier_id enviado), para que no pueda suplantar a otra empresa.
    """
    if _is_central(current_user):
        if data.supplier_id is None:
            raise HTTPException(status_code=400, detail="Indica el proveedor de la oferta.")
        supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    else:
        supplier = _require_own_supplier(db, current_user)

    offer = SupplierOffer(
        supplier_id=supplier.id,
        product_name=data.product_name,
        description=data.description,
        category=data.category,
        unit_cost=data.unit_cost,
        suggested_retail_price=data.suggested_retail_price,
        min_order_quantity=data.min_order_quantity,
        available_quantity=data.available_quantity,
        sizes_available=data.sizes_available,
        colors_available=data.colors_available,
        image_url=(data.image_url if data.image_url in data.image_urls else None) or (data.image_urls[0] if data.image_urls else None),
        image_urls=json.dumps(data.image_urls) if data.image_urls else None,
        status="PENDING",
    )
    db.add(offer)
    notificar_varios(db, _central_ids(db), "Nueva oferta de proveedor",
                     f"{supplier.name} ofertó el modelo '{data.product_name}'.", TIPO_SISTEMA, None, "SUPPLIER_OFFER")
    db.commit()
    db.refresh(offer)
    return _offer_response(offer)


@router.get("/offers", response_model=List[SupplierOfferResponse])
def list_supplier_offers(
    status_filter: Optional[str] = Query(None, description="PENDING, APPROVED, REJECTED, DESCONTINUADO, AGOTADO"),
    supplier_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU08] Bandeja de Casa Matriz con todas las ofertas enviadas por proveedores."""
    q = db.query(SupplierOffer)
    if status_filter:
        q = q.filter(SupplierOffer.status == status_filter.upper())
    if supplier_id:
        q = q.filter(SupplierOffer.supplier_id == supplier_id)
    return [_offer_response(o) for o in q.order_by(SupplierOffer.created_at.desc()).all()]


@router.get("/offers/my", response_model=List[SupplierOfferResponse])
def list_my_supplier_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU08] El proveedor consulta las ofertas que ha remitido y su estado de revisión."""
    supplier = _own_supplier(db, current_user)
    if not supplier:
        return []
    offers = (
        db.query(SupplierOffer)
        .filter(SupplierOffer.supplier_id == supplier.id)
        .order_by(SupplierOffer.created_at.desc())
        .all()
    )
    return [_offer_response(o) for o in offers]


@router.patch("/offers/{offer_id}/review", response_model=SupplierOfferResponse)
def review_supplier_offer(
    offer_id: int,
    data: SupplierOfferReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU08] Casa Matriz aprueba o rechaza una oferta y puede indicar la sucursal destino."""
    offer = db.query(SupplierOffer).filter(SupplierOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    new_status = data.status.upper()
    if new_status not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="El estado debe ser APPROVED o REJECTED.")
    if offer.status not in ("PENDING", "DESCONTINUADO", "AGOTADO"):
        raise HTTPException(status_code=400, detail="Esta oferta ya fue revisada.")

    if data.target_branch_id:
        branch = db.query(Branch).filter(Branch.id == data.target_branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Sucursal de destino no encontrada")
        offer.target_branch_id = data.target_branch_id

    if data.product_id:
        if not db.query(Product).filter(Product.id == data.product_id).first():
            raise HTTPException(status_code=404, detail="Prenda del catálogo no encontrada")
        offer.product_id = data.product_id
        if new_status == "APPROVED":
            set_supplier_product_status(db, offer.supplier_id, data.product_id, "DISPONIBLE")

    offer.status = new_status
    offer.admin_notes = data.admin_notes
    offer.reviewed_by_id = current_user.id
    offer.reviewed_at = datetime.now()

    veredicto = "aprobada" if new_status == "APPROVED" else "rechazada"
    notificar_varios(db, usuarios_de_proveedor(db, offer.supplier_id), f"Oferta {veredicto}",
                     f"Casa Matriz revisó tu oferta '{offer.product_name}': {veredicto}.",
                     TIPO_SISTEMA, offer.id, "SUPPLIER_OFFER")
    db.commit()
    db.refresh(offer)
    return _offer_response(offer)


@router.patch("/offers/{offer_id}/status", response_model=SupplierOfferResponse)
def update_supplier_offer_status(
    offer_id: int,
    data: SupplierOfferStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El proveedor marca una prenda ofertada y aprobada como DISPONIBLE, AGOTADO o DESCONTINUADO.

    La aprobación o rechazo de la oferta es exclusiva de Casa Matriz (ver /review).
    """
    offer = db.query(SupplierOffer).filter(SupplierOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    if not _is_central(current_user):
        supplier = _require_own_supplier(db, current_user)
        if offer.supplier_id != supplier.id:
            raise HTTPException(status_code=403, detail="No puedes modificar la oferta de otra empresa.")

    new_status = data.status.upper()
    if new_status not in SUPPLIER_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="El estado debe ser DISPONIBLE, AGOTADO o DESCONTINUADO.")
    if offer.status in ("PENDING", "REJECTED"):
        raise HTTPException(status_code=400, detail="Solo puedes cambiar la disponibilidad de una prenda ya aprobada.")

    offer.status = new_status
    if offer.product_id:
        set_supplier_product_status(db, offer.supplier_id, offer.product_id, new_status)
    if data.available_quantity is not None:
        offer.available_quantity = data.available_quantity
    if data.admin_notes:
        offer.admin_notes = data.admin_notes

    db.commit()
    db.refresh(offer)
    return _offer_response(offer)


# ===================================================================
# SOLICITUDES DE REPOSICIÓN (CASA MATRIZ -> PROVEEDOR, CON SUCURSAL DESTINO) (CU08, CU10)
# ===================================================================

@router.post("/reorder-requests", response_model=SupplierReorderResponse, status_code=status.HTTP_201_CREATED)
def create_reorder_request(
    data: SupplierReorderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU08] Casa Matriz pide reposición de una prenda a un proveedor.

    Valida disponibilidad del proveedor: Si la prenda fue descontinuada o no tiene stock disponible, se bloquea la solicitud.
    """
    supplier = db.query(Supplier).filter(Supplier.id == data.supplier_id).first()
    if not supplier or not supplier.is_active:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado o inactivo")

    variant = db.query(ProductVariant).filter(ProductVariant.id == data.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variante de prenda no encontrada")

    branch = db.query(Branch).filter(Branch.id == data.target_branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal de destino no encontrada")

    # El proveedor declaró que ya no trae (o no tiene) esta prenda: no se le puede pedir.
    product_status = get_supplier_product_status(db, supplier.id, variant.product_id)
    if product_status != "DISPONIBLE":
        motivo = "ya no trae" if product_status == "DESCONTINUADO" else "no tiene stock de"
        raise HTTPException(
            status_code=400,
            detail=f"No se puede pedir: {supplier.name} {motivo} la prenda '{variant.product.name}'.",
        )

    reorder = SupplierReorderRequest(
        supplier_id=data.supplier_id,
        variant_id=data.variant_id,
        requested_quantity=data.requested_quantity,
        target_branch_id=data.target_branch_id,
        unit_cost=data.unit_cost,
        status="PENDING",
        requested_by_id=current_user.id,
    )
    db.add(reorder)
    db.flush()
    notificar_varios(db, usuarios_de_proveedor(db, data.supplier_id), "Nuevo pedido de reposición",
                     f"Casa Matriz pide {data.requested_quantity} u. de {_nombre_variante(db, data.variant_id)}.",
                     TIPO_SISTEMA, reorder.id, "REORDER")
    db.commit()
    db.refresh(reorder)
    return _reorder_response(reorder, db)


@router.get("/reorder-requests", response_model=List[SupplierReorderResponse])
def list_reorder_requests(
    status_filter: Optional[str] = Query(None),
    branch_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_or_admin),
):
    """[CU08] Solicitudes de reposición. Un ENCARGADO solo ve las dirigidas a su sucursal."""
    q = db.query(SupplierReorderRequest)
    if not _is_central(current_user):
        own_branch = _resolve_branch_id(current_user, db)
        if own_branch is None:
            raise HTTPException(status_code=403, detail="Tu usuario no tiene una sucursal asignada.")
        branch_id = own_branch
    if status_filter:
        q = q.filter(SupplierReorderRequest.status == status_filter.upper())
    if branch_id:
        q = q.filter(SupplierReorderRequest.target_branch_id == branch_id)
    if supplier_id:
        q = q.filter(SupplierReorderRequest.supplier_id == supplier_id)
    return [_reorder_response(r, db) for r in q.order_by(SupplierReorderRequest.created_at.desc()).all()]


@router.get("/reorder-requests/my", response_model=List[SupplierReorderResponse])
def list_my_reorder_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU08] Bandeja del proveedor: pedidos de reposición que Casa Matriz le ha enviado."""
    supplier = _own_supplier(db, current_user)
    if not supplier:
        return []
    reorders = (
        db.query(SupplierReorderRequest)
        .filter(SupplierReorderRequest.supplier_id == supplier.id)
        .order_by(SupplierReorderRequest.created_at.desc())
        .all()
    )
    return [_reorder_response(r, db) for r in reorders]


@router.patch("/reorder-requests/{reorder_id}/respond", response_model=SupplierReorderResponse)
def respond_reorder_request(
    reorder_id: int,
    data: SupplierReorderRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_or_admin),
):
    """[CU08] El proveedor acepta (con fecha estimada) o rechaza una solicitud pendiente."""
    reorder = _get_reorder(db, reorder_id)
    _check_supplier_owns(db, current_user, reorder)
    new_status = data.status.upper()
    if new_status not in ("ACCEPTED", "REJECTED"):
        raise HTTPException(status_code=400, detail="El estado debe ser ACCEPTED o REJECTED.")
    if reorder.status != "PENDING":
        raise HTTPException(status_code=400, detail="Solo se puede responder una solicitud pendiente.")

    reorder.status = new_status
    reorder.estimated_delivery = data.estimated_delivery
    reorder.supplier_notes = data.supplier_notes
    reorder.updated_at = datetime.now()

    respuesta = "aceptó" if new_status == "ACCEPTED" else "rechazó"
    notificar(db, reorder.requested_by_id, f"El proveedor {respuesta} la reposición",
              f"Pedido #{reorder.id} de {_nombre_variante(db, reorder.variant_id)}: {respuesta}.",
              TIPO_SISTEMA, reorder.id, "REORDER")
    db.commit()
    db.refresh(reorder)
    return _reorder_response(reorder, db)


@router.patch("/reorder-requests/{reorder_id}/mark-shipped", response_model=SupplierReorderResponse)
def mark_reorder_shipped(
    reorder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(supplier_or_admin),
):
    """[CU08] El proveedor notifica que despachó la mercadería hacia la sucursal destino."""
    reorder = _get_reorder(db, reorder_id)
    _check_supplier_owns(db, current_user, reorder)
    if reorder.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="Solo se puede despachar una solicitud aceptada.")

    reorder.status = "SHIPPED"
    reorder.updated_at = datetime.now()
    notificar_varios(db, personal_de_sucursal(db, reorder.target_branch_id), "Mercadería en camino",
                     f"El proveedor despachó {reorder.requested_quantity} u. de {_nombre_variante(db, reorder.variant_id)}. Confirma la recepción al llegar.",
                     TIPO_SISTEMA, reorder.id, "REORDER")
    db.commit()
    db.refresh(reorder)
    return _reorder_response(reorder, db)


@router.patch("/reorder-requests/{reorder_id}/cancel", response_model=SupplierReorderResponse)
def cancel_reorder_request(
    reorder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU08] Casa Matriz anula una solicitud que aún no fue despachada."""
    reorder = _get_reorder(db, reorder_id)
    if reorder.status not in ("PENDING", "ACCEPTED"):
        raise HTTPException(status_code=400, detail="Solo se puede anular una solicitud pendiente o aceptada.")
    reorder.status = "CANCELLED"
    reorder.updated_at = datetime.now()
    db.commit()
    db.refresh(reorder)
    return _reorder_response(reorder, db)


@router.patch("/reorder-requests/{reorder_id}/mark-received", response_model=SupplierReorderResponse)
def mark_reorder_received(
    reorder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_or_admin),
):
    """[CU10] La sucursal destino confirma la recepción física de la mercadería.

    Solo el ENCARGADO de la sucursal destino (o Casa Matriz) puede confirmarla. Carga el
    stock al inventario de esa sucursal con costo promedio ponderado y lo registra en el kardex.
    """
    reorder = _get_reorder(db, reorder_id)
    if not _is_central(current_user) and _resolve_branch_id(current_user, db) != reorder.target_branch_id:
        raise HTTPException(status_code=403, detail="Solo la sucursal destino puede confirmar esta recepción.")
    if reorder.status == "RECEIVED":
        raise HTTPException(status_code=400, detail="Esta mercadería ya fue recibida e ingresada a inventario")
    if reorder.status != "SHIPPED":
        raise HTTPException(status_code=400, detail="El proveedor aún no despachó esta solicitud.")

    inv = (
        db.query(Inventory)
        .filter(
            Inventory.branch_id == reorder.target_branch_id,
            Inventory.variant_id == reorder.variant_id,
        )
        .with_for_update()
        .first()
    )

    prev_stock = inv.stock_actual if inv else 0
    new_stock = prev_stock + reorder.requested_quantity

    if inv:
        if new_stock > 0 and reorder.unit_cost > 0:
            total_val = (prev_stock * float(inv.avg_cost)) + (reorder.requested_quantity * float(reorder.unit_cost))
            inv.avg_cost = total_val / new_stock
        inv.stock_actual = new_stock
        inv.updated_at = datetime.now()
    else:
        inv = Inventory(
            branch_id=reorder.target_branch_id,
            variant_id=reorder.variant_id,
            stock_actual=new_stock,
            avg_cost=reorder.unit_cost,
        )
        db.add(inv)

    ledger = InventoryLedger(
        branch_id=reorder.target_branch_id,
        variant_id=reorder.variant_id,
        movement_type="INGRESO",
        quantity=reorder.requested_quantity,
        reference_id=f"REORDER-{reorder.id}",
        unit_cost=reorder.unit_cost,
    )
    db.add(ledger)

    reorder.status = "RECEIVED"
    reorder.updated_at = datetime.now()
    notificar(db, reorder.requested_by_id, "Reposición recibida en sucursal",
              f"Pedido #{reorder.id}: la sucursal recibió {reorder.requested_quantity} u. de {_nombre_variante(db, reorder.variant_id)}.",
              TIPO_SISTEMA, reorder.id, "REORDER")

    db.commit()
    db.refresh(reorder)
    return _reorder_response(reorder, db)


# ===================================================================
# DISPONIBILIDAD DEL PROVEEDOR POR PRENDA DEL CATÁLOGO
# ===================================================================

@router.get("/product-status", response_model=SupplierProductStatusResponse)
def read_supplier_product_status(
    supplier_id: int = Query(...),
    product_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """Casa Matriz consulta si el proveedor todavía trae una prenda antes de pedir reposición."""
    return SupplierProductStatusResponse(
        supplier_id=supplier_id,
        product_id=product_id,
        status=get_supplier_product_status(db, supplier_id, product_id),
    )
