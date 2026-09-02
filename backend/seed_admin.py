"""Seeder de datos base para FashionStore.

Crea los roles del sistema (SUPERADMIN, ENCARGADO, CAJERO, CLIENTE) y un usuario
administrador inicial. Ejecutar una sola vez tras crear la base de datos:

    python seed_admin.py
"""

import sys
import os

# Añadir el backend al path para poder importar la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine, Base
from app.packages.seguridad_y_usuarios.models import User, Role, user_roles
from app.packages.seguridad_y_usuarios.services import get_password_hash

# Import other models to ensure they are registered with Base.metadata before create_all
from app.packages.catalogo_y_tiendas import models as catalog_models
from app.packages.catalogo_y_tiendas.branches import models as branches_models
from app.packages.inventario_y_proveedores.suppliers import models as suppliers_models
from app.packages.inventario_y_proveedores.merchandise import models as merchandise_models
from app.packages.ventas_y_pagos import models as sales_models

# Roles base del sistema (RF06)
BASE_ROLES = {
    "SUPERADMIN": "Administrador principal del sistema",
    "ENCARGADO": "Encargado de sucursal",
    "CAJERO": "Cajero de punto de venta",
    "CLIENTE": "Cliente final de la tienda",
}

ADMIN_EMAIL = "admin@fashionstore.com"
ADMIN_PASSWORD = "Admin123!"


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Crear los roles base que no existan
        roles = {}
        for name, description in BASE_ROLES.items():
            role = db.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()
                print(f"[OK] Rol creado: {name}")
            roles[name] = role
        db.commit()

        # 2. Crear el usuario administrador si no existe
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if not user:
            user = User(
                email=ADMIN_EMAIL,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                first_name="Admin",
                last_name="FashionStore",
                phone="77712345",
            )
            db.add(user)
            db.flush()
            user.roles.append(roles["SUPERADMIN"])
            db.commit()
            print("[EXITO] Usuario administrador creado.")
        else:
            if roles["SUPERADMIN"] not in user.roles:
                user.roles.append(roles["SUPERADMIN"])
                db.commit()
            print("[INFO] El usuario administrador ya existe.")

        print(f"       Correo: {ADMIN_EMAIL}")
        print(f"       Contrasena: {ADMIN_PASSWORD}")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Iniciando seeder de base de datos...")
    seed()
