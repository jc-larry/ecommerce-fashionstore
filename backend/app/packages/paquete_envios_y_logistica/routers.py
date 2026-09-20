"""Controlador API REST del paquete Envíos y Logística.
Casos de Uso:
- [CU29] Gestión de despachos y asignación de transportistas.
- [CU30] Trazabilidad y seguimiento de envíos en tiempo real (Tracking Timeline).
- [CU31] Gestión de zonas de cobertura y tarifas por anillos/km.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.paquete_envios_y_logistica.models import DeliveryZone, Shipment, ShipmentTrackingEvent
from app.packages.paquete_envios_y_logistica.schemas import (
    DeliveryZoneCreate,
    DeliveryZoneUpdate,
    DeliveryZoneResponse,
    DeliveryRateCalculateRequest,
    DeliveryRateCalculateResponse,
    ShipmentCreate,
    ShipmentUpdateStatus,
    ShipmentResponse,
    ShipmentTrackingEventResponse,
)
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_seguridad_usuarios.routers import get_current_user, RoleChecker, _resolve_branch_id
from app.packages.paquete_ventas_y_pagos.models import Order
from app.packages.paquete_notificaciones.service import notificar, TIPO_ENVIO

router = APIRouter(prefix="/api/v1/logistics", tags=["Envíos y Logística"])

CENTRAL_ROLES = ("SUPERADMIN", "ADMINISTRADOR")
central_check = RoleChecker(allowed_roles=list(CENTRAL_ROLES))
# Despachos: Casa Matriz y el encargado de la sucursal que vendió el pedido.
dispatch_check = RoleChecker(allowed_roles=[*CENTRAL_ROLES, "ENCARGADO"])


def _role_names(user: User) -> set:
    return {r.name for r in user.roles}


def _is_central(user: User) -> bool:
    return bool(_role_names(user).intersection(CENTRAL_ROLES))


def _manager_branch_or_403(user: User, db: Session) -> Optional[int]:
    """None para Casa Matriz; la sucursal propia para un ENCARGADO."""
    if _is_central(user):
        return None
    branch_id = _resolve_branch_id(user, db)
    if branch_id is None:
        raise HTTPException(status_code=403, detail="Tu usuario no tiene una sucursal asignada.")
    return branch_id


def _can_view_shipment(user: User, shipment: Shipment, db: Session) -> bool:
    roles = _role_names(user)
    if roles.intersection(CENTRAL_ROLES):
        return True
    if "ENCARGADO" in roles and shipment.order and shipment.order.branch_id == _resolve_branch_id(user, db):
        return True
    if "REPARTIDOR" in roles and shipment.delivery_person and shipment.delivery_person.user_id == user.id:
        return True
    return bool(shipment.order and shipment.order.user_id == user.id)


# ===================================================================
# CU31: ZONAS Y TARIFAS DE ENTREGA
# ===================================================================

# Mensajes al cliente por cada estado de su envío (CU40). Se muestran en su buzón con el código TRK.
AVISOS_ENVIO = {
    "CREADO": ("Tu pedido tiene envío a domicilio", "Generamos la guía {trk}. Podrás seguirla en Rastrear envío."),
    "DISPATCHED": ("Tu pedido fue despachado", "El envío {trk} salió de la sucursal."),
    "ASSIGNED": ("Repartidor asignado", "Un repartidor tomó tu envío {trk} y va a la sucursal a recogerlo."),
    "PICKED_UP": ("Pedido recogido", "El repartidor recogió tu envío {trk} en la sucursal."),
    "IN_TRANSIT": ("Tu pedido va en camino", "El envío {trk} está en tránsito."),
    "OUT_FOR_DELIVERY": ("¡Tu pedido llega hoy!", "El repartidor está llegando con tu envío {trk}."),
    "DELIVERED": ("Pedido entregado", "Tu envío {trk} fue entregado. ¡Gracias por comprar en FashionStore!"),
    "FAILED_ATTEMPT": ("No pudimos entregar tu pedido", "Hubo un intento de entrega fallido del envío {trk}. Te contactaremos para reprogramar."),
    "RESCHEDULED": ("Entrega reprogramada", "La entrega de tu envío {trk} fue reprogramada."),
    "RETURNED_TO_STORE": ("Envío devuelto a la sucursal", "El envío {trk} volvió a la sucursal."),
}


def avisar_envio(db: Session, shipment: Shipment, estado: Optional[str] = None) -> None:
    """Notifica al cliente dueño del pedido el estado de su envío (no hace commit)."""
    estado = estado or shipment.status
    if estado not in AVISOS_ENVIO:
        return
    order = shipment.order or db.query(Order).filter(Order.id == shipment.order_id).first()
    if not order:
        return
    titulo, plantilla = AVISOS_ENVIO[estado]
    notificar(db, order.user_id, titulo, plantilla.format(trk=shipment.tracking_number),
              TIPO_ENVIO, shipment.id, "SHIPMENT")


@router.get("/zones", response_model=List[DeliveryZoneResponse])
def list_delivery_zones(
    active_only: bool = Query(True, description="Mostrar solo zonas activas"),
    db: Session = Depends(get_db),
):
    """[CU31] Lista zonas de entrega y sus tarifas base por anillos y kilometraje."""
    query = db.query(DeliveryZone)
    if active_only:
        query = query.filter(DeliveryZone.is_active == True)
    return query.order_by(DeliveryZone.min_distance_km.asc()).all()


@router.post("/zones", response_model=DeliveryZoneResponse, status_code=status.HTTP_201_CREATED)
def create_delivery_zone(
    data: DeliveryZoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(central_check),
):
    """[CU31] Registrar una nueva zona de despacho y tarifa."""
    zone = DeliveryZone(
        name=data.name,
        city=data.city,
        min_distance_km=data.min_distance_km,
        max_distance_km=data.max_distance_km,
        base_rate=data.base_rate,
        estimated_hours=data.estimated_hours,
        is_active=data.is_active,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.put("/zones/{zone_id}", response_model=DeliveryZoneResponse)
def update_delivery_zone(
    zone_id: int,
    data: DeliveryZoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(central_check),
):
    """[CU31] Actualizar parámetros o tarifa de una zona de entrega."""
    zone = db.query(DeliveryZone).filter(DeliveryZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona de entrega no encontrada.")

    for field, val in data.dict(exclude_unset=True).items():
        setattr(zone, field, val)

    db.commit()
    db.refresh(zone)
    return zone


@router.post("/calculate-rate", response_model=DeliveryRateCalculateResponse)
def calculate_shipping_rate(
    data: DeliveryRateCalculateRequest,
    db: Session = Depends(get_db),
):
    """[CU31] Calcula automáticamente el costo de flete según la distancia en kilómetros."""
    if data.zone_id:
        zone = db.query(DeliveryZone).filter(DeliveryZone.id == data.zone_id).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Zona de entrega no encontrada.")
        return DeliveryRateCalculateResponse(
            zone_id=zone.id,
            zone_name=zone.name,
            rate=float(zone.base_rate),
            estimated_hours=zone.estimated_hours,
            distance_km=data.distance_km,
        )

    # Buscar zona coincidente por rango de distancia
    zone = (
        db.query(DeliveryZone)
        .filter(
            DeliveryZone.is_active == True,
            DeliveryZone.min_distance_km <= data.distance_km,
            DeliveryZone.max_distance_km >= data.distance_km,
        )
        .first()
    )

    if not zone:
        # Si supera el rango máximo, calcular tarifa extendida (ej. Bs. 3 por km adicional)
        max_zone = (
            db.query(DeliveryZone)
            .filter(DeliveryZone.is_active == True)
            .order_by(DeliveryZone.max_distance_km.desc())
            .first()
        )
        if max_zone and data.distance_km > float(max_zone.max_distance_km):
            extra_km = data.distance_km - float(max_zone.max_distance_km)
            calc_rate = round(float(max_zone.base_rate) + (extra_km * 3.5), 2)
            return DeliveryRateCalculateResponse(
                zone_id=max_zone.id,
                zone_name=f"{max_zone.name} (+ Km Adicional)",
                rate=calc_rate,
                estimated_hours=max_zone.estimated_hours + 12,
                distance_km=data.distance_km,
            )
        # Tarifa plana por defecto si no hay zonas configuradas
        return DeliveryRateCalculateResponse(
            zone_id=None,
            zone_name="Tarifa Estándar Urbana",
            rate=15.0,
            estimated_hours=24,
            distance_km=data.distance_km,
        )

    return DeliveryRateCalculateResponse(
        zone_id=zone.id,
        zone_name=zone.name,
        rate=float(zone.base_rate),
        estimated_hours=zone.estimated_hours,
        distance_km=data.distance_km,
    )


# ===================================================================
# CU29: GESTIÓN DE DESPACHOS Y ASIGNACIÓN DE CARRIER
# ===================================================================

def _build_shipment_response(s: Shipment) -> ShipmentResponse:
    branch = s.order.branch if s.order else None
    dp_user = s.delivery_person.user if s.delivery_person else None
    return ShipmentResponse(
        id=s.id,
        tracking_number=s.tracking_number,
        order_id=s.order_id,
        zone_id=s.zone_id,
        zone_name=s.zone.name if s.zone else None,
        carrier_name=s.carrier_name,
        carrier_phone=s.carrier_phone,
        delivery_address=s.delivery_address,
        recipient_name=s.recipient_name,
        recipient_phone=s.recipient_phone,
        shipping_cost=float(s.shipping_cost),
        status=s.status,
        dispatched_at=s.dispatched_at,
        delivered_at=s.delivered_at,
        notes=s.notes,
        created_at=s.created_at,
        updated_at=s.updated_at,
        delivery_person_id=s.delivery_person_id,
        delivery_person_name=f"{dp_user.first_name} {dp_user.last_name}".strip() if dp_user else None,
        claimed_at=s.claimed_at,
        delivery_date=s.delivery_date,
        delivery_time=s.delivery_time,
        delivery_attempts=s.delivery_attempts or 0,
        failed_reason=s.failed_reason,
        delivery_photo_url=s.delivery_photo_url,
        received_by_name=s.received_by_name,
        origin_branch_id=branch.id if branch else None,
        origin_branch_name=branch.name if branch else None,
        origin_branch_address=branch.address if branch else None,
        origin_latitude=float(branch.latitude) if branch and branch.latitude is not None else None,
        origin_longitude=float(branch.longitude) if branch and branch.longitude is not None else None,
        events=[
            ShipmentTrackingEventResponse(
                id=ev.id,
                status=ev.status,
                location=ev.location,
                description=ev.description,
                photo_url=ev.photo_url,
                created_at=ev.created_at,
            )
            for ev in s.events
        ],
    )


@router.post("/shipments", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(
    data: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(dispatch_check),
):
    """[CU29] Crea la orden de despacho/envío para un pedido pagado y genera código de tracking."""
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    own_branch = _manager_branch_or_403(current_user, db)
    if own_branch is not None and order.branch_id != own_branch:
        raise HTTPException(status_code=403, detail="Solo puedes despachar pedidos de tu sucursal.")

    # Generar tracking number TRK-XXXXXXXX
    tracking_num = f"TRK-{uuid.uuid4().hex[:8].upper()}"

    shipment = Shipment(
        tracking_number=tracking_num,
        order_id=data.order_id,
        zone_id=data.zone_id,
        carrier_name=data.carrier_name,
        carrier_phone=data.carrier_phone,
        delivery_address=data.delivery_address,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
        shipping_cost=data.shipping_cost,
        status="PENDING_DISPATCH",
        notes=data.notes,
    )
    db.add(shipment)
    db.flush()

    # Registrar evento inicial en la bitácora de rastreo
    initial_event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status="PENDING_DISPATCH",
        location="Centro de Distribución FashionStore",
        description="Guía de despacho generada. Paquete en empaque y preparación de salida.",
    )
    db.add(initial_event)
    avisar_envio(db, shipment, "CREADO")
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


@router.get("/shipments", response_model=List[ShipmentResponse])
def list_shipments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por estado"),
    db: Session = Depends(get_db),
    current_user: User = Depends(dispatch_check),
):
    """[CU29] Despachos con trazabilidad. Un ENCARGADO solo ve los de su sucursal."""
    query = db.query(Shipment)
    own_branch = _manager_branch_or_403(current_user, db)
    if own_branch is not None:
        query = query.join(Order, Shipment.order_id == Order.id).filter(Order.branch_id == own_branch)
    if status_filter:
        query = query.filter(Shipment.status == status_filter.upper())
    shipments = query.order_by(Shipment.created_at.desc()).all()
    return [_build_shipment_response(s) for s in shipments]


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
def get_shipment_detail(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalle de un despacho con toda su bitácora de eventos."""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment or not _can_view_shipment(current_user, shipment, db):
        raise HTTPException(status_code=404, detail="Despacho no encontrado.")
    return _build_shipment_response(shipment)


@router.post("/shipments/{shipment_id}/events", response_model=ShipmentResponse)
def add_shipment_event(
    shipment_id: int,
    data: ShipmentUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(dispatch_check),
):
    """[CU29, CU30] Hito manual de Casa Matriz o del encargado de la sucursal de origen.

    El repartidor no usa este endpoint: actualiza su ruta con /route-status y confirma la
    entrega con /confirm-delivery, que exige la foto de evidencia.
    """
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Despacho no encontrado.")
    own_branch = _manager_branch_or_403(current_user, db)
    if own_branch is not None and shipment.order.branch_id != own_branch:
        raise HTTPException(status_code=403, detail="Este despacho no pertenece a tu sucursal.")

    new_status = data.status.upper()
    shipment.status = new_status
    now = datetime.now()

    if new_status == "DISPATCHED" and not shipment.dispatched_at:
        shipment.dispatched_at = now
    elif new_status == "DELIVERED":
        shipment.delivered_at = now

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status=new_status,
        location=data.location,
        description=data.description,
    )
    db.add(event)
    avisar_envio(db, shipment)
    db.commit()
    db.refresh(shipment)
    return _build_shipment_response(shipment)


# ===================================================================
# CU30: TRACKING TIMELINE POR CÓDIGO
# ===================================================================

@router.get("/track/{tracking_number}", response_model=ShipmentResponse)
def track_shipment_public(
    tracking_number: str,
    db: Session = Depends(get_db),
):
    """[CU30] Consulta pública de trazabilidad en tiempo real mediante código de tracking."""
    shipment = (
        db.query(Shipment)
        .filter(Shipment.tracking_number == tracking_number.strip().upper())
        .first()
    )
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún paquete con el código de seguimiento '{tracking_number}'."
        )
    return _build_shipment_response(shipment)
