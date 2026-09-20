"""Schemas Pydantic para el paquete Notificaciones."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class InAppNotificationCreate(BaseModel):
    user_id: int
    title: str = Field(..., max_length=150)
    message: str
    notification_type: str = Field(default="SYSTEM", description="RESERVATION, SHIPMENT, ORDER, SYSTEM, PROMOTION")
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None


class InAppNotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationsSummaryResponse(BaseModel):
    unread_count: int
    notifications: List[InAppNotificationResponse] = []


class SendEmailNotificationRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(..., max_length=200)
    message: str
