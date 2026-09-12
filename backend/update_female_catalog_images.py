"""
Script para actualizar el catálogo hacia Moda Femenina de Alta Gama y Elegancia
==============================================================================
Asegura que:
1. Todas las fotografías sean 100% de moda femenina, elegantes, sofisticadas y de alta resolución.
2. Ninguna prenda parezca masculina; todas tienen silueta, corte y estilismo de mujer.
3. Nombres y descripciones comerciales de boutique femenina de lujo (estilo Zara Woman / Massimo Dutti).
4. Las categorías principales cuenten con imágenes de portada femenina elegantes.
"""

import sys
import os
from decimal import Decimal
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.packages.catalogo_y_tiendas.models import Product, ProductImage, Category

# Categorías con imágenes representativas femeninas elegantes
CATEGORY_AVATARS = {
    "Ropa Superior": "https://images.unsplash.com/photo-1551803091-e20673f15770?w=500&auto=format&fit=crop&q=80",
    "Camisas": "https://images.unsplash.com/photo-1598554747436-c9293d6a588f?w=500&auto=format&fit=crop&q=80",
    "Blusas": "https://images.unsplash.com/photo-1564257631407-4deb129f044b?w=500&auto=format&fit=crop&q=80",
    "Tops / Crop Tops": "https://images.unsplash.com/photo-1508427953056-b00b8d78ebf5?w=500&auto=format&fit=crop&q=80",
    "Suéteres y Tejidos": "https://images.unsplash.com/photo-1576871337622-98d48d1cf531?w=500&auto=format&fit=crop&q=80",
    "Ropa Inferior": "https://images.unsplash.com/photo-1509551388413-e18d0ac5d495?w=500&auto=format&fit=crop&q=80",
    "Jeans / Mezclilla": "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=500&auto=format&fit=crop&q=80",
    "Pantalones": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500&auto=format&fit=crop&q=80",
    "Faldas": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=80",
    "Prendas de Una Pieza": "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=500&auto=format&fit=crop&q=80",
    "Vestidos": "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=500&auto=format&fit=crop&q=80",
    "Enterizos / Monos": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=500&auto=format&fit=crop&q=80",
    "Ropa Exterior": "https://images.unsplash.com/photo-1584273143981-41c073dfe8f8?w=500&auto=format&fit=crop&q=80",
    "Chaquetas / Chamarras": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&auto=format&fit=crop&q=80",
    "Abrigos": "https://images.unsplash.com/photo-1548883354-7622d03aca27?w=500&auto=format&fit=crop&q=80",
    "Blazers": "https://images.unsplash.com/photo-1584273143981-41c073dfe8f8?w=500&auto=format&fit=crop&q=80",
    "Ropa Deportiva": "https://images.unsplash.com/photo-1506619216599-9d16d0903dfd?w=500&auto=format&fit=crop&q=80",
    "Leggings deportivos": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=500&auto=format&fit=crop&q=80",
}

FEMALE_ELEGANT_CATALOG = [
    {
        "id": 1,
        "name": "Camisa de Lino Femenina Relaxed Chic",
        "description": "Camisa holgada femenina en lino natural 100% puro. Diseñada con cuello camisero suave, hombros caídos y botones en contraste, aportando un estilo fresco, distinguido y femenino.",
        "base_price": Decimal("149.00"),
        "compare_at_price": Decimal("189.00"),
        "material": "100% Lino Natural Premium",
        "neck_type": "Cuello camisero fluido femenino",
        "sleeve_length": "Manga larga remangable con trabilla",
        "tags": "Lino, Relaxed Chic, Mujer, Elegante",
        "images": [
            "https://images.unsplash.com/photo-1598554747436-c9293d6a588f?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1554412933-514a83d2f3c8?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 2,
        "name": "Blusa Satinada Fluida Escote V Elegance",
        "description": "Blusa femenina en satén sedoso con suave caída sobre el cuerpo, escote sutil en V y delicados puños elásticos. Una prenda esencial para atuendos de oficina refinados o cenas elegantes.",
        "base_price": Decimal("129.00"),
        "compare_at_price": Decimal("159.00"),
        "material": "Satén de Seda y Viscosa",
        "neck_type": "Escote en V femenino sutil",
        "sleeve_length": "Manga 3/4 con caída fluida",
        "tags": "Satén, Seda, Oficina Chic, Noche",
        "images": [
            "https://images.unsplash.com/photo-1551803091-e20673f15770?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 3,
        "name": "Chaqueta Biker Cuero Vegano Silueta Entallada",
        "description": "Chaqueta biker entallada para mujer, confeccionada en piel sintética ultrasuave de grano fino con solapas con broches y herrajes metálicos pulidos. Corte moderno que realza la cintura.",
        "base_price": Decimal("369.00"),
        "compare_at_price": Decimal("449.00"),
        "material": "Piel Sintética PU Suave / Forro Seda",
        "neck_type": "Solapa cruzada biker femenina",
        "sleeve_length": "Manga larga entallada con cremallera",
        "tags": "Biker, Cuero Vegano, Estilo Mujer, Vanguardia",
        "images": [
            "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1520975661595-6453be3f7070?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 4,
        "name": "Top Bustier Femenino de Satén Escote Corazón",
        "description": "Top corto estructurado estilo corsé femenino confeccionado en satén brillante, con copas moldeadas y tirantes finos. La prenda perfecta para elevar un blazer o una falda lápiz de fiesta.",
        "base_price": Decimal("89.00"),
        "compare_at_price": Decimal("119.00"),
        "material": "Satén con Ballenas Suaves y Elastano",
        "neck_type": "Escote corazón estructurado",
        "sleeve_length": "Tirantes finos ajustables",
        "tags": "Bustier, Corset, Fiesta, Satén",
        "images": [
            "https://images.unsplash.com/photo-1508427953056-b00b8d78ebf5?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 5,
        "name": "Pantalón Sastre Femenino Wide Leg Tiro Alto",
        "description": "Pantalón de vestir sastre para mujer con pinzas frontales profundas, tiro muy alto y pernera recta ancha que alarga visualmente las piernas. Confeccionado en tejido crepé con caída impecable.",
        "base_price": Decimal("199.00"),
        "compare_at_price": Decimal("249.00"),
        "material": "Crepé de Sastrería con Caída Pesada",
        "neck_type": "Pretina alta estructurada con trabillas",
        "sleeve_length": "Largo completo al suelo",
        "tags": "Sastrería, Wide Leg, Mujer Ejecutiva, Elegancia",
        "images": [
            "https://images.unsplash.com/photo-1509551388413-e18d0ac5d495?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 6,
        "name": "Vestido Midi Satén de Seda con Escote Drapeado",
        "description": "Vestido midi confeccionado en satén de seda pura con escote drapeado fluido y tirantes finos ajustables. Silueta entallada al bies que realza la elegancia femenina en galas y ocasiones nocturnas.",
        "base_price": Decimal("249.00"),
        "compare_at_price": Decimal("310.00"),
        "material": "100% Satén de Seda al Bies",
        "neck_type": "Escote drapeado femenino fluido",
        "sleeve_length": "Tirantes finos ajustables",
        "tags": "Seda, Gala, Vestido de Fiesta, Sofisticado",
        "images": [
            "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1566174053879-31528523f8ae?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 7,
        "name": "Blazer Sastrería Femenino Ivory Gold Buttons",
        "description": "Elegante blazer para mujer de corte sastre estructurado, solapas refinadas y botones metálicos dorados grabados. Confeccionado en crepé de alta gama para proyectar poder y distinción ejecutiva.",
        "base_price": Decimal("349.00"),
        "compare_at_price": Decimal("420.00"),
        "material": "Crepé Sastre con Forro Seda Marfil",
        "neck_type": "Solapa en punta ejecutiva",
        "sleeve_length": "Manga sastre con 4 botones dorados",
        "tags": "Blazer, Ivory, Power Dressing, Mujer Líder",
        "images": [
            "https://images.unsplash.com/photo-1584273143981-41c073dfe8f8?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 8,
        "name": "Suéter Femenino Cuello Vuelto Cachemira Touch",
        "description": "Prenda de punto extrafino con tacto de cachemira, cuello vuelto acanalado y corte regular femenino. Combina calidez absoluta con una silueta limpia, delicada y distinguida.",
        "base_price": Decimal("189.00"),
        "compare_at_price": Decimal("230.00"),
        "material": "Lana Merino Fina y Cachemira Soft",
        "neck_type": "Cuello vuelto tortuga refinado",
        "sleeve_length": "Manga larga con puño acanalado",
        "tags": "Cachemira, Punto Fino, Invierno Elegante, Mujer",
        "images": [
            "https://images.unsplash.com/photo-1576871337622-98d48d1cf531?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 9,
        "name": "Falda Midi Plisada de Satén con Cintura Elástica",
        "description": "Falda midi de corte evasé con microplisado permanente y reflejos satinados dorados y terracota. Se mueve con gracia en cada paso, perfecta para combinar con blusas de seda o tacones finos.",
        "base_price": Decimal("159.00"),
        "compare_at_price": Decimal("195.00"),
        "material": "Satén de Seda Plisado Permanente",
        "neck_type": "Pretina alta elástica oculta",
        "sleeve_length": "Largo midi bajo la rodilla",
        "tags": "Falda Midi, Plisado, Satén, Femenina",
        "images": [
            "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 10,
        "name": "Enterizo Palazzo Femenino de Gala con Cinturón",
        "description": "Enterizo largo de una pieza con pantalón palazzo de bota ancha, corpiño cruzado y lazo a la cintura para ceñir la silueta. Una alternativa ultramoderna y elegante al clásico vestido de gala.",
        "base_price": Decimal("289.00"),
        "compare_at_price": Decimal("350.00"),
        "material": "Crepé Georgette con Forro Interior",
        "neck_type": "Escote cruzado femenino con fajín",
        "sleeve_length": "Sin mangas con hombro definido",
        "tags": "Jumpsuit, Palazzo, Noche, Gala Mujer",
        "images": [
            "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1502716119720-b23a93e5fe1b?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 11,
        "name": "Leggings Deportivos Sculpting Mujer Tiro Alto",
        "description": "Leggings deportivos para mujer con efecto moldeador de cintura alta, tejido transpirable Four-Way Stretch sin costuras frontales y acabado mate aterciopelado de máxima sujeción.",
        "base_price": Decimal("139.00"),
        "compare_at_price": Decimal("169.00"),
        "material": "Poliamida Compresiva y Lycra DryFit",
        "neck_type": "Cintura alta compresiva antideslizante",
        "sleeve_length": "Largo tobillero deportivo",
        "tags": "Activewear, Sculpting, Gym Chic, Mujer",
        "images": [
            "https://images.unsplash.com/photo-1506619216599-9d16d0903dfd?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=800&auto=format&fit=crop&q=80",
        ]
    },
    {
        "id": 12,
        "name": "Trench Coat Femenino Gabardina Camel con Cinturón",
        "description": "Icónica gabardina trench para mujer en tono camel clásico. Confeccionada con tejido impermeable de tacto suave, forro satinado y cinturón con hebilla para entallar la silueta con sofisticación parisina.",
        "base_price": Decimal("469.00"),
        "compare_at_price": Decimal("560.00"),
        "material": "Gabardina de Algodón Hidrófugo y Forro Raso",
        "neck_type": "Solapa ancha trench clásica",
        "sleeve_length": "Manga larga con trabilla ajustable en puño",
        "tags": "Trench Coat, Camel, Elegancia Parisina, Mujer",
        "images": [
            "https://images.unsplash.com/photo-1548883354-7622d03aca27?w=800&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&auto=format&fit=crop&q=80",
        ]
    },
]


def update_female_catalog():
    print("==================================================================")
    print(" ACTUALIZANDO CATÁLOGO HACIA MODA FEMENINA ELEGANTE Y DE ALTA GAMA ")
    print("==================================================================")

    db: Session = SessionLocal()
    try:
        # 1. Actualizar imágenes de Categorías
        print("\n[1/2] Actualizando portadas de Categorías con estética femenina...")
        for cat_name, img_url in CATEGORY_AVATARS.items():
            cat = db.query(Category).filter(Category.name == cat_name).first()
            if cat:
                cat.image_url = img_url
                print(f"      -> Categoría '{cat.name}' vinculada a avatar HD.")
        db.commit()

        # 2. Actualizar Productos, Fotos y Descripciones
        print("\n[2/2] Actualizando prendas con estilismo 100% de mujer elegante...")
        for item in FEMALE_ELEGANT_CATALOG:
            prod = db.query(Product).filter(Product.id == item["id"]).first()
            if not prod:
                continue

            prod.name = item["name"]
            prod.description = item["description"]
            prod.base_price = item["base_price"]
            prod.compare_at_price = item["compare_at_price"]
            prod.material = item["material"]
            prod.neck_type = item["neck_type"]
            prod.sleeve_length = item["sleeve_length"]
            prod.tags = item["tags"]

            # Reemplazar imágenes por fotos de modelos mujeres elegantes
            db.query(ProductImage).filter(ProductImage.product_id == prod.id).delete()
            for idx, img_url in enumerate(item["images"]):
                pi = ProductImage(
                    product_id=prod.id,
                    image_url=img_url,
                    is_primary=(idx == 0)
                )
                db.add(pi)

            print(f"      [PRENDA FEMENINA] #{prod.id}: {prod.name} (Bs. {prod.base_price})")

        db.commit()
        print("\n==================================================================")
        print(" CATÁLOGO FEMENINO ELEGANTE ACTUALIZADO CON ÉXITO!               ")
        print("==================================================================")

    except Exception as e:
        db.rollback()
        print("[ERROR]:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_female_catalog()
