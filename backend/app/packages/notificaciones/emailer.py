"""[CU03] Envío de correo saliente vía SMTP.

En Ciclo 1 solo se usa para el enlace de recuperación de contraseña. Si no hay
credenciales SMTP configuradas (`SMTP_USER` / `SMTP_PASSWORD`), la función no
falla: registra el contenido en consola para poder probar el flujo en desarrollo.
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.config import settings


def _send(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    if not settings.smtp_enabled:
        print("[EMAIL:DEV] SMTP no configurado (SMTP_USER/SMTP_PASSWORD vacíos).")
        print(f"  Para:    {to_email}")
        print(f"  Asunto:  {subject}")
        print(f"  Texto:   {text_body}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
    msg["To"] = to_email
    msg["Reply-To"] = settings.SMTP_FROM
    # Date y Message-ID mejoran la entregabilidad (menor puntaje de spam).
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=settings.SMTP_FROM.split("@")[-1])
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        refused = server.send_message(msg)
        if refused:
            # Gmail rechazó explícitamente al menos un destinatario.
            print(f"[EMAIL:RECHAZADO] Gmail rechazó destinatarios: {refused}")
            return False
    print(f"[EMAIL:ENVIADO] Correo de recuperación aceptado por Gmail para {to_email}")
    return True


def send_password_recovery_email(to_email: str, reset_link: str) -> bool:
    """Envía el correo con el enlace de restablecimiento (válido 5 minutos)."""
    subject = "FashionStore — Restablece tu contraseña"
    text_body = (
        "Recibimos una solicitud para restablecer tu contraseña de FashionStore.\n\n"
        f"Abre este enlace (válido por 5 minutos):\n{reset_link}\n\n"
        "Si no fuiste tú, ignora este mensaje."
    )
    html_body = f"""\
<div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:auto;color:#2B1F1D">
  <h2 style="color:#C66F5C">FashionStore</h2>
  <p>Recibimos una solicitud para restablecer tu contraseña.</p>
  <p style="margin:24px 0">
    <a href="{reset_link}"
       style="background:#C66F5C;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:bold">
      Restablecer contraseña
    </a>
  </p>
  <p style="font-size:13px;color:#8C7E7B">
    Este enlace vence en <strong>5 minutos</strong>. Si no fuiste tú, ignora este correo.
  </p>
  <p style="font-size:12px;color:#8C7E7B;word-break:break-all">{reset_link}</p>
</div>"""
    try:
        return _send(to_email, subject, html_body, text_body)
    except smtplib.SMTPAuthenticationError as exc:
        print(f"[EMAIL:ERROR] Gmail rechazó las credenciales SMTP: {exc!r}. "
              "Revisa SMTP_USER y la contraseña de aplicación (SMTP_PASSWORD) en backend/.env.")
        return False
    except Exception as exc:  # pragma: no cover - depende del entorno SMTP
        print(f"[EMAIL:ERROR] No se pudo enviar el correo a {to_email}: {exc!r}")
        return False
