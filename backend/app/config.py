import os
from dotenv import load_dotenv

load_dotenv()


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


class Settings:
    """Configuración central de la plataforma FashionStore (leída desde variables de entorno)."""

    PROJECT_NAME: str = "FashionStore"

    # --- Base de datos (PostgreSQL) ---
    # Formato esperado: postgresql+psycopg2://usuario:contrasena@host:puerto/basededatos
    # Normaliza automáticamente URLs de Render o proveedores cloud (postgres:// -> postgresql+psycopg2://)
    _raw_db: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/fashionstore",
    )
    if _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql+psycopg2://", 1)
    elif _raw_db.startswith("postgresql://") and not _raw_db.startswith("postgresql+psycopg2://"):
        _raw_db = _raw_db.replace("postgresql://", "postgresql+psycopg2://", 1)

    DATABASE_URL: str = _raw_db

    # --- Seguridad / JWT ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clave_secreta_super_segura_para_el_primer_parcial")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[str] = _csv(
        "BACKEND_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
    )

    # --- Frontend (para armar enlaces en los correos) ---
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")

    # --- Correo saliente (SMTP) para el enlace de recuperación (CU03) ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", ""))
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "FashionStore")

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_USER and self.SMTP_PASSWORD)


settings = Settings()
