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
from app.packages.paquete_seguridad_usuarios.models import User, Role, user_roles
from app.packages.paquete_seguridad_usuarios.services import get_password_hash

# Import other models to ensure they are registered with Base.metadata before create_all
from app.packages.paquete_catalogo_y_tiendas import models as catalog_models
from app.packages.paquete_catalogo_y_tiendas.branches import models as branches_models
from app.packages.paquete_inventario_y_proveedores.suppliers import models as suppliers_models
from app.packages.paquete_inventario_y_proveedores.merchandise import models as merchandise_models
from app.packages.paquete_ventas_y_pagos import models as sales_models

# Roles base del sistema (RF06)
BASE_ROLES = {
    "SUPERADMIN": "Administrador principal del sistema",
    "ADMINISTRADOR": "Administrador general de operaciones",
    "ENCARGADO": "Encargado de sucursal",
    "CAJERO": "Cajero de punto de venta",
    "CLIENTE": "Cliente final de la tienda",
    "PROVEEDOR": "Proveedor textil y confeccionista",
    "REPARTIDOR": "Repartidor de logística y delivery de última milla",
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

        # 3. Asegurar sucursales distribuidas exclusivamente en Santa Cruz de la Sierra (CU06)
        from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
        branches_data = [
            {
                "name": "FashionStore Equipetrol",
                "code": "SUC-EQP",
                "city": "Santa Cruz",
                "zone": "Equipetrol",
                "address": "Av. San Martín esquina Calle 8",
                "reference": "Frente a Starbucks Equipetrol",
                "phone": "33445566",
                "whatsapp": "77011223",
                "opening_time": "09:00",
                "closing_time": "21:00",
                "days_open": "Lunes a Domingo",
                "has_fitting_room": True,
            },
            {
                "name": "FashionStore Plan 3000",
                "code": "SUC-P3K",
                "city": "Santa Cruz",
                "zone": "Plan 3000",
                "address": "Av. Paurito casi Rotonda Principal",
                "reference": "A dos cuadras del Obelisco Plan 3000",
                "phone": "33889900",
                "whatsapp": "77022334",
                "opening_time": "08:30",
                "closing_time": "20:30",
                "days_open": "Lunes a Sábado",
                "has_fitting_room": True,
            },
            {
                "name": "FashionStore Ventura Mall",
                "code": "SUC-VTR",
                "city": "Santa Cruz",
                "zone": "Ventura Mall",
                "address": "4to Anillo y Av. San Martín - Nivel 2",
                "reference": "Pasillo de Modas frente al patio de comidas",
                "phone": "33112233",
                "whatsapp": "77033445",
                "opening_time": "10:00",
                "closing_time": "22:00",
                "days_open": "Lunes a Domingo",
                "has_fitting_room": True,
            },
            {
                "name": "FashionStore Centro",
                "code": "SUC-CEN",
                "city": "Santa Cruz",
                "zone": "Centro",
                "address": "Calle Junín #145",
                "reference": "A media cuadra de la Plaza 24 de Septiembre",
                "phone": "33221100",
                "whatsapp": "77044556",
                "opening_time": "08:30",
                "closing_time": "20:00",
                "days_open": "Lunes a Sábado",
                "has_fitting_room": True,
            },
        ]
        for b_data in branches_data:
            b_exist = db.query(Branch).filter(Branch.name == b_data["name"]).first()
            if not b_exist:
                new_b = Branch(**b_data)
                db.add(new_b)
                print(f"[OK] Sucursal Santa Cruz creada: {b_data['name']}")
        db.commit()

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
