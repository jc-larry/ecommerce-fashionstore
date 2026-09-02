from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Importar modelos para que SQLAlchemy los registre en metadata
from app.packages.seguridad_y_usuarios import models as security_models
from app.packages.catalogo_y_tiendas import models as catalog_models
from app.packages.catalogo_y_tiendas.branches import models as branches_models
from app.packages.inventario_y_proveedores.suppliers import models as suppliers_models
from app.packages.inventario_y_proveedores.merchandise import models as merchandise_models
# Ventas y Pagos: solo modelos en el Ciclo 1 (tablas orders/order_items/payments/invoices;
# jerarquías MedioDePago y Comprobante). Los routers llegan en el Ciclo 2 (CU17-CU24).
from app.packages.ventas_y_pagos import models as sales_models

# Importar routers de cada paquete
from app.packages.seguridad_y_usuarios.routers import router as security_router
from app.packages.catalogo_y_tiendas.routers import router as catalog_router
from app.packages.catalogo_y_tiendas.branches.routers import router as branches_router
from app.packages.inventario_y_proveedores.suppliers.routers import router as suppliers_router
from app.packages.inventario_y_proveedores.merchandise.routers import router as merchandise_router

# Crear tablas automáticamente al arrancar.
# Si la conexión a PostgreSQL falla, mostramos una guía clara y detenemos el arranque.
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.db.session import engine, Base

# Migraciones ligeras idempotentes (mientras no se adopte Alembic): añadir columnas nuevas
# a tablas que ya existían. `create_all` solo crea tablas faltantes, no columnas.
_COLUMN_UPGRADES = [
    "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS avg_cost NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS channel VARCHAR(10) NOT NULL DEFAULT 'ONLINE'",
]

# Normalización de datos: el correo es único e insensible a mayúsculas. Se pasan a
# minúsculas las cuentas creadas antes de esta regla, salvo que colisionen con otra.
_DATA_FIXES = [
    """
    UPDATE users u SET email = lower(u.email)
    WHERE u.email <> lower(u.email)
      AND NOT EXISTS (SELECT 1 FROM users o WHERE o.id <> u.id AND lower(o.email) = lower(u.email))
    """,
]

try:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for stmt in _COLUMN_UPGRADES:
            conn.execute(text(stmt))
        for stmt in _DATA_FIXES:
            conn.execute(text(stmt))
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
# PKG Seguridad y Usuarios      → CU01, CU02, CU03, CU04, CU05, CU36
app.include_router(security_router)
# PKG Catálogo y Tiendas        → CU07, CU11  (consulta pública del catálogo)
app.include_router(catalog_router)
# PKG Catálogo y Tiendas        → CU06 (sucursales), CU09 (empleados de sucursal)
app.include_router(branches_router)
# PKG Inventario y Proveedores  → CU08 (proveedores)
app.include_router(suppliers_router)
# PKG Inventario y Proveedores  → CU10 (ingresos), CU37 (valoración), CU38 (ajustes)
app.include_router(merchandise_router)


@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de FashionStore"}
