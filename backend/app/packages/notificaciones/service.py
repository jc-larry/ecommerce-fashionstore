"""[CU40] Generación de notificaciones in-app a partir de los eventos del negocio.

Los routers de ventas, reservas, logística y proveedores llaman a `notificar()` dentro de su
propia transacción (antes del `commit`), de modo que la notificación queda guardada junto con el
cambio que la originó. Si el cambio se revierte, la notificación también.
"""
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.packages.notificaciones.models import InAppNotification

# Tipos de notificación (columna `in_app_notifications.notification_type`).
TIPO_PEDIDO = "ORDER"
TIPO_RESERVA = "RESERVATION"
TIPO_ENVIO = "SHIPMENT"
TIPO_SISTEMA = "SYSTEM"


def notificar(
    db: Session,
    user_id: Optional[int],
    titulo: str,
    mensaje: str,
    tipo: str = TIPO_SISTEMA,
    referencia_id: Optional[int] = None,
    referencia_tipo: Optional[str] = None,
) -> None:
    """Agrega una notificación al buzón del usuario (no hace commit)."""
    if not user_id:
        return
    db.add(InAppNotification(
        user_id=user_id,
        title=titulo[:150],
        message=mensaje,
        notification_type=tipo,
        reference_id=referencia_id,
        reference_type=referencia_tipo,
    ))


def notificar_varios(
    db: Session,
    user_ids: Iterable[int],
    titulo: str,
    mensaje: str,
    tipo: str = TIPO_SISTEMA,
    referencia_id: Optional[int] = None,
    referencia_tipo: Optional[str] = None,
) -> None:
    """Notifica a varios usuarios (sin duplicados)."""
    for uid in dict.fromkeys(u for u in user_ids if u):
        notificar(db, uid, titulo, mensaje, tipo, referencia_id, referencia_tipo)


def personal_de_sucursal(db: Session, branch_id: Optional[int], roles=("ENCARGADO",)) -> List[int]:
    """IDs de los usuarios activos de la sucursal con alguno de los roles indicados."""
    if not branch_id:
        return []
    from app.packages.catalogo_y_tiendas.branches.models import Branch

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        return []
    return [
        u.id for u in branch.employees
        if u.is_active and any(r.name in roles for r in u.roles)
    ]


def usuarios_de_proveedor(db: Session, supplier_id: Optional[int]) -> List[int]:
    """IDs de los usuarios (rol PROVEEDOR) vinculados a un proveedor."""
    if not supplier_id:
        return []
    from app.packages.inventario_y_proveedores.suppliers.models import Supplier

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        return []
    return [u.id for u in getattr(supplier, "users", []) if u.is_active]
