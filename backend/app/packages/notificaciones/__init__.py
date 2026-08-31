# Notifications Package (Notificaciones)
# CU25 (tiempo real) → Ciclo 2. En Ciclo 1 solo el correo de recuperación (CU03).
from app.packages.notificaciones.emailer import send_password_recovery_email

__all__ = ["send_password_recovery_email"]
