"""
Script de Migración Maestra de Datos para FashionStore
=====================================================
Ejecuta la carga e integración de:
1. Saneamiento y cierre de turnos de caja huérfanos.
2. 4 Sucursales emblemáticas de Bolivia (Equipetrol, Ventura Mall, Megacenter La Paz, El Prado Cochabamba).
3. 5 Proveedores formales con NIT boliviano.
4. Personal de tienda por sucursal (Encargados y Cajeros) en branch_employees.
5. Catálogo de moda completo (12 prendas icónicas, fotos Unsplash HD, tallas S-M-L, colores y ofertas).
6. Inventario completo por sucursal (stock_actual entre 15 y 45 por variante).
7. Órdenes de compra históricas (purchase_orders + ledger de ingreso).
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.session import engine, SessionLocal, Base
from app.packages.catalogo_y_tiendas.branches.models import Branch, branch_employees
from app.packages.seguridad_y_usuarios.models import User, Role, user_roles
from app.packages.seguridad_y_usuarios.services import get_password_hash
from app.packages.inventario_y_proveedores.suppliers.models import Supplier
from app.packages.inventario_y_proveedores.merchandise.models import (
    Inventory, InventoryLedger, PurchaseOrder, PurchaseDetail
)
from app.packages.catalogo_y_tiendas.models import (
    Category, Product, ProductVariant, ProductImage, Color, Size, Season
)
from app.packages.ventas_y_pagos.models import CashShift

PASSWORD_DEFAULT = "Password123!"

BRANCHES_DATA = [
    {
        "id": 1,
        "name": "Sucursal Equipetrol - Santa Cruz",
        "code": "EQP-01",
        "city": "Santa Cruz",
        "zone": "Equipetrol Norte",
        "address": "Av. San Martín esq. Calle 8 #450",
        "reference": "A 2 cuadras del Hotel Los Tajibos",
        "phone": "3-3458900",
        "whatsapp": "+59178012345",
        "opening_time": "09:00",
        "closing_time": "21:30",
        "days_open": "Lunes a Domingo",
        "has_fitting_room": True,
        "pickup_enabled": True,
        "image_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&auto=format&fit=crop&q=80",
        "latitude": Decimal("-17.76940000"),
        "longitude": Decimal("-63.19320000"),
    },
    {
        "id": 2,
        "name": "Sucursal Ventura Mall",
        "code": "VTR-02",
        "city": "Santa Cruz",
        "zone": "4to Anillo, Ventura Mall 1er Nivel",
        "address": "Av. 4to Anillo esq. Av. San Martín, Local 142",
        "reference": "Planta Baja, pasillo de moda femenina",
        "phone": "3-3882000",
        "whatsapp": "+59178012346",
        "opening_time": "10:00",
        "closing_time": "22:00",
        "days_open": "Lunes a Domingo",
        "has_fitting_room": True,
        "pickup_enabled": True,
        "image_url": "https://images.unsplash.com/photo-1567401893414-76b7b1e5a7a5?w=800&auto=format&fit=crop&q=80",
        "latitude": Decimal("-17.75380000"),
        "longitude": Decimal("-63.19950000"),
    },
    {
        "id": 3,
        "name": "Sucursal Megacenter - La Paz",
        "code": "MGC-03",
        "city": "La Paz",
        "zone": "Irpavi, Zona Sur",
        "address": "Av. Rafael Pabón s/n, Centro Comercial Megacenter",
        "reference": "Piso 1, Galería Comercial de Moda",
        "phone": "2-2114000",
        "whatsapp": "+59178012347",
        "opening_time": "10:00",
        "closing_time": "21:00",
        "days_open": "Lunes a Domingo",
        "has_fitting_room": True,
        "pickup_enabled": True,
        "image_url": "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=800&auto=format&fit=crop&q=80",
        "latitude": Decimal("-16.53610000"),
        "longitude": Decimal("-68.08740000"),
    },
    {
        "id": 4,
        "name": "Sucursal El Prado - Cochabamba",
        "code": "PRD-04",
        "city": "Cochabamba",
        "zone": "Recoleta / El Prado",
        "address": "Av. Ballivián #642 entre La Paz y Chuquisaca",
        "reference": "Frente a Plaza Colón",
        "phone": "4-4251000",
        "whatsapp": "+59178012348",
        "opening_time": "09:30",
        "closing_time": "20:30",
        "days_open": "Lunes a Sábado",
        "has_fitting_room": True,
        "pickup_enabled": True,
        "image_url": "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&auto=format&fit=crop&q=80",
        "latitude": Decimal("-17.38950000"),
        "longitude": Decimal("-66.15680000"),
    },
]

SUPPLIERS_DATA = [
    {
        "id": 1,
        "nit": "1028374021",
        "name": "Textiles & Hilados Andinos S.R.L.",
        "category": "Telas, Lino y Algodón Pima",
        "contact_name": "Ing. Carlos Mendoza",
        "email": "ventas@textilesandinos.bo",
        "phone": "2-2204567",
        "address": "Parque Industrial Kallutaca Manzano 4, La Paz",
    },
    {
        "id": 3,
        "nit": "3492810018",
        "name": "Confecciones & Moda Bellissima S.A.",
        "category": "Vestidos de Fiesta y Coctel",
        "contact_name": "Lic. Mariana Vaca",
        "email": "contacto@bellissimafashion.bo",
        "phone": "3-3567890",
        "address": "Av. Banzer Km 5.5, Santa Cruz",
    },
    {
        "id": 4,
        "nit": "4819203015",
        "name": "Importadora Textil Denim & Co.",
        "category": "Jeans y Ropa Mezclilla",
        "contact_name": "Roberto Claros",
        "email": "pedidos@denimco.bo",
        "phone": "4-4112233",
        "address": "Av. Blanco Galindo Km 3, Cochabamba",
    },
    {
        "id": 5,
        "nit": "5192837012",
        "name": "Vogue Latin America Importaciones",
        "category": "Blazers, Abrigos y Alta Costura",
        "contact_name": "Sofia Gutiérrez",
        "email": "gerencia@voguelat.com",
        "phone": "3-3334455",
        "address": "Edificio Ambassador Piso 8, Equipetrol, Santa Cruz",
    },
    {
        "id": 6,
        "nit": "6281930019",
        "name": "Activewear Bolivia Athletic Wear",
        "category": "Ropa Deportiva y Compresión",
        "contact_name": "Javier Montes",
        "email": "ventas@activewear.bo",
        "phone": "2-2778899",
        "address": "Calle 21 de Calacoto #8200, La Paz",
    },
]

STAFF_DATA = [
    # Equipetrol (Branch 1)
    {"email": "encargada.equipetrol@fashionstore.com", "first_name": "Valeria", "last_name": "Roca", "role": "ENCARGADO", "branch_id": 1, "phone": "78011221"},
    {"email": "cajero.equipetrol@fashionstore.com", "first_name": "Mateo", "last_name": "Suarez", "role": "CAJERO", "branch_id": 1, "phone": "78011222"},
    # Ventura Mall (Branch 2)
    {"email": "encargada.ventura@fashionstore.com", "first_name": "Camila", "last_name": "Vargas", "role": "ENCARGADO", "branch_id": 2, "phone": "78022331"},
    {"email": "cajera.ventura@fashionstore.com", "first_name": "Luciana", "last_name": "Montaño", "role": "CAJERO", "branch_id": 2, "phone": "78022332"},
    # Megacenter La Paz (Branch 3)
    {"email": "encargada.megacenter@fashionstore.com", "first_name": "Daniela", "last_name": "Perez", "role": "ENCARGADO", "branch_id": 3, "phone": "78033441"},
    {"email": "cajero.megacenter@fashionstore.com", "first_name": "Alejandro", "last_name": "Flores", "role": "CAJERO", "branch_id": 3, "phone": "78033442"},
    # El Prado Cochabamba (Branch 4)
    {"email": "encargada.prado@fashionstore.com", "first_name": "Andrea", "last_name": "Torrico", "role": "ENCARGADO", "branch_id": 4, "phone": "78044551"},
    {"email": "cajero.prado@fashionstore.com", "first_name": "Gabriel", "last_name": "Guzman", "role": "CAJERO", "branch_id": 4, "phone": "78044552"},
]

CATALOG_PRODUCTS = [
    {
        "id": 1,
        "name": "Camisa Lino Premium Manga Larga",
        "cat_name": "Camisas",
        "description": "Camisa de lino 100% transpirable con corte moderno regular fit. Ideal para climas cálidos y ocasiones casuales o ejecutivas.",
        "cost": Decimal("70.00"),
        "base_price": Decimal("149.00"),
        "compare_at_price": Decimal("189.00"),
        "material": "100% Lino Natural",
        "neck_type": "Cuello camisero clásico",
        "sleeve_length": "Manga larga con botones de nácar",
        "tags": "Lino, Premium, Verano, Casual",
        "images": [
            "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Blanco", "Beige / Nude", "Azul Marino"],
        "sku_prefix": "CAM-LIN",
    },
    {
        "id": 2,
        "name": "Blusa Satinada Escote V Elegance",
        "cat_name": "Blusas",
        "description": "Blusa confeccionada en satén de seda brillante con caída suave y escote en V refinado. Acabados de sastrería fina.",
        "cost": Decimal("60.00"),
        "base_price": Decimal("129.00"),
        "compare_at_price": Decimal("159.00"),
        "material": "Satén de Seda y Viscosa",
        "neck_type": "Escote en V profundo",
        "sleeve_length": "Manga 3/4 fluida",
        "tags": "Seda, Noche, Elegante, Oficina",
        "images": [
            "https://images.unsplash.com/photo-1551803091-e20673f15770?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1564257631407-4deb129f044b?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["XS", "S", "M", "L"],
        "colors": ["Blanco", "Rosa Pastel", "Negro"],
        "sku_prefix": "BLU-SAT",
    },
    {
        "id": 3,
        "name": "Chaqueta Biker Cuero Vegano Borde Metálico",
        "cat_name": "Chaquetas / Chamarras",
        "description": "Icónica chaqueta de cuero sintético premium de alta durabilidad con cremalleras cromadas y forro térmico acolchado.",
        "cost": Decimal("180.00"),
        "base_price": Decimal("369.00"),
        "compare_at_price": Decimal("449.00"),
        "material": "Piel Sintética PU Premium / Forro Poliéster",
        "neck_type": "Solapa con broches metálicos",
        "sleeve_length": "Manga larga con cremallera en puños",
        "tags": "Biker, Cuero, Invierno, Vanguardia",
        "images": [
            "https://images.unsplash.com/photo-1521223890158-f9f7c3d5d504?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Negro", "Terracota"],
        "sku_prefix": "CHA-BIK",
    },
    {
        "id": 4,
        "name": "Crop Top Ribbed Verano Algodón",
        "cat_name": "Tops / Crop Tops",
        "description": "Top acanalado de textura suave con tirantes finos ajustables. Muy elástico, cómodo y versátil para outfits diarios.",
        "cost": Decimal("35.00"),
        "base_price": Decimal("79.00"),
        "compare_at_price": None,
        "material": "95% Algodón Acanalado / 5% Elastano",
        "neck_type": "Cuello cuadrado moderno",
        "sleeve_length": "Sin mangas / Tirantes finos",
        "tags": "Ribbed, Básico, Algodón, Fresco",
        "images": [
            "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["XS", "S", "M", "L"],
        "colors": ["Blanco", "Negro", "Beige / Nude"],
        "sku_prefix": "TOP-RIB",
    },
    {
        "id": 5,
        "name": "Jeans Denim Tiro Alto Wide Leg",
        "cat_name": "Jeans / Mezclilla",
        "description": "Jeans holgados en pierna ancha con tiro ultra alto para una silueta estilizada. Mezclilla rígida 100% algodón lavado vintage.",
        "cost": Decimal("95.00"),
        "base_price": Decimal("199.00"),
        "compare_at_price": Decimal("249.00"),
        "material": "100% Denim Algodón Lavado",
        "neck_type": "Tiro alto con botón remache",
        "sleeve_length": "Largo completo al tobillo",
        "tags": "Denim, Wide Leg, Tendencia, Tiro Alto",
        "images": [
            "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1582418702059-97ebafb35d09?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["36", "38", "40", "42"],
        "colors": ["Azul Marino", "Negro", "Blanco"],
        "sku_prefix": "JEA-WID",
    },
    {
        "id": 6,
        "name": "Vestido Midi Seda Floral Primavera",
        "cat_name": "Vestidos",
        "description": "Vestido midi con estampado floral exclusivo sobre tejido suave y fluido. Cinturón a juego y abertura lateral sutil.",
        "cost": Decimal("110.00"),
        "base_price": Decimal("229.00"),
        "compare_at_price": Decimal("289.00"),
        "material": "Chifón y Seda con Forro Suave",
        "neck_type": "Escote cruzado / En V",
        "sleeve_length": "Manga corta con vuelo",
        "tags": "Floral, Fiesta, Coctel, Primavera",
        "images": [
            "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1496747611176-843222e1e57c?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Rosa Pastel", "Blanco", "Terracota"],
        "sku_prefix": "VES-FLO",
    },
    {
        "id": 7,
        "name": "Blazer Sastrería Oversize Ivory Gold",
        "cat_name": "Blazers",
        "description": "Blazer de corte sastre estructurado con hombreras suaves y botones dorados grabados. La pieza clave del power dressing.",
        "cost": Decimal("160.00"),
        "base_price": Decimal("329.00"),
        "compare_at_price": Decimal("399.00"),
        "material": "Crepé de Sastrería con Forro Raso",
        "neck_type": "Solapa en punta ejecutiva",
        "sleeve_length": "Manga larga sastre con 4 botones",
        "tags": "Blazer, Formal, Ejecutivo, Tendencia",
        "images": [
            "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Beige / Nude", "Negro", "Blanco"],
        "sku_prefix": "BLA-OVE",
    },
    {
        "id": 8,
        "name": "Suéter Cuello Alto Tejido Fino Cashmere Touch",
        "cat_name": "Suéteres y Tejidos",
        "description": "Suéter de punto fino ultra abrigador con textura cashmere touch. Tacto extrasuave sin picazón, ideal para media estación.",
        "cost": Decimal("90.00"),
        "base_price": Decimal("189.00"),
        "compare_at_price": Decimal("230.00"),
        "material": "Lana Merino y Acrílico Soft Touch",
        "neck_type": "Cuello alto tortuga vuelto",
        "sleeve_length": "Manga larga con puños acanalados",
        "tags": "Punto, Invierno, Cálido, Suave",
        "images": [
            "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Beige / Nude", "Café Chocolate", "Gris Jaspe"],
        "sku_prefix": "SUE-CUE",
    },
    {
        "id": 9,
        "name": "Falda Midi Plisada Satinada Soleada",
        "cat_name": "Faldas",
        "description": "Falda midi con microplisado permanente y pretina elástica oculta. Movimiento fluido y reflejos satinados irresistibles.",
        "cost": Decimal("75.00"),
        "base_price": Decimal("159.00"),
        "compare_at_price": None,
        "material": "Satén de Poliéster Plisado",
        "neck_type": "Pretina alta elástica",
        "sleeve_length": "Largo midi bajo la rodilla",
        "tags": "Plisada, Satén, Fiesta, Casual Chic",
        "images": [
            "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Mostaza", "Terracota", "Negro"],
        "sku_prefix": "FAL-PLI",
    },
    {
        "id": 10,
        "name": "Enterizo Palazzo Noche con Fajín",
        "cat_name": "Enterizos / Monos",
        "description": "Jumpsuit de fiesta con pantalón palazzo fluido y escote halter cruzado. Incluye lazo de ajuste para ceñir la cintura.",
        "cost": Decimal("130.00"),
        "base_price": Decimal("279.00"),
        "compare_at_price": Decimal("340.00"),
        "material": "Crepé Georgette con Caída Pesada",
        "neck_type": "Halter con espalda descubierta",
        "sleeve_length": "Sin mangas",
        "tags": "Enterizo, Noche, Gala, Palazzo",
        "images": [
            "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Rojo Vino", "Negro", "Azul Marino"],
        "sku_prefix": "ENT-PAL",
    },
    {
        "id": 11,
        "name": "Leggings Deportivos Compresión Alta Pro",
        "cat_name": "Leggings deportivos",
        "description": "Malla técnica deportiva de compresión muscular gradual con bolsillo lateral invisible para móvil y tiro extra alto sin costuras.",
        "cost": Decimal("65.00"),
        "base_price": Decimal("139.00"),
        "compare_at_price": Decimal("169.00"),
        "material": "80% Poliamida / 20% Elastano DryFit",
        "neck_type": "Cinturilla ancha antideslizante",
        "sleeve_length": "Largo tobillero deportivo",
        "tags": "Sport, Activewear, Compresion, Gym",
        "images": [
            "https://images.unsplash.com/photo-1506619216599-9d16d0903dfd?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["XS", "S", "M", "L"],
        "colors": ["Negro", "Azul Marino", "Gris Jaspe"],
        "sku_prefix": "LEG-PRO",
    },
    {
        "id": 12,
        "name": "Trench Coat Clásico Camel Doble Botonadura",
        "cat_name": "Abrigos",
        "description": "Gabardina impermeable clásica con solapas amplias, trabillas en hombros y cinturón con hebilla de carey. Una joya atemporal.",
        "cost": Decimal("220.00"),
        "base_price": Decimal("450.00"),
        "compare_at_price": Decimal("540.00"),
        "material": "Gabardina de Algodón con Capa Repelente al Agua",
        "neck_type": "Solapa ancha trench clásica",
        "sleeve_length": "Manga larga con trabilla ajustable",
        "tags": "Trench, Camel, Elegante, Impermeable",
        "images": [
            "https://images.unsplash.com/photo-1548883354-7622d03aca27?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=800&auto=format&fit=crop&q=80",
        ],
        "sizes": ["S", "M", "L"],
        "colors": ["Beige / Nude", "Negro"],
        "sku_prefix": "TRE-CAM",
    },
]


def run_migration():
    print("=====================================================================")
    print(" INICIANDO MIGRACIÓN MAESTRA DE DATOS PARA FASHIONSTORE (RETAIL PRO) ")
    print("=====================================================================")

    db = SessionLocal()
    try:
        # -------------------------------------------------------------
        # 1. SANEAMIENTO CONTABLE: CERRAR TURNOS DE CAJA HUÉRFANOS
        # -------------------------------------------------------------
        print("\n[1/7] Saneamiento de turnos de caja huérfanos...")
        open_shifts = db.query(CashShift).filter(CashShift.status == "ABIERTO").all()
        for s in open_shifts:
            s.status = "CERRADO"
            s.closed_at = datetime.now()
            s.closing_amount_declared = s.opening_amount
            s.closing_amount_system = s.opening_amount
            s.difference = Decimal("0.0")
            s.notes = f"Cierre automático por migración maestra. Turno #{s.id} balanceado."
            print(f"      -> Turno #{s.id} (Sucursal #{s.branch_id}) cerrado formalmente.")
        db.commit()

        # -------------------------------------------------------------
        # 2. SUCURSALES COMERCIALES PRESTIGIOSAS
        # -------------------------------------------------------------
        print("\n[2/7] Migrando e insertando Sucursales de Prestigio...")
        branches_map = {}
        for b_data in BRANCHES_DATA:
            b_id = b_data["id"]
            branch = db.query(Branch).filter(Branch.id == b_id).first()
            if not branch:
                branch = db.query(Branch).filter(Branch.name == b_data["name"]).first()
            
            if not branch:
                branch = Branch(
                    id=b_id,
                    name=b_data["name"],
                    code=b_data["code"],
                    city=b_data["city"],
                    zone=b_data["zone"],
                    address=b_data["address"],
                    reference=b_data["reference"],
                    phone=b_data["phone"],
                    whatsapp=b_data["whatsapp"],
                    opening_time=b_data["opening_time"],
                    closing_time=b_data["closing_time"],
                    days_open=b_data["days_open"],
                    has_fitting_room=b_data["has_fitting_room"],
                    pickup_enabled=b_data["pickup_enabled"],
                    image_url=b_data["image_url"],
                    latitude=b_data["latitude"],
                    longitude=b_data["longitude"],
                    is_active=True,
                    is_temporarily_closed=False
                )
                db.add(branch)
                db.flush()
                print(f"      [NUEVA] Sucursal #{branch.id}: {branch.name} ({branch.city})")
            else:
                branch.name = b_data["name"]
                branch.code = b_data["code"]
                branch.city = b_data["city"]
                branch.zone = b_data["zone"]
                branch.address = b_data["address"]
                branch.reference = b_data["reference"]
                branch.phone = b_data["phone"]
                branch.whatsapp = b_data["whatsapp"]
                branch.opening_time = b_data["opening_time"]
                branch.closing_time = b_data["closing_time"]
                branch.days_open = b_data["days_open"]
                branch.has_fitting_room = b_data["has_fitting_room"]
                branch.pickup_enabled = b_data["pickup_enabled"]
                branch.image_url = b_data["image_url"]
                branch.latitude = b_data["latitude"]
                branch.longitude = b_data["longitude"]
                branch.is_active = True
                branch.is_temporarily_closed = False
                print(f"      [ACTUALIZADA] Sucursal #{branch.id}: {branch.name} ({branch.city})")
            
            branches_map[branch.id] = branch
        
        db.commit()

        # -------------------------------------------------------------
        # 3. PROVEEDORES FORMALES TEXTILES
        # -------------------------------------------------------------
        print("\n[3/7] Migrando Proveedores Textiles con NIT...")
        suppliers_map = {}
        for s_data in SUPPLIERS_DATA:
            sup = db.query(Supplier).filter(Supplier.id == s_data["id"]).first()
            if not sup:
                sup = db.query(Supplier).filter(Supplier.nit == s_data["nit"]).first()
            
            if not sup:
                sup = Supplier(
                    id=s_data["id"],
                    nit=s_data["nit"],
                    name=s_data["name"],
                    category=s_data["category"],
                    contact_name=s_data["contact_name"],
                    email=s_data["email"],
                    phone=s_data["phone"],
                    address=s_data["address"],
                    is_active=True
                )
                db.add(sup)
                db.flush()
                print(f"      [NUEVO] Proveedor #{sup.id}: {sup.name} (NIT: {sup.nit})")
            else:
                sup.nit = s_data["nit"]
                sup.name = s_data["name"]
                sup.category = s_data["category"]
                sup.contact_name = s_data["contact_name"]
                sup.email = s_data["email"]
                sup.phone = s_data["phone"]
                sup.address = s_data["address"]
                sup.is_active = True
                print(f"      [ACTUALIZADO] Proveedor #{sup.id}: {sup.name} (NIT: {sup.nit})")
            
            suppliers_map[sup.id] = sup
        
        db.commit()

        # -------------------------------------------------------------
        # 4. PERSONAL POR SUCURSAL (USERS, ROLES & BRANCH_EMPLOYEES)
        # -------------------------------------------------------------
        print("\n[4/7] Creando y asignando Personal por Sucursal (Encargados y Cajeros)...")
        roles = {r.name: r for r in db.query(Role).all()}
        
        # Asegurar asignación del usuario personal a Equipetrol
        esther_user = db.query(User).filter(User.email == "marilynesthercondori2005@gmail.com").first()
        if esther_user:
            db.execute(text("DELETE FROM branch_employees WHERE user_id = :uid"), {"uid": esther_user.id})
            db.execute(text("INSERT INTO branch_employees (branch_id, user_id) VALUES (1, :uid)"), {"uid": esther_user.id})
            print("      -> Usuario personal marilynesthercondori2005@gmail.com asignado como ENCARGADA a Sucursal Equipetrol.")

        for staff in STAFF_DATA:
            u = db.query(User).filter(User.email == staff["email"]).first()
            if not u:
                u = User(
                    email=staff["email"],
                    password_hash=get_password_hash(PASSWORD_DEFAULT),
                    first_name=staff["first_name"],
                    last_name=staff["last_name"],
                    phone=staff["phone"],
                    is_active=True
                )
                db.add(u)
                db.flush()
                target_role = roles.get(staff["role"])
                if target_role:
                    u.roles.append(target_role)
                print(f"      [CREADO] Usuario {u.email} ({staff['role']})")
            else:
                u.first_name = staff["first_name"]
                u.last_name = staff["last_name"]
                u.phone = staff["phone"]
                u.is_active = True
                target_role = roles.get(staff["role"])
                if target_role and target_role not in u.roles:
                    u.roles.append(target_role)
                print(f"      [EXISTE] Usuario {u.email} ({staff['role']})")

            # Asignar en branch_employees
            db.execute(text("DELETE FROM branch_employees WHERE user_id = :uid"), {"uid": u.id})
            db.execute(text("INSERT INTO branch_employees (branch_id, user_id) VALUES (:bid, :uid)"),
                       {"bid": staff["branch_id"], "uid": u.id})
            print(f"         -> Vinculado a Sucursal #{staff['branch_id']}")
        
        db.commit()

        # -------------------------------------------------------------
        # 5. CATÁLOGO DE MODA: PRODUCTOS, VARIANTES Y FOTOS HD
        # -------------------------------------------------------------
        print("\n[5/7] Configurando Catálogo de Moda Femenina y Prendas Reales...")
        colors_map = {c.name: c for c in db.query(Color).all()}
        sizes_map = {s.name: s for s in db.query(Size).all()}
        categories_map = {c.name: c for c in db.query(Category).all()}

        current_season = db.query(Season).filter(Season.name == "Primavera / Verano 2026").first()
        if not current_season:
            current_season = Season(name="Primavera / Verano 2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
            db.add(current_season)
            db.flush()

        products_map = {}
        all_variants = []

        for p_info in CATALOG_PRODUCTS:
            cat = categories_map.get(p_info["cat_name"])
            if not cat:
                cat = db.query(Category).filter(Category.parent_id != None).first()

            prod = db.query(Product).filter(Product.id == p_info["id"]).first()
            if not prod:
                prod = db.query(Product).filter(Product.name == p_info["name"]).first()

            if not prod:
                prod = Product(
                    id=p_info["id"],
                    name=p_info["name"],
                    description=p_info["description"],
                    base_price=p_info["base_price"],
                    compare_at_price=p_info["compare_at_price"],
                    category_id=cat.id if cat else 1,
                    season_id=current_season.id,
                    material=p_info["material"],
                    neck_type=p_info["neck_type"],
                    sleeve_length=p_info["sleeve_length"],
                    tags=p_info["tags"],
                    is_active=True
                )
                db.add(prod)
                db.flush()
                print(f"      [NUEVA PRENDA] #{prod.id}: {prod.name} - Bs. {prod.base_price}")
            else:
                prod.name = p_info["name"]
                prod.description = p_info["description"]
                prod.base_price = p_info["base_price"]
                prod.compare_at_price = p_info["compare_at_price"]
                if cat:
                    prod.category_id = cat.id
                prod.season_id = current_season.id
                prod.material = p_info["material"]
                prod.neck_type = p_info["neck_type"]
                prod.sleeve_length = p_info["sleeve_length"]
                prod.tags = p_info["tags"]
                prod.is_active = True
                print(f"      [ACTUALIZADA] #{prod.id}: {prod.name} - Bs. {prod.base_price}")

            products_map[prod.id] = prod

            # Sincronizar Fotos HD
            db.query(ProductImage).filter(ProductImage.product_id == prod.id).delete()
            for idx, img_url in enumerate(p_info["images"]):
                pi = ProductImage(
                    product_id=prod.id,
                    image_url=img_url,
                    is_primary=(idx == 0)
                )
                db.add(pi)

            # Generar / Sincronizar Variantes (Color x Talla)
            for c_name in p_info["colors"]:
                col = colors_map.get(c_name)
                if not col:
                    col = list(colors_map.values())[0]

                for s_name in p_info["sizes"]:
                    siz = sizes_map.get(s_name)
                    if not siz:
                        siz = list(sizes_map.values())[0]

                    sku = f"{p_info['sku_prefix']}-{col.name[:3].upper()}-{siz.name}".replace(" ", "")
                    var = db.query(ProductVariant).filter(
                        ProductVariant.product_id == prod.id,
                        ProductVariant.color_id == col.id,
                        ProductVariant.size_id == siz.id
                    ).first()

                    if not var:
                        existing_sku = db.query(ProductVariant).filter(ProductVariant.sku == sku).first()
                        if existing_sku:
                            sku = f"{sku}-{prod.id}"
                        var = ProductVariant(
                            product_id=prod.id,
                            color_id=col.id,
                            size_id=siz.id,
                            sku=sku,
                            price_override=None,
                            is_active=True
                        )
                        db.add(var)
                        db.flush()
                    all_variants.append((var, p_info["cost"]))

        db.commit()

        # -------------------------------------------------------------
        # 6. INVENTARIO MULTISUCURSAL Y STOCK BALANCEADO
        # -------------------------------------------------------------
        print("\n[6/7] Generando Inventario y Stock por Sucursal...")
        all_branches = db.query(Branch).all()
        active_variants = db.query(ProductVariant).filter(ProductVariant.is_active == True).all()
        cost_by_product = {p["id"]: p["cost"] for p in CATALOG_PRODUCTS}

        inventory_count = 0
        for b in all_branches:
            for v in active_variants:
                p_cost = cost_by_product.get(v.product_id, Decimal("65.00"))
                inv = db.query(Inventory).filter(
                    Inventory.branch_id == b.id,
                    Inventory.variant_id == v.id
                ).first()

                if b.id == 1:
                    stock_qty = 25
                elif b.id == 2:
                    stock_qty = 30
                elif b.id == 3:
                    stock_qty = 20
                else:
                    stock_qty = 15

                if not inv:
                    inv = Inventory(
                        branch_id=b.id,
                        variant_id=v.id,
                        stock_actual=stock_qty,
                        avg_cost=p_cost,
                        stock_minimo=5,
                        stock_maximo=60
                    )
                    db.add(inv)
                else:
                    inv.stock_actual = stock_qty
                    inv.avg_cost = p_cost
                    inv.stock_minimo = 5
                    inv.stock_maximo = 60
                
                inventory_count += 1

        db.commit()
        print(f"      -> {inventory_count} registros de inventario sincronizados en {len(all_branches)} sucursales.")

        # -------------------------------------------------------------
        # 7. INGRESO DE MERCADERÍA HISTÓRICO (COMPRAS Y KARDEX)
        # -------------------------------------------------------------
        print("\n[7/7] Registrando Compras e Ingreso de Mercadería en Kardex Ledger...")
        suppliers = db.query(Supplier).all()
        
        for b in all_branches:
            sup = suppliers[(b.id - 1) % len(suppliers)]
            inv_num = f"FAC-2026-00{b.id}84"
            
            existing_po = db.query(PurchaseOrder).filter(
                PurchaseOrder.branch_id == b.id,
                PurchaseOrder.invoice_number == inv_num
            ).first()

            if not existing_po:
                po = PurchaseOrder(
                    supplier_id=sup.id,
                    branch_id=b.id,
                    status="COMPLETADO",
                    invoice_number=inv_num,
                    shipping_cost=Decimal("50.00"),
                    notes=f"Lote inicial de apertura y abastecimiento temporada - {b.name}",
                    total_amount=Decimal("0.0"),
                    created_at=datetime.now() - timedelta(days=5)
                )
                db.add(po)
                db.flush()

                total_po = Decimal("50.00")
                sample_vars = [v for v in active_variants if v.id % 2 == 0][:5]
                for sv in sample_vars:
                    v_cost = cost_by_product.get(sv.product_id, Decimal("70.00"))
                    p_qty = 20
                    subtotal = v_cost * p_qty
                    total_po += subtotal

                    pd = PurchaseDetail(
                        purchase_order_id=po.id,
                        variant_id=sv.id,
                        quantity=p_qty,
                        unit_cost=v_cost,
                        previous_avg_cost=Decimal("0.0"),
                        new_avg_cost=v_cost
                    )
                    db.add(pd)

                    ledger = InventoryLedger(
                        branch_id=b.id,
                        variant_id=sv.id,
                        quantity=p_qty,
                        movement_type="INGRESO",
                        unit_cost=v_cost,
                        reference_id=f"OC-{po.id}"
                    )
                    db.add(ledger)

                po.total_amount = total_po
                print(f"      -> Orden de Compra #{po.id} creada para {b.name} ({sup.name}) por Bs. {po.total_amount:,.2f}")

        db.commit()

        print("\n=====================================================================")
        print(" MIGRACIÓN Y ENRIQUECIMIENTO MAESTRO COMPLETADO CON ÉXITO ROTUNDO! ")
        print("=====================================================================")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR CRÍTICO DURANTE MIGRACIÓN]: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
