# FashionStore · Backend (FastAPI)

API REST del Ciclo 1: autenticación (JWT), gestión de usuarios/roles, sucursales,
catálogo, proveedores, ingreso de mercadería y bitácora de auditoría.

## Requisitos

- Python 3.11+
- PostgreSQL 14+ (gestionado con pgAdmin 4)

## Puesta en marcha

```bash
cd backend

# 1. Entorno virtual + dependencias
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2. Base de datos: en pgAdmin -> CREATE DATABASE fashionstore;

# 3. Configuración
copy .env.example .env           # y edita DATABASE_URL con tu usuario/clave

# 4. Datos base (roles + usuario admin) y creación de tablas
python seed_admin.py

# 5. Servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Documentación interactiva: http://127.0.0.1:8000/docs
- Usuario inicial: `admin@fashionstore.com` / `Admin123!`

## Estructura

```
app/
├── main.py                 # App FastAPI + registro de routers
├── config.py               # Settings (lee .env)
├── db/session.py           # Engine + SessionLocal + Base
└── packages/               # Un paquete por subsistema UML
    ├── seguridad_y_usuarios/     # CU01–CU05, CU36
    ├── catalogo_y_tiendas/       # CU06, CU07, CU09
    └── inventario_y_proveedores/ # CU08, CU10
```
