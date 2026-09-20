from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Importar modelos para que SQLAlchemy los registre en metadata
from app.packages.seguridad_y_usuarios import models as security_models
from app.packages.catalogo_y_tiendas import models as catalog_models
from app.packages.catalogo_y_tiendas.branches import models as branches_models
from app.packages.inventario_y_proveedores.suppliers import models as suppliers_models
from app.packages.inventario_y_proveedores.suppliers import offer_models as supplier_offer_models
from app.packages.inventario_y_proveedores.merchandise import models as merchandise_models
# Ventas y Pagos: solo modelos en el Ciclo 1 (tablas orders/order_items/payments/invoices;
# jerarquías MedioDePago y Comprobante). Los routers llegan en el Ciclo 2 (CU17-CU24).
from app.packages.ventas_y_pagos import models as sales_models
# Ciclo 3: Reservas, Envíos, Inteligente/Analítica, Notificaciones
from app.packages.reservas_y_citas import models as reservation_models
from app.packages.envios_y_logistica import models as logistics_models
from app.packages.envios_y_logistica.delivery_persons import models as delivery_persons_models
from app.packages.inteligente_y_analitica import models as analytics_models
from app.packages.notificaciones import models as notification_models

# Importar routers de cada paquete
from app.packages.seguridad_y_usuarios.routers import router as security_router
from app.packages.catalogo_y_tiendas.routers import router as catalog_router
from app.packages.catalogo_y_tiendas.branches.routers import router as branches_router
from app.packages.inventario_y_proveedores.suppliers.routers import router as suppliers_router
from app.packages.inventario_y_proveedores.suppliers.offer_routers import router as supplier_offers_router
from app.packages.inventario_y_proveedores.merchandise.routers import router as merchandise_router
from app.packages.ventas_y_pagos.routers import router as sales_router
from app.packages.ventas_y_pagos.paypal_routers import router as paypal_router
from app.packages.reservas_y_citas.routers import router as reservations_router
from app.packages.envios_y_logistica.routers import router as logistics_router
from app.packages.envios_y_logistica.delivery_persons.routers import router as delivery_persons_router
from app.packages.inteligente_y_analitica.routers import router as analytics_router
from app.packages.notificaciones.routers import router as notifications_router


# Crear tablas automáticamente al arrancar.
# Si la conexión a PostgreSQL falla, mostramos una guía clara y detenemos el arranque.
import os
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.db.session import engine, Base

# Migraciones ligeras idempotentes (mientras no se adopte Alembic): añadir columnas nuevas
# a tablas que ya existían. `create_all` solo crea tablas faltantes, no columnas.
_COLUMN_UPGRADES = [
    "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS avg_cost NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_reservado INT NOT NULL DEFAULT 0",
    "ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_en_transito INT NOT NULL DEFAULT 0",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS channel VARCHAR(10) NOT NULL DEFAULT 'ONLINE'",
    "ALTER TABLE product_images ALTER COLUMN color_id DROP NOT NULL",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS compare_at_price NUMERIC(10, 2)",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS code VARCHAR(20)",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS city VARCHAR(50) DEFAULT 'Santa Cruz'",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS zone VARCHAR(80)",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS reference VARCHAR(255)",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS whatsapp VARCHAR(20)",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS opening_time VARCHAR(10) DEFAULT '09:00'",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS closing_time VARCHAR(10) DEFAULT '21:00'",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS days_open VARCHAR(100) DEFAULT 'Lunes a Sábado'",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS has_fitting_room BOOLEAN DEFAULT TRUE",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS pickup_enabled BOOLEAN DEFAULT TRUE",
    "ALTER TABLE branches ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)",
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL",
    "ALTER TABLE sizes ADD COLUMN IF NOT EXISTS category_type VARCHAR(30)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS material VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS neck_type VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS sleeve_length VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS tags VARCHAR(255)",
    "ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'APPROVED'",
    "ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS moderator_id INTEGER REFERENCES users(id) ON DELETE SET NULL",
    "ALTER TABLE inventory_ledger ALTER COLUMN movement_type TYPE VARCHAR(30)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS subtotal NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS coupon_code VARCHAR(30)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS cash_shift_id INTEGER REFERENCES cash_shifts(id) ON DELETE SET NULL",
    "CREATE INDEX IF NOT EXISTS idx_inventory_branch_stock ON inventory (branch_id, stock_actual)",
    "CREATE INDEX IF NOT EXISTS idx_inventory_variant_stock ON inventory (variant_id, stock_actual)",
    "CREATE INDEX IF NOT EXISTS idx_products_active_price ON products (is_active, base_price)",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products (category_id)",
    "CREATE INDEX IF NOT EXISTS idx_product_variants_size_color ON product_variants (size_id, color_id)",
    "CREATE INDEX IF NOT EXISTS idx_product_reviews_status ON product_reviews (status, product_id)",
    "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(50)",
    "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS shipping_cost NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS notes VARCHAR(255)",
    "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE purchase_details ADD COLUMN IF NOT EXISTS previous_avg_cost NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE purchase_details ADD COLUMN IF NOT EXISTS new_avg_cost NUMERIC(10, 2) DEFAULT 0",
    "ALTER TABLE quotations ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE virtual_tryon_captures ALTER COLUMN photo_url TYPE TEXT",
    "ALTER TABLE virtual_tryon_captures ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES virtual_tryon_sessions(id) ON DELETE SET NULL",
    "ALTER TABLE virtual_tryon_captures ADD COLUMN IF NOT EXISTS original_photo_url TEXT",
    "ALTER TABLE virtual_tryon_captures ADD COLUMN IF NOT EXISTS generation_model VARCHAR(100) DEFAULT 'IDM-VTON'",
    "ALTER TABLE virtual_tryon_captures ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.92",
    # Migraciones para Shipments y Repartidores (CU29, CU30)
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_person_id INTEGER REFERENCES delivery_persons(id) ON DELETE SET NULL",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_date DATE",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_time VARCHAR(20)",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_attempts INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS failed_reason VARCHAR(255)",
    # Evidencia fotográfica de entrega del repartidor
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS delivery_photo_url TEXT",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS received_by_name VARCHAR(100)",
    "ALTER TABLE shipment_tracking_events ADD COLUMN IF NOT EXISTS photo_url TEXT",
    # Galería de fotos de ofertas de proveedores y vínculo con el catálogo
    "ALTER TABLE supplier_offers ALTER COLUMN image_url TYPE TEXT",
    "ALTER TABLE supplier_offers ADD COLUMN IF NOT EXISTS image_urls TEXT",
    "ALTER TABLE supplier_offers ADD COLUMN IF NOT EXISTS product_id INTEGER REFERENCES products(id) ON DELETE SET NULL",
    # Migraciones para Proveedores (CU08, CU10)
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS city VARCHAR(50) DEFAULT 'Santa Cruz'",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2) DEFAULT 5.0",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS delivery_time_days INTEGER DEFAULT 7",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS notes VARCHAR(255)",
    "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS specialty VARCHAR(100)",
    # Migraciones para Reservas y Citas (CU26, CU27, CU28)
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS appointment_date DATE",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS appointment_time VARCHAR(10)",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS reschedule_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS grace_period_notified BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) DEFAULT 'TARJETA'",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS payment_reference VARCHAR(100)",
    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS deposit_paid BOOLEAN NOT NULL DEFAULT TRUE",
    # Migraciones para Pagos y Pasarela PayPal (CU18, CU19)
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS paypal_payer_id VARCHAR(50)",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS paypal_payer_email VARCHAR(100)",
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

# Carpeta física de almacenamiento de imágenes
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "products"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Configuración de CORS para permitir peticiones desde Angular (web) y Flutter (móvil).
# El navegador rechaza "*" + credenciales; usamos regex para cualquier puerto local
# y, si BACKEND_CORS_ORIGINS trae "*", desactivamos credenciales (no usamos cookies).
_origins = settings.BACKEND_CORS_ORIGINS
_wildcard = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if _wildcard else _origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?" if not _wildcard else r".*",
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
app.include_router(supplier_offers_router)
# PKG Inventario y Proveedores  → CU10 (ingresos), CU37 (valoración), CU38 (ajustes)
app.include_router(merchandise_router)
# PKG Ventas y Pagos            → CU17 a CU24 (Carrito, Checkout, POS, Facturación, Cotización, Devolución, Arqueo)
app.include_router(sales_router)
app.include_router(paypal_router, prefix="/api/v1")
# PKG Reservas y Citas          → CU26 (agendar), CU27 (Kanban), CU28 (cancelar/liberar), CU25 (conversión POS)
app.include_router(reservations_router)
# PKG Envíos y Logística        → CU29 (despachos), CU30 (tracking), CU31 (zonas y tarifas)
app.include_router(delivery_persons_router)
app.include_router(logistics_router)
# PKG Inteligente y Analítica   → CU32 (vestidor RA), CU33 (chatbot IA), CU34 (voz NLP), CU35 (reportes), CU39 (dashboard)
app.include_router(analytics_router)
# PKG Notificaciones            → CU40 (in-app y confirmaciones email)
app.include_router(notifications_router)



@app.get("/")
async def root():
    return {"message": "Bienvenido a la API de FashionStore"}


@app.get("/download-apk", tags=["Móvil"])
@app.get("/api/v1/download-apk", tags=["Móvil"])
async def download_mobile_apk():
    """Descarga directa del APK compilado de la aplicación móvil de FashionStore."""
    apk_candidates = [
        os.path.join(UPLOAD_DIR, "apk", "fashionstore.apk"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mobile", "build", "app", "outputs", "flutter-apk", "app-release.apk"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mobile", "build", "app", "outputs", "flutter-apk", "app-debug.apk"),
    ]
    for apk_path in apk_candidates:
        if os.path.exists(apk_path) and os.path.getsize(apk_path) > 0:
            return FileResponse(
                path=apk_path,
                media_type="application/vnd.android.package-archive",
                filename="fashionstore.apk",
                headers={
                    "Content-Disposition": 'attachment; filename="fashionstore.apk"',
                    "Cache-Control": "no-cache",
                }
            )
    raise HTTPException(
        status_code=404,
        detail="El archivo APK aún no está disponible para descarga. Ejecuta 'flutter build apk --release' en la carpeta mobile/."
    )
