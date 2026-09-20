"""Controlador API REST del paquete Notificaciones.
Casos de Uso:
- [CU40] Notificaciones in-app persistentes y confirmaciones automáticas por correo electrónico.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.packages.paquete_notificaciones.models import InAppNotification
from app.packages.paquete_notificaciones.schemas import (
    InAppNotificationCreate,
    InAppNotificationResponse,
    NotificationsSummaryResponse,
    SendEmailNotificationRequest,
)
from app.packages.paquete_notificaciones.emailer import send_transactional_email
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_seguridad_usuarios.routers import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notificaciones (In-App y Email)"])


@router.get("/my", response_model=NotificationsSummaryResponse)
def get_my_notifications(
    unread_only: bool = Query(False, description="Filtrar solo notificaciones no leídas"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU40] Obtiene las notificaciones del buzón in-app del usuario autenticado."""
    query = db.query(InAppNotification).filter(InAppNotification.user_id == current_user.id)
    if unread_only:
        query = query.filter(InAppNotification.is_read == False)

    notifications = query.order_by(InAppNotification.created_at.desc()).limit(limit).all()

    unread_count = (
        db.query(InAppNotification)
        .filter(InAppNotification.user_id == current_user.id, InAppNotification.is_read == False)
        .count()
    )

    return NotificationsSummaryResponse(
        unread_count=unread_count,
        notifications=[
            InAppNotificationResponse(
                id=n.id,
                title=n.title,
                message=n.message,
                notification_type=n.notification_type,
                reference_id=n.reference_id,
                reference_type=n.reference_type,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in notifications
        ],
    )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU40] Devuelve el número de notificaciones no leídas para la insignia del navbar."""
    count = (
        db.query(InAppNotification)
        .filter(InAppNotification.user_id == current_user.id, InAppNotification.is_read == False)
        .count()
    )
    return {"unread_count": count}


@router.patch("/{notification_id}/read", response_model=InAppNotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU40] Marca una notificación específica como leída."""
    notif = (
        db.query(InAppNotification)
        .filter(InAppNotification.id == notification_id, InAppNotification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return InAppNotificationResponse(
        id=notif.id,
        title=notif.title,
        message=notif.message,
        notification_type=notif.notification_type,
        reference_id=notif.reference_id,
        reference_type=notif.reference_type,
        is_read=notif.is_read,
        created_at=notif.created_at,
    )


@router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU40] Marca todas las notificaciones pendientes del usuario como leídas."""
    db.query(InAppNotification).filter(
        InAppNotification.user_id == current_user.id,
        InAppNotification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Todas las notificaciones fueron marcadas como leídas."}


@router.post("/send-email")
def send_email_notification(
    data: SendEmailNotificationRequest,
    current_user: User = Depends(get_current_user),
):
    """[CU40] Envía correo transaccional manual o disparado por eventos."""
    success = send_transactional_email(
        to_email=data.to_email,
        subject=data.subject,
        message=data.message,
    )
    return {"delivered": success, "recipient": data.to_email}
