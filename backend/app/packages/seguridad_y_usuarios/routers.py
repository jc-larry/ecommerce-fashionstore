from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db

from app.config import settings
from app.packages.seguridad_y_usuarios.services import verify_password, get_password_hash, create_access_token, decode_access_token
from app.packages.seguridad_y_usuarios.models import User, Role, SessionToken, AuditLog
from app.packages.notificaciones import send_password_recovery_email
import secrets
from app.packages.seguridad_y_usuarios.schemas import (
    UserLogin, UserRegister, TokenResponse, UserRecover, UserResponse,
    UserCreate, UserUpdate, UserDetailResponse, AuditLogResponse, PasswordReset
)

router = APIRouter(prefix="/api/v1", tags=["security"])

# --- DEPENDENCIAS DE SEGURIDAD ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """[CU01 / CU02] Valida token JWT y extrae el usuario de la sesión activa"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de acceso no válidas.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id_str = decode_access_token(token)
    if user_id_str is None:
        raise credentials_exception
    
    session_record = db.query(SessionToken).filter(
        SessionToken.token == token,
        SessionToken.is_revoked == False
    ).first()
    if not session_record:
        raise credentials_exception

    # [CU02] Rechazar sesiones cuyo token JWT ya venció
    if session_record.expires_at and session_record.expires_at < datetime.now(timezone.utc):
        session_record.is_revoked = True
        db.commit()
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id_str), User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    """[CU05 / CU36] Inyector para validar permisos según roles del usuario"""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_roles = [r.name for r in current_user.roles]
        if "SUPERADMIN" in user_roles:
            return current_user
        for role in self.allowed_roles:
            if role in user_roles:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos suficientes para realizar esta acción."
        )

# --- BITÁCORA AUDITORA ---
def log_event(db: Session, user_id: int, action: str, table: str, row_id: int, details: dict, ip: str = None):
    """[CU36] Auxiliar para registrar auditoría de base de datos"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table,
        row_id=row_id,
        new_values=details,
        ip_address=ip
    )
    db.add(log)
    db.commit()

# --- ENDPOINTS: AUTENTICACIÓN ---
@router.post("/auth/login", response_model=TokenResponse)
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """[CU01] Inicio de sesión unificado"""
    # [CU01 - Paso 2] / [DSC001 - Paso 2] +login(email, password)
    # [CU01 - Paso 3] / [DSC001 - Paso 3] +select_where(email)
    # El correo ya viene normalizado a minúsculas por el schema; la contraseña se limpia de
    # espacios accidentales del teclado/autocompletado (sin recortar espacios internos).
    email = login_data.email
    password = login_data.password.strip()
    user = db.query(User).filter(User.email == email).first()
    # [CU01 - Paso 4] / [DSC001 - Paso 4] +Datos y Hash (verificación implícita)
    if not user:
        print(f"[LOGIN] Rechazado: el correo '{email}' NO está registrado en esta base de datos.")
        raise HTTPException(status_code=400, detail="Correo electrónico o contraseña incorrectos.")
    if not verify_password(password, user.password_hash):
        print(f"[LOGIN] Rechazado: contraseña incorrecta para '{email}' (usuario id={user.id}).")
        raise HTTPException(status_code=400, detail="Correo electrónico o contraseña incorrectos.")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Cuenta de usuario desactivada.")

    # [CU01 - Paso 5] / [DSC001 - Paso 5] +create_token()
    token = create_access_token(subject=user.id)
    expires = datetime.now(timezone.utc) + timedelta(minutes=60)

    # Limpieza: revocar tokens expirados del usuario para evitar acumulación de sesiones obsoletas.
    # Esto asegura que iniciar sesión desde cualquier navegador/dispositivo funcione sin problemas.
    db.query(SessionToken).filter(
        SessionToken.user_id == user.id,
        SessionToken.is_revoked == False,
        SessionToken.expires_at < datetime.now(timezone.utc)
    ).update({"is_revoked": True})

    session = SessionToken(user_id=user.id, token=token, expires_at=expires)
    db.add(session)
    db.commit()

    log_event(db, user.id, "LOGIN", "users", user.id, {"email": user.email}, request.client.host)

    roles = [r.name for r in user.roles]
    # [CU01 - Paso 6] / [DSC001 - Paso 6] +Token JWT
    return {
        "access_token": token,
        "token_type": "bearer",
        "roles": roles,
        "user": user
    }

@router.post("/auth/register", response_model=UserResponse)
def register(reg_data: UserRegister, request: Request, db: Session = Depends(get_db)):
    """[CU04] Auto-registro autónomo de clientes"""
    # [CU04 - Paso 2] / [DSC004 - Paso 2] +register(datos)
    # [CU04 - Paso 3] / [DSC004 - Paso 3] +check_exists(email)
    existing = db.query(User).filter(User.email == reg_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya se encuentra registrado.")
    # [CU04 - Paso 4] / [DSC004 - Paso 4] +No existe (si pasa validación)

    # [CU04 - Paso 5] / [DSC004 - Paso 5] +insert(datos, rol='CLIENTE')
    user = User(
        email=reg_data.email,
        password_hash=get_password_hash(reg_data.password),
        first_name=reg_data.first_name,
        last_name=reg_data.last_name,
        phone=reg_data.phone,
        is_active=True
    )
    db.add(user)
    db.flush()

    role = db.query(Role).filter(Role.name == "CLIENTE").first()
    if not role:
        role = Role(name="CLIENTE", description="Cliente final de la tienda")
        db.add(role)
        db.flush()
    user.roles.append(role)
    # [CU04 - Paso 6] / [DSC004 - Paso 6] +Usuario Creado
    db.commit()
    db.refresh(user)

    log_event(db, user.id, "REGISTER", "users", user.id, {"email": user.email, "role": "CLIENTE"}, request.client.host)
    # [CU04 - Paso 7] / [DSC004 - Paso 7] +Notificar éxito
    return user

@router.post("/auth/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """[CU02] Cerrar sesión activa"""
    # [CU02 - Paso 2] / [DSC002 - Paso 2] +logout(token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        session = db.query(SessionToken).filter(SessionToken.token == token).first()
        if session:
            # [CU02 - Paso 3] / [DSC002 - Paso 3] +update_revoked(token)
            session.is_revoked = True
            # [CU02 - Paso 4] / [DSC002 - Paso 4] +Confirmación
            db.commit()
            log_event(db, current_user.id, "LOGOUT", "session_tokens", session.id, {"token_id": session.id}, request.client.host)
    # [CU02 - Paso 5] / [DSC002 - Paso 5] +Limpiar credenciales y redirigir (en frontend)
    return {"message": "Sesión cerrada correctamente."}

@router.post("/auth/recover")
def recover_credentials(data: UserRecover, request: Request, db: Session = Depends(get_db)):
    """[CU03] Recuperar credenciales de acceso"""
    # [CU03 - Paso 2] / [DSC003 - Paso 2] +recover(email)
    # [CU03 - Paso 3] / [DSC003 - Paso 3] +verificar_email(email)
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Respuesta neutra por seguridad; aviso solo en consola para diagnóstico.
        print(f"[RECOVER] Solicitud para un correo NO registrado: {data.email} (no se envía correo)")
        return {"message": "Si el correo está registrado, se enviará un enlace de recuperación."}
    # [CU03 - Paso 4] / [DSC003 - Paso 4] +Existe (si pasa validación)

    # [CU03 - Paso 5] / [DSC003 - Paso 5] +generar_y_enviar_token()
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.commit()

    # Enviar el correo con el enlace de restablecimiento (válido 5 minutos).
    reset_link = f"{settings.FRONTEND_URL}/recover?token={token}"
    sent = send_password_recovery_email(user.email, reset_link)
    print(f"[DEBUG] Enlace de recuperación para {user.email}: {reset_link}")

    log_event(db, user.id, "RECOVER", "users", user.id, {"email": user.email}, request.client.host)
    # [CU03 - Paso 6] / [DSC003 - Paso 6] +Mensaje de éxito
    response = {"message": "Si el correo está registrado, se enviará un enlace de recuperación."}
    # Ayuda de desarrollo: si SMTP no está configurado, devolvemos el enlace para poder
    # probar el flujo completo sin correo real. En producción (SMTP activo) NUNCA se expone.
    if not settings.smtp_enabled:
        response["dev_reset_link"] = reset_link
        response["message"] = (
            "SMTP no configurado (modo desarrollo): usa el enlace de 'dev_reset_link' "
            "o revísalo en la consola del servidor. Vence en 5 minutos."
        )
    return response

@router.post("/auth/reset-password")
def reset_password(data: PasswordReset, request: Request, db: Session = Depends(get_db)):
    """[CU03] Restablecer contraseña con token de seguridad (5 minutos)"""
    # [CU03 - Paso 8] / [DSC003 - Paso 8] +reset_password(token, nueva_clave)
    user = db.query(User).filter(User.reset_token == data.token).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado.")
    
    if not user.reset_token_expires or datetime.now(timezone.utc) > user.reset_token_expires:
        raise HTTPException(status_code=400, detail="El token de recuperación ha expirado (límite 5 minutos).")

    # [CU03 - Paso 9] / [DSC003 - Paso 9] +update_password(hash)
    user.password_hash = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    # [CU03 - Paso 10] / [DSC003 - Paso 10] +Actualizado
    db.commit()

    log_event(db, user.id, "RESET_PASSWORD", "users", user.id, {"email": user.email}, request.client.host)
    # [CU03 - Paso 11] / [DSC003 - Paso 11] +Redirigir a Login (en frontend)
    return {"message": "Contraseña restablecida con éxito."}

# --- ENDPOINTS: USUARIOS ---
admin_check = RoleChecker(allowed_roles=["SUPERADMIN"])

@router.get("/users", response_model=List[UserDetailResponse])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(admin_check)):
    """[CU05] Lista todos los usuarios"""
    return db.query(User).all()

@router.post("/users", response_model=UserDetailResponse, status_code=201)
def create_user(
    user_data: UserCreate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU05] Crea un nuevo usuario administrativo o cliente"""
    # [CU05 - Paso 2] / [DSC005 - Paso 2] +create_user(datos, roles)
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El correo electrónico ya existe.")
    
    # [CU05 - Paso 3] / [DSC005 - Paso 3] +insert(datos)
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_active=True
    )
    db.add(new_user)
    db.flush()
    # [CU05 - Paso 4] / [DSC005 - Paso 4] +ID Usuario (implícito)

    # [CU05 - Paso 5] / [DSC005 - Paso 5] +assign_roles(id, roles)
    for role_name in user_data.role_names:
        role = db.query(Role).filter(Role.name == role_name.upper()).first()
        if not role:
            role = Role(name=role_name.upper(), description=f"Rol de {role_name}")
            db.add(role)
            db.flush()
        new_user.roles.append(role)
    # [CU05 - Paso 6] / [DSC005 - Paso 6] +Roles asignados
    db.commit()
    db.refresh(new_user)

    log_event(db, current_user.id, "INSERT", "users", new_user.id, {"email": new_user.email, "roles": [r.name for r in new_user.roles]}, request.client.host)
    return new_user

@router.put("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: int, 
    user_data: UserUpdate, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU05] Modifica datos y roles de usuario"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    old_vals = {"email": user.email, "is_active": user.is_active, "roles": [r.name for r in user.roles]}

    for key, value in user_data.model_dump(exclude_unset=True).items():
        if key == "role_names":
            user.roles.clear()
            for r_name in value:
                role = db.query(Role).filter(Role.name == r_name.upper()).first()
                if not role:
                    role = Role(name=r_name.upper(), description=f"Rol de {r_name}")
                    db.add(role)
                    db.flush()
                user.roles.append(role)
        else:
            setattr(user, key, value)

    db.commit()
    db.refresh(user)

    log_event(db, current_user.id, "UPDATE", "users", user.id, {"old": old_vals, "new": {"email": user.email, "is_active": user.is_active, "roles": [r.name for r in user.roles]}}, request.client.host)
    return user

@router.delete("/users/{user_id}", response_model=UserDetailResponse)
def deactivate_user(
    user_id: int, 
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(admin_check)
):
    """[CU05] Baja lógica de usuario"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user.is_active = False
    db.commit()
    log_event(db, current_user.id, "UPDATE", "users", user.id, {"deactivated": True, "email": user.email}, request.client.host)
    return user

# --- ENDPOINTS: AUDITORÍA ---
@router.get("/audit/logs", response_model=List[AuditLogResponse])
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(admin_check)):
    """[CU36] Consulta la bitácora auditora"""
    # [CU36 - Paso 2] / [DSC036 - Paso 2] +get_audit_logs()
    # [CU36 - Paso 3] / [DSC036 - Paso 3] +select_all()
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
