"""Controlador API REST para Repartidores y Auto-selección de Pedidos (CU05, CU29, CU30)."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.envios_y_logistica.models import Shipment, ShipmentTrackingEvent
from app.packages.envios_y_logistica.schemas import ShipmentResponse
from app.packages.envios_y_logistica.routers import _build_shipment_response, avisar_envio
from app.packages.envios_y_logistica.delivery_persons.models import DeliveryPerson
from app.packages.envios_y_logistica.delivery_persons.schemas import (
    DeliveryPersonCreate,
    DeliveryPersonUpdate,
    DeliveryPersonResponse,
    FailedDeliveryReport,
    RescheduleDeliveryRequest,
    DeliveryStatusUpdate,
    DeliveryConfirmation,
)
from app.packages.seguridad_y_usuarios.models import User
from app.packages.seguridad_y_usuarios.routers import get_current_user, RoleChecker

router = APIRouter(prefix="/api/v1/logistics", tags=["Repartidores y Última Milla"])

admin_or_super = RoleChecker(allowed_roles=["SUPERADMIN", "ADMINISTRADOR"])
delivery_checker = RoleChecker(allowed_roles=["SUPERADMIN", "ADMINISTRADOR", "REPARTIDOR"])

# Máximo ~1.5 MB de data URL: la app comprime la foto antes de enviarla.
MAX_PHOTO_DATA_URL = 1_500_000

# Transiciones permitidas en ruta (estado actual -> nuevos estados válidos).
ROUTE_TRANSITIONS = {
    "ASSIGNED": {"PICKED_UP"},
    "PICKED_UP": {"IN_TRANSIT"},
    "IN_TRANSIT": {"OUT_FOR_DELIVERY"},
    "FAILED_ATTEMPT": {"IN_TRANSIT"},
    "RESCHEDULED": {"IN_TRANSIT"},
}
DELIVERABLE_STATUSES = {"PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "FAILED_ATTEMPT"}


def _user_full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip()


def _is_admin(user: User) -> bool:
    return any(role.name in ["SUPERADMIN", "ADMINISTRADOR"] for role in user.roles)


def _owned_shipment(db: Session, current_user: User, shipment_id: int) -> tuple:
    """Devuelve (envío, perfil de repartidor) verificando que el envío sea del repartidor autenticado."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Envío no encontrado")
    if not _is_admin(current_user) and (not dp or shipment.delivery_person_id != dp.id):
        raise HTTPException(status_code=403, detail="Este envío no te corresponde")
    return shipment, dp


# ===================================================================
# GESTIÓN DE PERFILES DE REPARTIDORES (CU05)
# ===================================================================

@router.post("/delivery-persons", response_model=DeliveryPersonResponse, status_code=status.HTTP_201_CREATED)
def create_delivery_person(
    data: DeliveryPersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU05] Registrar un nuevo perfil operativo de repartidor."""
    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    existing = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya tiene un perfil de repartidor asignado")

    dp = DeliveryPerson(
        user_id=data.user_id,
        vehicle_type=data.vehicle_type,
        vehicle_plate=data.vehicle_plate,
        license_number=data.license_number,
        coverage_zone=data.coverage_zone,
        phone=data.phone,
        is_available=True,
    )
    db.add(dp)
    db.commit()
    db.refresh(dp)
    return dp


@router.get("/delivery-persons", response_model=List[DeliveryPersonResponse])
def list_delivery_persons(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    """[CU05] Listar todos los repartidores registrados."""
    q = db.query(DeliveryPerson)
    if active_only:
        q = q.filter(DeliveryPerson.is_active == True)
    return q.order_by(DeliveryPerson.created_at.desc()).all()


@router.get("/delivery-persons/my", response_model=DeliveryPersonResponse)
def get_my_delivery_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU05] Consultar el perfil operativo del repartidor autenticado."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="No tienes un perfil de repartidor activo")
    return dp


@router.patch("/delivery-persons/availability", response_model=DeliveryPersonResponse)
def toggle_availability(
    is_available: bool = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU29] Alternar disponibilidad para recibir/tomar pedidos."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Perfil de repartidor no encontrado")
    dp.is_available = is_available
    db.commit()
    db.refresh(dp)
    return dp


# ===================================================================
# BOLSA DE PEDIDOS Y AUTO-SELECCIÓN (CU29, CU30)
# ===================================================================

@router.get("/shipments/available", response_model=List[ShipmentResponse])
def get_available_shipments(
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU29] Bolsa de pedidos disponibles para ser tomados por los repartidores.
    
    Muestra envíos en estado PENDING_DISPATCH o RESCHEDULED sin repartidor asignado.
    """
    shipments = (
        db.query(Shipment)
        .filter(
            Shipment.status.in_(["PENDING_DISPATCH", "RESCHEDULED"]),
            Shipment.delivery_person_id == None,
        )
        .order_by(Shipment.created_at.asc())
        .all()
    )
    return [_build_shipment_response(s) for s in shipments]


@router.get("/shipments/my-active", response_model=List[ShipmentResponse])
def get_my_active_shipments(
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU29, CU30] Lista de pedidos actualmente tomados por el repartidor autenticado."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Perfil de repartidor no encontrado")

    active_statuses = ["ASSIGNED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "FAILED_ATTEMPT", "RESCHEDULED"]
    shipments = (
        db.query(Shipment)
        .filter(
            Shipment.delivery_person_id == dp.id,
            Shipment.status.in_(active_statuses),
        )
        .order_by(Shipment.updated_at.desc())
        .all()
    )
    return [_build_shipment_response(s) for s in shipments]


@router.post("/shipments/{shipment_id}/claim", response_model=ShipmentResponse)
def claim_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU29] Auto-selección atómica de pedido por el repartidor.
    
    Al tomar el pedido:
    - Se asigna delivery_person_id
    - Cambia estado a ASSIGNED
    - Ya no aparece en la bolsa para otros repartidores
    - Genera hito de tracking
    """
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    if not dp:
        raise HTTPException(status_code=403, detail="Solo un repartidor con perfil activo puede tomar pedidos")
    if not dp.is_available:
        raise HTTPException(status_code=400, detail="Debes estar en estado disponible para tomar nuevos pedidos")

    # Bloqueo atómico o verificación
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Envío no encontrado")

    if shipment.delivery_person_id is not None or shipment.status not in ["PENDING_DISPATCH", "RESCHEDULED"]:
        raise HTTPException(
            status_code=409,
            detail="Este pedido ya fue tomado por otro repartidor o ya no está disponible",
        )

    now = datetime.now()
    driver_name = _user_full_name(current_user)
    shipment.delivery_person_id = dp.id
    shipment.carrier_name = driver_name
    shipment.carrier_phone = dp.phone
    shipment.status = "ASSIGNED"
    shipment.claimed_at = now
    shipment.updated_at = now

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status="ASSIGNED",
        location=f"Asignado a {driver_name}",
        description=f"El repartidor {driver_name} ({dp.vehicle_type}) aceptó el pedido y se dirige a la sucursal para retiro.",
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.post("/shipments/{shipment_id}/release", response_model=ShipmentResponse)
def release_shipment(
    shipment_id: int,
    reason: Optional[str] = Query("Inconveniente con el repartidor"),
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU29] El repartidor libera el pedido para que vuelva a la bolsa disponible."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Envío no encontrado")

    # Solo el repartidor asignado o un admin pueden liberar
    is_admin = any(role.name in ["SUPERADMIN", "ADMINISTRADOR"] for role in current_user.roles)
    if not is_admin and (not dp or shipment.delivery_person_id != dp.id):
        raise HTTPException(status_code=403, detail="No puedes liberar un pedido que no te corresponde")

    shipment.delivery_person_id = None
    shipment.status = "PENDING_DISPATCH"
    shipment.notes = f"Liberado: {reason}"
    shipment.updated_at = datetime.now()

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status="PENDING_DISPATCH",
        location="Santa Cruz - Bolsa de pedidos",
        description=f"El pedido volvió a la bolsa disponible. Motivo: {reason}",
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.patch("/shipments/{shipment_id}/route-status", response_model=ShipmentResponse)
def update_route_status(
    shipment_id: int,
    data: DeliveryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU30] Repartidor avanza la ruta: recogido -> en camino -> cerca del destino.

    La entrega final se confirma con /confirm-delivery, que exige foto de evidencia.
    """
    shipment, dp = _owned_shipment(db, current_user, shipment_id)

    if data.status == "DELIVERED":
        raise HTTPException(
            status_code=400,
            detail="Para marcar la entrega debes confirmarla con la foto de evidencia.",
        )
    allowed = ROUTE_TRANSITIONS.get(shipment.status, set())
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede pasar de {shipment.status} a {data.status}.",
        )

    now = datetime.now()
    shipment.status = data.status
    shipment.updated_at = now

    desc_map = {
        "PICKED_UP": "El repartidor recogió las prendas en la tienda/sucursal.",
        "IN_TRANSIT": "El pedido va en camino hacia el domicilio del cliente.",
        "OUT_FOR_DELIVERY": "El repartidor está cerca del domicilio para la entrega final.",
        "DELIVERED": "Pedido entregado con éxito al cliente en su domicilio.",
    }

    if data.status == "PICKED_UP" and not shipment.dispatched_at:
        shipment.dispatched_at = now

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status=data.status,
        location=shipment.order.branch.name if data.status == "PICKED_UP" and shipment.order and shipment.order.branch else "En ruta",
        description=data.notes or desc_map.get(data.status, "Actualización de ruta"),
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.post("/shipments/{shipment_id}/failed-delivery", response_model=ShipmentResponse)
def report_failed_delivery(
    shipment_id: int,
    data: FailedDeliveryReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU30] Repartidor reporta intento de entrega fallido (ej: cliente ausente).
    
    Incrementa delivery_attempts y cambia estado a FAILED_ATTEMPT.
    Si supera 3 intentos, cambia automáticamente a RETURNED_TO_STORE.
    """
    shipment, dp = _owned_shipment(db, current_user, shipment_id)
    if shipment.status not in DELIVERABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Solo se reporta un intento fallido de un pedido en ruta.")

    now = datetime.now()
    shipment.delivery_attempts += 1
    shipment.failed_reason = data.reason
    shipment.updated_at = now

    if shipment.delivery_attempts >= 3:
        shipment.status = "RETURNED_TO_STORE"
        desc = f"Tercer intento fallido ({data.reason}). El paquete es devuelto a la tienda/sucursal de origen."
    else:
        shipment.status = "FAILED_ATTEMPT"
        desc = f"Intento de entrega fallido #{shipment.delivery_attempts}: {data.reason}. Pendiente de reprogramación."

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status=shipment.status,
        location=shipment.delivery_address[:100],
        description=desc,
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.post("/shipments/{shipment_id}/reschedule-delivery", response_model=ShipmentResponse)
def reschedule_delivery(
    shipment_id: int,
    data: RescheduleDeliveryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU30] Reprogramar fecha u hora de entrega tras un intento fallido."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Envío no encontrado")
    role_names = {r.name for r in current_user.roles}
    is_staff = bool(role_names.intersection({"SUPERADMIN", "ADMINISTRADOR", "ENCARGADO"}))
    is_driver = shipment.delivery_person is not None and shipment.delivery_person.user_id == current_user.id
    is_customer = shipment.order is not None and shipment.order.user_id == current_user.id
    if not (is_staff or is_driver or is_customer):
        raise HTTPException(status_code=404, detail="Envío no encontrado")

    if shipment.status == "RETURNED_TO_STORE":
        raise HTTPException(
            status_code=400,
            detail="El envío ya fue devuelto a tienda tras alcanzar el límite de 3 intentos.",
        )

    now = datetime.now()
    shipment.delivery_date = data.new_delivery_date
    shipment.delivery_time = data.new_delivery_time
    shipment.status = "RESCHEDULED"
    shipment.updated_at = now

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status="RESCHEDULED",
        location="Santa Cruz - Reprogramado",
        description=f"Entrega reprogramada para el {data.new_delivery_date} a las {data.new_delivery_time}. {data.notes or ''}",
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


# ===================================================================
# EVIDENCIA DE ENTREGA E HISTORIAL DEL REPARTIDOR (CU30)
# ===================================================================

@router.post("/shipments/{shipment_id}/confirm-delivery", response_model=ShipmentResponse)
def confirm_delivery(
    shipment_id: int,
    data: DeliveryConfirmation,
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU30] El repartidor confirma la entrega con foto de evidencia y el nombre de quien recibió.

    La foto queda guardada en el envío y en el hito DELIVERED de la línea de tiempo, como
    respaldo ante un reclamo del cliente ("no me llegó").
    """
    shipment, dp = _owned_shipment(db, current_user, shipment_id)
    if shipment.status not in DELIVERABLE_STATUSES:
        raise HTTPException(status_code=400, detail="Primero debes recoger el pedido e iniciar la ruta.")
    if not data.photo_data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="La evidencia debe ser una foto (imagen).")
    if len(data.photo_data_url) > MAX_PHOTO_DATA_URL:
        raise HTTPException(status_code=413, detail="La foto es demasiado grande. Vuelve a tomarla.")

    now = datetime.now()
    received_by = data.received_by_name.strip()
    shipment.status = "DELIVERED"
    shipment.delivered_at = now
    shipment.updated_at = now
    shipment.delivery_photo_url = data.photo_data_url
    shipment.received_by_name = received_by
    if dp:
        dp.total_deliveries += 1

    description = f"Pedido entregado a {received_by}. Evidencia fotográfica registrada por el repartidor."
    if data.notes:
        description = f"{description} {data.notes}"[:255]
    db.add(ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status="DELIVERED",
        location=shipment.delivery_address[:100],
        description=description,
        photo_url=data.photo_data_url,
    ))
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.get("/shipments/my-history", response_model=List[ShipmentResponse])
def get_my_delivery_history(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(delivery_checker),
):
    """[CU30] Historial del repartidor: entregas realizadas, fallidas o devueltas, con sus tiempos."""
    dp = db.query(DeliveryPerson).filter(DeliveryPerson.user_id == current_user.id).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Perfil de repartidor no encontrado")
    shipments = (
        db.query(Shipment)
        .filter(
            Shipment.delivery_person_id == dp.id,
            Shipment.status.in_(["DELIVERED", "RETURNED_TO_STORE"]),
        )
        .order_by(Shipment.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [_build_shipment_response(s) for s in shipments]
