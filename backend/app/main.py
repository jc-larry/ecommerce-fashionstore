from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Importar modelos para que SQLAlchemy los registre en metadata
from app.packages.seguridad_y_usuarios import models as security_models
from app.packages.catalogo_y_tiendas import models as catalog_models
from app.packages.catalogo_y_tiendas.branches import models as branches_models
from app.packages.inventario_y_proveedores.suppliers import models as suppliers_models
from app.packages.inventario_y_proveedores.merchandise import models as merchandise_models

# Importar routers de cada paquete
from app.packages.seguridad_y_usuarios.routers import router as security_router
from app.packages.catalogo_y_tiendas.routers import router as catalog_router
from app.packages.catalogo_y_tiendas.branches.routers import router as branches_router
from app.packages.inventario_y_proveedores.suppliers.routers import router as suppliers_router
from app.packages.inventario_y_proveedores.merchandise.routers import router as merchandise_router

# Crear tablas automáticamente al arrancar.
# Si la conexión a PostgreSQL falla, mostramos una guía clara y detenemos el arranque.
from sqlalchemy.exc import OperationalError
from app.db.session import engine, Base

try:
    Base.metadata.create_all(bind=engine)
    print("[DB] Tablas creadas/verificadas correctamente en PostgreSQL.")
except OperationalError as exc:  # pragma: no cover - depende del entorno
    raise RuntimeError(
        "No se pudo conectar a PostgreSQL. Revisa que el servidor esté activo y que "
        "DATABASE_URL en backend/.env apunte a una base existente "
        f"(usuario/clave/host/puerto/nombre). Detalle original: {exc!r}"
    ) from exc

app = FastAPI(
    title="FashionStore API",
    description="Backend para la plataforma de Comercio Electrónico con Vestidor Virtual (RA)",
    version="1.0.0",
)

# Configuración de CORS para permitir peticiones desde Angular (web) y Flutter (móvil).
# El navegador rechaza "*" + credenciales; usamos regex para cualquier puerto local
# y, si BACKEND_CORS_ORIGINS trae "*", desactivamos credenciales (no usamos cookies).
_origins = settings.BACKEND_CORS_ORIGINS
_wildcard = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if _wildcard else _origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?" if not _wildcard else r".*",
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ===================================================================
# REGISTRO DE ROUTERS POR PAQUETE UML
# ===================================================================
# PKG Seguridad y Usuarios   → CU01, CU02, CU03, CU04, CU05, CU36
app.include_router(security_router)
# PKG Catálogo y Tiendas     → CU07
app.include_router(catalog_router)
# PKG Sucursales              → CU06, CU09
app.include_router(branches_router)
# PKG Proveedores             → CU08
app.include_router(suppliers_router)
# PKG Inventario y Mercadería → CU10
app.include_router(merchandise_router)


@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de FashionStore"}
