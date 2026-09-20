"""Controlador API REST del paquete Reservas y Citas.
Casos de Uso:
- [CU26] Agendar reserva de prendas para probador físico (Fitting Room).
- [CU27] Bandeja Kanban de preparación de prendas por dependientes de sucursal.
- [CU28] Cancelación de reserva y liberación inmediata de stock apartado (HOLD).
- [CU25] Conversión directa de reserva física en venta presencial POS con factura IVA 13%.
"""
import uuid
from datetime import datetime, timedelta, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import Product, ProductVariant, Size, Color
from app.packages.inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger
from app.packages.reservas_y_citas.models import Reservation, ReservationItem
from app.packages.reservas_y_citas.schemas import (
    ReservationCreate,
    ReservationResponse,
    ReservationItemResponse,
    ReservationStatusUpdate,
    ReservationConvertToPOSRequest,
    ReservationReschedule,
)
from app.packages.seguridad_y_usuarios.models import User
from app.packages.seguridad_y_usuarios.routers import get_current_user, _resolve_branch_id

from app.packages.ventas_y_pagos.models import (
    Order, OrderItem, Payment, EfectivoPayment, TarjetaPayment, QRPayment, Invoice, CashShift
)
from app.packages.ventas_y_pagos.paypal_service import paypal_service
from app.packages.notificaciones.service import (
    notificar, notificar_varios, personal_de_sucursal, TIPO_RESERVA,
)

router = APIRouter(prefix="/api/v1/reservations", tags=["Reservas y Citas (Fitting Room)"])

CENTRAL_ROLES = {"SUPERADMIN", "ADMINISTRADOR"}
BRANCH_STAFF_ROLES = {"ENCARGADO", "CAJERO"}


def _staff_branch(user: User, db: Session) -> tuple:
    """(es_personal, sucursal) — sucursal None = Casa Matriz (ve todas)."""
    roles = {r.name for r in user.roles}
    if roles & CENTRAL_ROLES:
        return True, None
    if roles & BRANCH_STAFF_ROLES:
        branch_id = _resolve_branch_id(user, db)
        if branch_id is None:
            raise HTTPException(status_code=403, detail="Tu usuario no tiene una sucursal asignada.")
        return True, branch_id
    return False, None


# Mensajes al cliente por cada estado de su reserva (CU40).
AVISOS_RESERVA = {
    "PENDING": ("Reserva confirmada", "Tu reserva {codigo} en {sucursal} quedó registrada para el {cita}. Las prendas están apartadas."),
    "PREPARING": ("Estamos preparando tu probador", "La sucursal {sucursal} está preparando las prendas de tu reserva {codigo}."),
    "READY": ("Tu probador está listo", "Las prendas de tu reserva {codigo} te esperan en el vestidor de {sucursal}."),
    "LATE": ("Tu cita ya comenzó", "Pasaron más de 15 minutos de tu cita {codigo} en {sucursal}. Si no llegas en 30 minutos, la reserva se libera."),
    "NO_SHOW": ("Reserva liberada por inasistencia", "No asististe a tu cita {codigo}; las prendas volvieron al stock de {sucursal}."),
    "COMPLETED": ("Compra de tu reserva completada", "Tu reserva {codigo} se convirtió en venta en {sucursal}. ¡Gracias por tu compra!"),
    "CANCELLED": ("Reserva cancelada", "Tu reserva {codigo} en {sucursal} fue cancelada y las prendas volvieron al stock."),
    "EXPIRED": ("Reserva vencida", "Tu reserva {codigo} en {sucursal} venció."),
}


def _texto_cita(res: Reservation) -> str:
    if res.appointment_date:
        hora = f" a las {res.appointment_time}" if res.appointment_time else ""
        return f"{res.appointment_date.strftime('%d/%m/%Y')}{hora}"
    return "la fecha acordada"


def _avisar_reserva(res: Reservation, db: Session, estado: Optional[str] = None) -> None:
    """Notifica al cliente el estado de su reserva (no hace commit)."""
    estado = estado or res.status
    if estado not in AVISOS_RESERVA:
        return
    branch = db.query(Branch).filter(Branch.id == res.branch_id).first()
    titulo, plantilla = AVISOS_RESERVA[estado]
    notificar(
        db, res.customer_id, titulo,
        plantilla.format(codigo=res.reservation_code, sucursal=branch.name if branch else "la sucursal", cita=_texto_cita(res)),
        TIPO_RESERVA, res.id, "RESERVATION",
    )


def _avisar_personal(res: Reservation, db: Session, titulo: str, mensaje: str) -> None:
    """Avisa al encargado de la sucursal (campana del panel)."""
    notificar_varios(db, personal_de_sucursal(db, res.branch_id), titulo, mensaje, TIPO_RESERVA, res.id, "RESERVATION")


def _get_accessible_reservation(reservation_id: int, user: User, db: Session, staff_only: bool = False) -> Reservation:
    """La reserva la ve su cliente o el personal de la sucursal donde se atiende (o Casa Matriz)."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")
    is_staff, branch_id = _staff_branch(user, db)
    if is_staff:
        if branch_id is not None and reservation.branch_id != branch_id:
            raise HTTPException(status_code=404, detail="Reserva no encontrada.")
        return reservation
    if staff_only or reservation.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Reserva no encontrada.")
    return reservation


def _build_reservation_response(res: Reservation, db: Session) -> ReservationResponse:
    # Chequeo dinámico de tolerancia de citas (15 min -> LATE, 30 min -> NO_SHOW)
    if res.appointment_date and res.appointment_time and res.status in ["PENDING", "PREPARING", "READY"]:
        try:
            parts = res.appointment_time.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            apt_datetime = datetime.combine(res.appointment_date, datetime.min.time()).replace(hour=hour, minute=minute)
            now = datetime.now()
            diff_minutes = (now - apt_datetime).total_seconds() / 60.0

            if diff_minutes > 30 and res.status != "NO_SHOW":
                res.status = "NO_SHOW"
                _release_reservation_stock(res, db)
                _avisar_reserva(res, db)
                db.commit()
            elif diff_minutes > 15 and res.status not in ["LATE", "NO_SHOW"]:
                res.status = "LATE"
                _avisar_reserva(res, db)
                db.commit()
        except Exception:
            pass

    items_out = []
    for it in res.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == it.variant_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
        size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
        color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None

        img_url = None
        if prod and prod.images:
            color_img = next((im for im in prod.images if variant and im.color_id == variant.color_id), None)
            if color_img:
                img_url = color_img.image_url
            else:
                primary_img = next((im for im in prod.images if im.is_primary), None)
                img_url = primary_img.image_url if primary_img else prod.images[0].image_url

        items_out.append(
            ReservationItemResponse(
                id=it.id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                unit_price=float(it.unit_price),
                notes=it.notes,
                product_name=prod.name if prod else "Prenda",
                size_name=size.name if size else "Única",
                color_name=color.name if color else "Estándar",
                sku=variant.sku if variant else None,
                image_url=img_url,
            )
        )

    branch = db.query(Branch).filter(Branch.id == res.branch_id).first()
    customer = db.query(User).filter(User.id == res.customer_id).first()

    tot_amt = float(getattr(res, "total_amount", 0.0) or 0.0)
    dep_amt = float(getattr(res, "deposit_amount", 0.0) or 0.0)
    bal_due = max(0.0, round(tot_amt - dep_amt, 2))

    return ReservationResponse(
        id=res.id,
        reservation_code=res.reservation_code,
        customer_id=res.customer_id,
        customer_name=f"{customer.first_name} {customer.last_name}".strip() if customer else "Cliente",
        customer_email=customer.email if customer else None,
        customer_phone=customer.phone if customer else None,
        branch_id=res.branch_id,
        branch_name=branch.name if branch else "Sucursal",
        branch_address=branch.address if branch else None,
        status=res.status,
        appointment_date=res.appointment_date,
        appointment_time=res.appointment_time,
        reschedule_count=res.reschedule_count or 0,
        reserved_at=res.reserved_at,
        expires_at=res.expires_at,
        notes=res.notes,
        total_amount=tot_amt,
        deposit_amount=dep_amt,
        balance_due=bal_due,
        payment_method=getattr(res, "payment_method", "TARJETA") or "TARJETA",
        payment_reference=getattr(res, "payment_reference", None),
        deposit_paid=bool(getattr(res, "deposit_paid", True)),
        completed_sale_id=res.completed_sale_id,
        items=items_out,
        created_at=res.created_at,
    )


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    data: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU26] Agendar reserva física para probador con bloqueo de stock (HOLD 48h máx 5 prendas y seña 50%)."""
    # 1. Validar sucursal
    branch = db.query(Branch).filter(Branch.id == data.branch_id).first()
    if not branch or not branch.is_active:
        raise HTTPException(status_code=400, detail="Sucursal no válida o inactiva.")

    # 1.1 Validar fecha y hora de cita si fueron provistas
    if data.appointment_date:
        today = date.today()
        if data.appointment_date < today:
            raise HTTPException(status_code=400, detail="La fecha de la cita no puede ser anterior a la fecha de hoy.")
        if data.appointment_date > today + timedelta(days=30):
            raise HTTPException(status_code=400, detail="No es posible agendar citas con más de 30 días de anticipación.")

    if data.appointment_time:
        try:
            parts = data.appointment_time.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            time_val = f"{hour:02d}:{minute:02d}"
            # Comparar con horario de apertura y cierre de sucursal
            open_t = getattr(branch, "opening_time", "09:00") or "09:00"
            close_t = getattr(branch, "closing_time", "21:00") or "21:00"
            if time_val < open_t or time_val > close_t:
                raise HTTPException(
                    status_code=400,
                    detail=f"La hora de la cita ({time_val}) debe estar dentro del horario de atención de la sucursal ({open_t} - {close_t})."
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de hora de cita no válido. Use 'HH:MM'.")

    # 2. Validar límite máximo de 5 prendas por reserva
    total_qty = sum(item.quantity for item in data.items)
    if total_qty > 5:
        raise HTTPException(status_code=400, detail="El límite por reserva es de hasta 5 prendas.")

    # 3. Validar disponibilidad de stock en la sucursal seleccionada
    items_to_reserve = []
    for item_in in data.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item_in.variant_id).first()
        if not variant or not variant.is_active:
            raise HTTPException(status_code=404, detail=f"Variante #{item_in.variant_id} no disponible.")

        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == item_in.variant_id,
        ).with_for_update().first()

        current_stock = inv.stock_actual if inv else 0
        if current_stock < item_in.quantity:
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            prod_name = prod.name if prod else "Prenda"
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en la sucursal para '{prod_name}'. Disponible: {current_stock}, Solicitado: {item_in.quantity}."
            )

        prod = db.query(Product).filter(Product.id == variant.product_id).first()
        price = float(prod.base_price if prod else 0.0)
        items_to_reserve.append((variant, inv, item_in.quantity, price, item_in.notes))

    # 4. Calcular total de prendas y seña del 50%
    total_amount = round(sum(price * qty for _, _, qty, price, _ in items_to_reserve), 2)
    deposit_amount = round(total_amount * 0.50, 2)

    # 5. Generar código único de reserva (RES-XXXXXX)
    code = f"RES-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now()
    reserved_date = data.reserved_at if data.reserved_at else now
    # Expiración por defecto: 48 horas desde la fecha de reserva
    expires_date = reserved_date + timedelta(hours=48)

    p_method = (data.payment_method or "TARJETA").upper()
    if p_method not in ("TARJETA", "PAYPAL", "QR"):
        p_method = "TARJETA"
    if p_method == "PAYPAL":
        # La seña por PayPal se verifica con la pasarela antes de apartar las prendas.
        ref = data.payment_reference or ""
        if not ref.startswith("PAYPAL:"):
            raise HTTPException(status_code=400, detail="Falta la orden de PayPal de la seña.")
        paypal_service.verify_completed_order(ref.split(":", 1)[1], deposit_amount)
    p_ref = data.payment_reference or f"{p_method}-TX-{uuid.uuid4().hex[:8].upper()}"

    reservation = Reservation(
        reservation_code=code,
        customer_id=current_user.id,
        branch_id=data.branch_id,
        status="PENDING",
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        reschedule_count=0,
        reserved_at=reserved_date,
        expires_at=expires_date,
        notes=data.notes,
        total_amount=total_amount,
        deposit_amount=deposit_amount,
        payment_method=p_method,
        payment_reference=p_ref,
        deposit_paid=True,
    )
    db.add(reservation)
    db.flush()

    # 5. Apartar stock (HOLD) e insertar items
    for variant, inv, qty, price, item_notes in items_to_reserve:
        # Descontar stock físico temporalmente para asegurar disponibilidad
        inv.stock_actual -= qty

        # Registrar movimiento en el libro mayor de inventario
        db.add(
            InventoryLedger(
                branch_id=data.branch_id,
                variant_id=variant.id,
                quantity=-qty,
                movement_type="RESERVA",
                unit_cost=float(inv.avg_cost or 0),
                reference_id=code,
            )
        )

        db.add(
            ReservationItem(
                reservation_id=reservation.id,
                variant_id=variant.id,
                quantity=qty,
                unit_price=price,
                notes=item_notes,
            )
        )

    _avisar_reserva(reservation, db, "PENDING")
    _avisar_personal(
        reservation, db, "Nueva reserva de probador",
        f"{reservation.reservation_code}: {total_qty} prenda(s) para el {_texto_cita(reservation)}. Seña pagada: Bs. {deposit_amount:.2f} ({p_method}).",
    )
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)


@router.get("/my", response_model=List[ReservationResponse])
def get_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU26] Listar reservas del cliente autenticado."""
    reservations = (
        db.query(Reservation)
        .filter(Reservation.customer_id == current_user.id)
        .order_by(Reservation.created_at.desc())
        .all()
    )
    return [_build_reservation_response(r, db) for r in reservations]


@router.get("", response_model=List[ReservationResponse])
def list_reservations(
    branch_id: Optional[int] = Query(None, description="Filtrar por sucursal"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU27] Bandeja de reservas del personal. Encargado y cajero solo ven las de su sucursal."""
    is_staff, own_branch = _staff_branch(current_user, db)
    if not is_staff:
        raise HTTPException(status_code=403, detail="Solo el personal de tienda puede ver la bandeja de reservas.")
    if own_branch is not None:
        branch_id = own_branch
    query = db.query(Reservation)
    if branch_id:
        query = query.filter(Reservation.branch_id == branch_id)
    if status_filter:
        query = query.filter(Reservation.status == status_filter.upper())

    # Ordenar por fecha de reserva más próxima
    reservations = query.order_by(Reservation.reserved_at.asc()).all()
    return [_build_reservation_response(r, db) for r in reservations]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalle de una reserva física (su cliente o el personal de la sucursal)."""
    reservation = _get_accessible_reservation(reservation_id, current_user, db)
    return _build_reservation_response(reservation, db)


@router.patch("/{reservation_id}/status", response_model=ReservationResponse)
def update_reservation_status(
    reservation_id: int,
    data: ReservationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU27] Actualiza el estado Kanban de preparación (PENDING, PREPARING, READY, LATE, NO_SHOW, COMPLETED, CANCELLED, EXPIRED)."""
    reservation = _get_accessible_reservation(reservation_id, current_user, db, staff_only=True)

    new_status = data.status.upper()
    valid_statuses = ["PENDING", "PREPARING", "READY", "LATE", "NO_SHOW", "COMPLETED", "CANCELLED", "EXPIRED"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Valores permitidos: {valid_statuses}")

    if reservation.status in ["CANCELLED", "COMPLETED", "NO_SHOW"] and new_status != "READY":
        raise HTTPException(
            status_code=400,
            detail=f"La reserva ya se encuentra en estado '{reservation.status}' y no puede cambiar."
        )

    # Si se cancela o pasa a NO_SHOW, liberar el stock apartado (la seña no se reembolsa)
    if new_status in ["CANCELLED", "NO_SHOW"] and reservation.status not in ["CANCELLED", "NO_SHOW"]:
        _release_reservation_stock(reservation, db)

    if reservation.status != new_status:
        _avisar_reserva(reservation, db, new_status)
    reservation.status = new_status
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)


@router.patch("/{reservation_id}/reschedule", response_model=ReservationResponse)
def reschedule_reservation(
    reservation_id: int,
    data: ReservationReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU28] Reprogramar fecha y hora de la cita de reserva (máximo 2 veces, mínimo 4 horas de anticipación)."""
    reservation = _get_accessible_reservation(reservation_id, current_user, db)

    if reservation.status in ["COMPLETED", "CANCELLED", "NO_SHOW"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede reprogramar una reserva en estado '{reservation.status}'."
        )

    current_count = getattr(reservation, "reschedule_count", 0) or 0
    if current_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Ha alcanzado el límite máximo permitido de 2 reprogramaciones para esta reserva."
        )

    # Validar fecha no pasada
    if data.new_date < date.today():
        raise HTTPException(status_code=400, detail="La nueva fecha no puede ser en el pasado.")

    branch = db.query(Branch).filter(Branch.id == reservation.branch_id).first()
    if branch:
        open_t = getattr(branch, "opening_time", "09:00") or "09:00"
        close_t = getattr(branch, "closing_time", "21:00") or "21:00"
        if data.new_time < open_t or data.new_time > close_t:
            raise HTTPException(
                status_code=400,
                detail=f"La hora solicitada ({data.new_time}) está fuera del horario de atención ({open_t} - {close_t})."
            )

    reservation.appointment_date = data.new_date
    reservation.appointment_time = data.new_time
    reservation.reschedule_count = current_count + 1
    reservation.status = "PENDING"
    if data.reason:
        reservation.notes = f"Reprogramado ({data.reason}). " + (reservation.notes or "")

    nueva_cita = _texto_cita(reservation)
    notificar(db, reservation.customer_id, "Cita reprogramada",
              f"Tu reserva {reservation.reservation_code} ahora es el {nueva_cita}.", TIPO_RESERVA, reservation.id, "RESERVATION")
    _avisar_personal(reservation, db, "Reserva reprogramada", f"{reservation.reservation_code} pasó al {nueva_cita}.")
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)


@router.patch("/{reservation_id}/mark-arrived", response_model=ReservationResponse)
def mark_customer_arrived(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU27] El encargado/cajero marca que el cliente llegó a la tienda (reactiva citas en LATE)."""
    reservation = _get_accessible_reservation(reservation_id, current_user, db, staff_only=True)

    if reservation.status not in ["LATE", "PENDING", "PREPARING"]:
        raise HTTPException(
            status_code=400,
            detail=f"La reserva está en estado '{reservation.status}', no requiere marcación de llegada."
        )

    reservation.status = "READY"
    _avisar_reserva(reservation, db)
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU28] Cancelar reserva y liberar inmediatamente el stock apartado (HOLD).
    Regla: Si el cliente cancela, debe ser con más de 24 horas de antelación a la cita.
    """
    reservation = _get_accessible_reservation(reservation_id, current_user, db)

    if reservation.status in ["CANCELLED", "COMPLETED"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cancelar una reserva en estado '{reservation.status}'."
        )

    # Validar ventana de 24 horas para clientes
    user_roles = [r.name for r in current_user.roles]
    is_staff = any(r in ["SUPERADMIN", "ADMINISTRADOR", "ENCARGADO", "CAJERO"] for r in user_roles)
    if not is_staff and reservation.reserved_at:
        now = datetime.now()
        res_time = reservation.reserved_at.replace(tzinfo=None) if reservation.reserved_at.tzinfo else reservation.reserved_at
        hours_before = (res_time - now).total_seconds() / 3600
        if hours_before < 24:
            raise HTTPException(
                status_code=400,
                detail="No es posible cancelar la cita con menos de 24 horas de anticipación. Las prendas ya se encuentran preparadas en probador y se considera venta perdida según política de tienda."
            )

    _release_reservation_stock(reservation, db)
    reservation.status = "CANCELLED"
    _avisar_reserva(reservation, db)
    if not is_staff:
        _avisar_personal(reservation, db, "Reserva cancelada por el cliente",
                         f"{reservation.reservation_code} ({_texto_cita(reservation)}) fue cancelada; el stock ya se liberó.")
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)


def _release_reservation_stock(reservation: Reservation, db: Session):
    """Restaura el stock apartado a la sucursal y asienta el movimiento en el ledger."""
    for it in reservation.items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == reservation.branch_id,
            Inventory.variant_id == it.variant_id,
        ).first()
        if inv:
            inv.stock_actual += it.quantity
            db.add(
                InventoryLedger(
                    branch_id=reservation.branch_id,
                    variant_id=it.variant_id,
                    quantity=it.quantity,
                    movement_type="RESERVA_LIBERACION",
                    unit_cost=float(inv.avg_cost or 0),
                    reference_id=f"REL-{reservation.reservation_code}",
                )
            )


@router.post("/{reservation_id}/convert-to-pos", response_model=ReservationResponse)
def convert_reservation_to_pos(
    reservation_id: int,
    data: ReservationConvertToPOSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU25] Convierte reserva física en venta presencial POS con facturación selectiva:
    - Las prendas que el cliente compra se facturan y se liquida el saldo (descontando la seña del 50%).
    - Las prendas que el cliente deja/no compra se devuelven inmediatamente a reposición de stock.
    - El saldo se cobra en el turno de caja ABIERTO del cajero, en la sucursal de la reserva,
      para que cuadre en su arqueo de cierre.
    """
    reservation = _get_accessible_reservation(reservation_id, current_user, db, staff_only=True)

    if reservation.status in ["CANCELLED", "COMPLETED", "EXPIRED", "NO_SHOW"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede facturar una reserva en estado '{reservation.status}'."
        )

    shift = db.query(CashShift).filter(CashShift.id == data.cash_shift_id).first()
    if not shift or shift.status != "ABIERTO":
        raise HTTPException(status_code=400, detail="Abre tu caja antes de cobrar la reserva.")
    if shift.cashier_id != current_user.id:
        raise HTTPException(status_code=400, detail="El turno de caja indicado no es tuyo.")
    if shift.branch_id != reservation.branch_id:
        raise HTTPException(status_code=400, detail="La reserva pertenece a otra sucursal que tu caja abierta.")

    p_method = data.payment_method.upper()
    if p_method not in ("EFECTIVO", "TARJETA", "QR"):
        raise HTTPException(status_code=400, detail="El saldo en caja se cobra en EFECTIVO, TARJETA o QR.")

    # 1. Separar prendas compradas vs prendas rechazadas/devueltas
    if data.selected_item_ids is not None:
        items_to_buy = [it for it in reservation.items if it.id in data.selected_item_ids]
        items_to_return = [it for it in reservation.items if it.id not in data.selected_item_ids]
    else:
        items_to_buy = list(reservation.items)
        items_to_return = []

    if not items_to_buy:
        raise HTTPException(
            status_code=400,
            detail="Debe seleccionar al menos una prenda que el cliente compre. Si no compra ninguna, cancele la reserva para reponer todas al stock."
        )

    # 2. REPOSICIÓN INMEDIATA: Reintegrar al stock las prendas que el cliente NO compró
    for it in items_to_return:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == reservation.branch_id,
            Inventory.variant_id == it.variant_id,
        ).first()
        if inv:
            inv.stock_actual += it.quantity
            db.add(
                InventoryLedger(
                    branch_id=reservation.branch_id,
                    variant_id=it.variant_id,
                    quantity=it.quantity,
                    movement_type="REPOSICION_NO_COMPRADO",
                    unit_cost=float(inv.avg_cost or 0),
                    reference_id=f"REPOSICION-{reservation.reservation_code}",
                )
            )

    # 3. Calcular totales para las prendas efectivamente compradas
    subtotal = round(sum(float(it.unit_price) * it.quantity for it in items_to_buy), 2)
    # Seña computable del 50% para las prendas compradas
    deposit_credited = round(subtotal * 0.50, 2)
    # Saldo neto a cobrar en caja del POS hoy:
    balance_to_charge = round(subtotal - deposit_credited, 2)
    total_amount = subtotal

    # 4. Crear cabecera Order POS
    order = Order(
        user_id=reservation.customer_id,
        branch_id=reservation.branch_id,
        channel="POS",
        status="PAGADA",
        subtotal=subtotal,
        discount_amount=0.0,
        coupon_code=None,
        total_amount=total_amount,
        cash_shift_id=shift.id,
    )
    db.add(order)
    db.flush()

    # 5. Insertar OrderItems (solo prendas compradas) y asentar venta en el ledger
    for it in items_to_buy:
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                unit_price=it.unit_price,
            )
        )
        inv = db.query(Inventory).filter(
            Inventory.branch_id == reservation.branch_id,
            Inventory.variant_id == it.variant_id,
        ).first()
        db.add(
            InventoryLedger(
                branch_id=reservation.branch_id,
                variant_id=it.variant_id,
                quantity=0,  # Ya se descontó en la reserva; se registra la venta confirmada
                movement_type="VENTA_RESERVA",
                unit_cost=float(inv.avg_cost or 0) if inv else 0.0,
                reference_id=f"ORD-{order.id}",
            )
        )

    # 6. Crear Pago en Caja por el saldo restante (queda ligado al turno vía la orden)
    if p_method == "EFECTIVO":
        received = data.cash_received if data.cash_received is not None else balance_to_charge
        if received + 0.001 < balance_to_charge:
            raise HTTPException(status_code=400, detail=f"El efectivo recibido no cubre el saldo de Bs. {balance_to_charge}.")
        payment = EfectivoPayment(
            order_id=order.id,
            amount=balance_to_charge,
            status="CONFIRMADO",
            cash_received=received,
            cash_change=round(received - balance_to_charge, 2),
        )
    elif p_method == "TARJETA":
        payment = TarjetaPayment(
            order_id=order.id,
            amount=balance_to_charge,
            status="CONFIRMADO",
            card_brand=(data.card_brand or "VISA").upper(),
            card_last4=data.card_last4 or "0000",
            gateway_reference=data.payment_reference or f"POS-{uuid.uuid4().hex[:8].upper()}",
        )
    else:  # QR
        payment = QRPayment(
            order_id=order.id,
            amount=balance_to_charge,
            status="CONFIRMADO",
            qr_reference=data.payment_reference or f"QR-{uuid.uuid4().hex[:8].upper()}",
        )
    db.add(payment)

    # 7. Emitir Factura fiscal oficial con IVA 13% sobre el total comprado
    iva_amount = round(total_amount * 0.13, 2)
    control_code = f"{uuid.uuid4().hex[:2].upper()}-{uuid.uuid4().hex[2:4].upper()}-{uuid.uuid4().hex[4:6].upper()}"

    invoice = Invoice(
        order_id=order.id,
        doc_type="FACTURA",
        tax_rate=0.130,
        subtotal=subtotal,
        tax_amount=iva_amount,
        total=total_amount,
        control_code=control_code,
        customer_nit=data.nit_ruc or "0",
        customer_name=data.business_name or "SIN NOMBRE",
    )
    db.add(invoice)

    # 8. Actualizar estado de la reserva
    reservation.status = "COMPLETED"
    reservation.completed_sale_id = order.id
    if items_to_return:
        returned_names = ", ".join(f"Variant #{it.variant_id}" for it in items_to_return)
        reservation.notes = f"{reservation.notes or ''} [Compró {len(items_to_buy)} prendas. Se repusieron {len(items_to_return)} prendas al stock: {returned_names}]".strip()

    _avisar_reserva(reservation, db)
    db.commit()
    db.refresh(reservation)
    return _build_reservation_response(reservation, db)
