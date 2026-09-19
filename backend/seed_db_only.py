"""Seed solo BD - Las imagenes ya estan procesadas."""
import sys, os
from decimal import Decimal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.session import SessionLocal
from app.packages.catalogo_y_tiendas.models import (
    Category, Product, ProductVariant, ProductImage, Color, Size
)

db = SessionLocal()
try:
    # Verificar si ya hay productos
    count = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
    if count > 0:
        print(f"Ya hay {count} productos. Saliendo.")
        sys.exit(0)

    # Categorias
    categories_needed = {
        "Blusas": "Blusas y tops femeninos elegantes",
        "Tops / Crop Tops": "Tops, crop tops y prendas superiores ligeras",
        "Blazers": "Blazers y chaquetas sastre femeninas",
    }
    cat_map = {}
    for cat_name, cat_desc in categories_needed.items():
        existing = db.query(Category).filter(Category.name == cat_name).first()
        if existing:
            cat_map[cat_name] = existing
        else:
            new_cat = Category(name=cat_name, description=cat_desc)
            db.add(new_cat)
            db.flush()
            cat_map[cat_name] = new_cat
        print(f"  Cat '{cat_name}' id={cat_map[cat_name].id}")

    # Colores
    colors_needed = {
        "Blanco": "#FFFFFF",
        "Beige": "#D4C5A9",
        "Camel": "#A67B5B",
        "Chocolate": "#3E2723",
    }
    color_map = {}
    for col_name, col_hex in colors_needed.items():
        existing = db.query(Color).filter(Color.name == col_name).first()
        if existing:
            color_map[col_name] = existing
        else:
            new_col = Color(name=col_name, hex_code=col_hex)
            db.add(new_col)
            db.flush()
            color_map[col_name] = new_col
        print(f"  Color '{col_name}' id={color_map[col_name].id}")

    # Tallas
    sizes_needed = ["XS", "S", "M", "L", "XL"]
    size_map = {}
    for sz_name in sizes_needed:
        existing = db.query(Size).filter(Size.name == sz_name).first()
        if existing:
            size_map[sz_name] = existing
        else:
            new_sz = Size(name=sz_name, category_type="TOPS")
            db.add(new_sz)
            db.flush()
            size_map[sz_name] = new_sz

    # 4 prendas
    PRENDAS = [
        {
            "name": "Blusa Peplum Plisada Escote V con Botones de Carey",
            "description": "Blusa femenina plisada con corte peplum y escote en V pronunciado. Botones de carey centrales. Manga corta cap sleeve. Lino texturizado ligero.",
            "base_price": Decimal("189.00"),
            "compare_at_price": Decimal("249.00"),
            "category": "Blusas",
            "color": "Blanco",
            "material": "Lino texturizado",
            "neck_type": "Escote en V pronunciado",
            "sleeve_length": "Manga corta cap sleeve",
            "tags": "peplum,plisada,botones carey,escote V,lino,blanco,elegante,peplum_v_neck",
            "image_file": "blusa_peplum_blanca",
        },
        {
            "name": "Top Sastre Off-Shoulder Cruzado Estilo Haute Couture",
            "description": "Top sastre haute couture con escote barco off-shoulder. Doble hilera de botones forrados. Corte peplum. Crepe grueso acabado mate premium.",
            "base_price": Decimal("320.00"),
            "compare_at_price": Decimal("450.00"),
            "category": "Tops / Crop Tops",
            "color": "Beige",
            "material": "Crepe grueso acabado mate",
            "neck_type": "Escote barco off-shoulder",
            "sleeve_length": "Manga corta estructurada",
            "tags": "off-shoulder,cruzado,haute couture,beige,sastre,botones,peplum,off_shoulder_double_breasted",
            "image_file": "top_dior_beige",
        },
        {
            "name": "Blusa Estructurada Cuello Redondo con Botones Dorados",
            "description": "Blusa entallada cuello redondo caja cerrado. Botones dorados de relieve. Manga corta sobre el codo. Lino estructurado acabado gamuza. Color camel.",
            "base_price": Decimal("210.00"),
            "compare_at_price": Decimal("285.00"),
            "category": "Blusas",
            "color": "Camel",
            "material": "Lino estructurado acabado gamuza",
            "neck_type": "Cuello redondo caja cerrado",
            "sleeve_length": "Manga corta sobre el codo",
            "tags": "estructurada,cuello redondo,botones dorados,camel,bolsillos,entallada,crew_neck_structured",
            "image_file": "blusa_camel_botones",
        },
        {
            "name": "Blazer Peplum Manga Corta con Solapa Clasica y Botones Dorados",
            "description": "Blazer femenino manga corta con solapa de muesca clasica y corte peplum acampanado. Tres botones dorados. Pano mezcla aterciopelado. Chocolate oscuro.",
            "base_price": Decimal("350.00"),
            "compare_at_price": Decimal("480.00"),
            "category": "Blazers",
            "color": "Chocolate",
            "material": "Pano mezcla acabado aterciopelado",
            "neck_type": "Solapa de muesca clasica en V",
            "sleeve_length": "Manga corta sobre el codo",
            "tags": "blazer,peplum,manga corta,solapa,botones dorados,chocolate,sastre,formal,blazer_notch_lapel_peplum",
            "image_file": "blazer_chocolate",
        },
    ]

    for p in PRENDAS:
        cat = cat_map[p["category"]]
        product = Product(
            name=p["name"],
            description=p["description"],
            base_price=p["base_price"],
            compare_at_price=p["compare_at_price"],
            category_id=cat.id,
            is_active=True,
            material=p["material"],
            neck_type=p["neck_type"],
            sleeve_length=p["sleeve_length"],
            tags=p["tags"],
        )
        db.add(product)
        db.flush()
        print(f"  Prenda '{product.name}' id={product.id}")

        color = color_map[p["color"]]
        pi = ProductImage(
            product_id=product.id,
            color_id=color.id,
            image_url=f"/uploads/products/{p['image_file']}.png",
            is_primary=True,
        )
        db.add(pi)

        for sz_name in sizes_needed:
            sz = size_map[sz_name]
            sku = f"FS-{p['image_file'][:10].upper()}-{p['color'][:3].upper()}-{sz_name}"
            variant = ProductVariant(
                product_id=product.id,
                color_id=color.id,
                size_id=sz.id,
                sku=sku,
                is_active=True,
            )
            db.add(variant)
        db.flush()
        print(f"    -> {len(sizes_needed)} variantes creadas")

    db.commit()
    print("\nOK - 4 prendas insertadas correctamente.")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
