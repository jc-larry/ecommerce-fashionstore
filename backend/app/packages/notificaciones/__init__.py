# Paquete Notificaciones - [CU40] push + correos transaccionales (Ciclo 3).
# En el Ciclo 1 este paquete solo provee el correo del enlace de recuperación (CU03).
from app.packages.notificaciones.emailer import send_password_recovery_email

__all__ = ["send_password_recovery_email"]
