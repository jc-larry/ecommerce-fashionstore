import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

# [CU01] Inicialización del contexto de encriptación para contraseñas usando BCrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# BCrypt solo procesa los primeros 72 bytes; truncamos de forma explícita para
# evitar errores con contraseñas largas.
_BCRYPT_MAX_BYTES = 72


def _truncate_for_bcrypt(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) <= _BCRYPT_MAX_BYTES:
        return password
    return encoded[:_BCRYPT_MAX_BYTES].decode("utf-8", "ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """[CU01] Verifica si la contraseña provista coincide con el hash guardado"""
    return pwd_context.verify(_truncate_for_bcrypt(plain_password), hashed_password)

def get_password_hash(password: str) -> str:
    """[CU04 / CU05] Genera un hash seguro BCrypt para guardar nuevas contraseñas"""
    return pwd_context.hash(_truncate_for_bcrypt(password))

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """[CU01] Genera un token de acceso JWT firmado digitalmente"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # `jti` (identificador único del token) e `iat` garantizan que dos inicios de
    # sesión, aunque ocurran en el mismo segundo, produzcan tokens distintos y no
    # choquen con la restricción UNIQUE de session_tokens.token.
    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "jti": uuid.uuid4().hex,
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Union[str, None]:
    """[CU01 / CU02 / CU36] Decodifica un JWT para extraer el sujeto (ID del usuario)"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None
