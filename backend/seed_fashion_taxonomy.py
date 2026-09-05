"""
Script para inicializar la Taxonomía Oficial de Moda Femenina, Curvas de Tallas y Paleta de Colores.
"""
from sqlalchemy import text
from app.db.session import engine, SessionLocal
from app.packages.catalogo_y_tiendas.models import Category, Size, Color, Product, ProductVariant, ProductImage

# Asegurar columnas nuevas
UPGRADES = [
    "ALTER TABLE categories ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL",
    "ALTER TABLE sizes ADD COLUMN IF NOT EXISTS category_type VARCHAR(30)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS material VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS neck_type VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS sleeve_length VARCHAR(100)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS tags VARCHAR(255)",
]

TAXONOMY = [
    {
        "name": "Ropa Superior",
        "description": "Prendas para la parte superior del cuerpo: camisas, blusas, tops y tejidos.",
        "subs": [
            ("Camisas", "Con botones y cuello estructurado"),
            ("Blusas", "Telas fluidas, cortes sueltos y elegantes"),
            ("Camisetas / T-Shirts", "Algodón, cuello redondo o en V para uso diario"),
            ("Tops / Crop Tops", "Cortos, ajustados, tirantes o strapless"),
            ("Suéteres y Tejidos", "Prendas de punto fino, cárdigans y suéteres"),
        ]
    },
    {
        "name": "Ropa Inferior",
        "description": "Prendas para la parte inferior: jeans, pantalones, faldas y shorts.",
        "subs": [
            ("Jeans / Mezclilla", "Denim tiro alto, skinny, wide leg, mom jeans"),
            ("Pantalones", "De tela, vestir, sastrería y casuales"),
            ("Faldas", "Faldas cortas, midi, lápiz y largas"),
            ("Shorts / Bermudas", "Denim, lino y pantalones cortos"),
        ]
    },
    {
        "name": "Prendas de Una Pieza",
        "description": "Vestidos y monos enterizos de una sola pieza.",
        "subs": [
            ("Vestidos", "De día, de noche/fiesta, cóctel y casuales"),
            ("Enterizos / Monos", "Jumpsuits elegantes y rompers frescos"),
        ]
    },
    {
        "name": "Ropa Exterior",
        "description": "Chaquetas, abrigos y blazers de abrigo y sastrería.",
        "subs": [
            ("Chaquetas / Chamarras", "Cuero, mezclilla, biker y bombers"),
            ("Abrigos", "Trench coats, paño y frío intenso"),
            ("Blazers", "Sastrería ejecutiva y blazers oversize"),
        ]
    },
    {
        "name": "Ropa Íntima y Descanso",
        "description": "Lencería femenina y ropa para dormir.",
        "subs": [
            ("Lencería", "Brasieres, calzones y conjuntos íntimos"),
            ("Ropa de dormir / Pijamas", "Pijamas de satén, algodón y batas"),
        ]
    },
    {
        "name": "Ropa Deportiva",
        "description": "Activewear y prendas de alto rendimiento.",
        "subs": [
            ("Leggings deportivos", "Mallas de compresión y ciclistas"),
            ("Tops deportivos", "Sports bras y camisetas transpirables"),
        ]
    },
    {
        "name": "Ropa de Baño",
        "description": "Trajes de baño y complementos de playa.",
        "subs": [
            ("Bikinis", "Dos piezas, tops y panties de playa"),
            ("Trajes de baño enteros", "Bañadores de una sola pieza y trikinis"),
        ]
    },
]

SIZES = [
    # TOPS / DRESSES / GENERAL (Letras)
    ("XS", "TOPS"),
    ("S", "TOPS"),
    ("M", "TOPS"),
    ("L", "TOPS"),
    ("XL", "TOPS"),
    ("XXL", "TOPS"),
    # BOTTOMS (Pantalones numéricos EU)
    ("34", "BOTTOMS"),
    ("36", "BOTTOMS"),
    ("38", "BOTTOMS"),
    ("40", "BOTTOMS"),
    ("42", "BOTTOMS"),
    ("44", "BOTTOMS"),
    # BOTTOMS_US (Jeans americanos)
    ("26", "BOTTOMS_US"),
    ("28", "BOTTOMS_US"),
    ("30", "BOTTOMS_US"),
    ("32", "BOTTOMS_US"),
    ("34-US", "BOTTOMS_US"),
]

COLORS = [
    ("Blanco", "#FFFFFF"),
    ("Negro", "#1A1A1A"),
    ("Beige / Nude", "#E8D8C8"),
    ("Terracota", "#C66F5C"),
    ("Azul Marino", "#1A2B4C"),
    ("Rojo Vino", "#800020"),
    ("Rosa Pastel", "#F4C2C2"),
    ("Verde Oliva", "#556B2F"),
    ("Mostaza", "#D4AF37"),
    ("Lavanda", "#E6E6FA"),
    ("Gris Jaspe", "#8E8E93"),
    ("Café Chocolate", "#4A2E18"),
]

def run():
    print("[1/5] Aplicando migraciones DDL...")
    with engine.begin() as conn:
        for u in UPGRADES:
            conn.execute(text(u))
    print("      DDL aplicado.")

    db = SessionLocal()
    try:
        # [2/5] Crear o verificar colores oficiales
        print("[2/5] Creando Paleta de Colores de Moda...")
        color_map = {}
        for name, hex_code in COLORS:
            c = db.query(Color).filter(Color.name == name).first()
            if not c:
                # Si existe por hex, actualizarlo
                c = db.query(Color).filter(Color.hex_code == hex_code).first()
                if c:
                    c.name = name
                else:
                    c = Color(name=name, hex_code=hex_code)
                    db.add(c)
                    db.flush()
            color_map[name] = c
        db.commit()
        default_color = color_map["Blanco"]

        # [3/5] Crear o verificar Curva de Tallas
        print("[3/5] Creando Curva de Tallas Inteligente...")
        size_map = {}
        for name, ctype in SIZES:
            s = db.query(Size).filter(Size.name == name).first()
            if not s:
                s = Size(name=name, category_type=ctype)
                db.add(s)
                db.flush()
            else:
                s.category_type = ctype
            size_map[name] = s
        db.commit()
        default_size = size_map["M"]

        # [4/5] Crear Categorías y Subcategorías
        print("[4/5] Creando Taxonomía Jerárquica...")
        subcat_map = {}
        for parent_data in TAXONOMY:
            p_name = parent_data["name"]
            p = db.query(Category).filter(Category.name == p_name).first()
            if not p:
                p = Category(name=p_name, description=parent_data["description"], parent_id=None)
                db.add(p)
                db.flush()
            else:
                p.description = parent_data["description"]

            for sub_name, sub_desc in parent_data["subs"]:
                sub = db.query(Category).filter(Category.name == sub_name).first()
                if not sub:
                    sub = Category(name=sub_name, description=sub_desc, parent_id=p.id)
                    db.add(sub)
                    db.flush()
                else:
                    sub.parent_id = p.id
                    sub.description = sub_desc
                subcat_map[sub_name] = sub
        db.commit()

        # [5/5] Reasignar productos existentes a las nuevas categorías y limpiar datos de test
        print("[5/5] Reasignando prendas existentes y limpiando datos de prueba...")
        camisas_cat = subcat_map["Camisas"]
        vestidos_cat = subcat_map["Vestidos"]
        blusas_cat = subcat_map["Blusas"]

        # Reasignar productos que apuntaban a categorías antiguas con números
        for prod in db.query(Product).all():
            old_cat = db.query(Category).filter(Category.id == prod.category_id).first()
            old_name = (old_cat.name if old_cat else "").lower()
            if "camisa" in old_name or "p9228" in prod.name.lower() or "prod" in prod.name.lower():
                prod.category_id = camisas_cat.id
                if not prod.material: prod.material = "Lino / Algodón"
                if not prod.neck_type: prod.neck_type = "Cuello camisero"
                if not prod.sleeve_length: prod.sleeve_length = "Manga larga"
                if not prod.tags: prod.tags = "Casual, Verano"
            elif "vestido" in old_name:
                prod.category_id = vestidos_cat.id
                if not prod.material: prod.material = "Seda / Viscosa"
                if not prod.neck_type: prod.neck_type = "Cuello en V"
                if not prod.sleeve_length: prod.sleeve_length = "Sin mangas"
                if not prod.tags: prod.tags = "Floral, Fiesta, Elegante"
            elif prod.category_id not in [s.id for s in subcat_map.values()]:
                prod.category_id = blusas_cat.id

            # Reasignar variantes a colores y tallas válidos inteligentemente
            used_combinations = set()
            for v in prod.variants:
                v_color = db.query(Color).filter(Color.id == v.color_id).first()
                old_cname = (v_color.name if v_color else "").lower()
                target_color = default_color
                if "rojo" in old_cname:
                    target_color = color_map["Rojo Vino"]
                elif "azul" in old_cname:
                    target_color = color_map["Azul Marino"]
                elif "blanco" in old_cname:
                    target_color = color_map["Blanco"]
                elif "negro" in old_cname:
                    target_color = color_map["Negro"]

                v_size = db.query(Size).filter(Size.id == v.size_id).first()
                old_sname = (v_size.name if v_size else "").lower()
                target_size = default_size
                if "xs" in old_sname:
                    target_size = size_map["XS"]
                elif "xl" in old_sname:
                    target_size = size_map["XL"]
                elif "s" in old_sname:
                    target_size = size_map["S"]
                elif "m" in old_sname:
                    target_size = size_map["M"]
                elif "l" in old_sname:
                    target_size = size_map["L"]

                # Evitar colisiones de (product_id, color_id, size_id)
                key = (prod.id, target_color.id, target_size.id)
                if key in used_combinations:
                    # Buscar otra talla que no colisione
                    for s_candidate in [size_map["S"], size_map["M"], size_map["L"], size_map["XL"], size_map["XS"]]:
                        cand_key = (prod.id, target_color.id, s_candidate.id)
                        if cand_key not in used_combinations:
                            target_size = s_candidate
                            key = cand_key
                            break

                used_combinations.add(key)
                v.color_id = target_color.id
                v.size_id = target_size.id

            # Reasignar fotos a colores válidos
            for img in prod.images:
                if img.color_id:
                    i_col = db.query(Color).filter(Color.id == img.color_id).first()
                    old_iname = (i_col.name if i_col else "").lower()
                    if "rojo" in old_iname:
                        img.color_id = color_map["Rojo Vino"].id
                    elif "azul" in old_iname:
                        img.color_id = color_map["Azul Marino"].id
                    else:
                        img.color_id = default_color.id

        db.commit()

        # Eliminar categorías de test que ya no tienen productos
        valid_cat_ids = {p.id for p in db.query(Category).filter(Category.parent_id == None).all()}
        valid_cat_ids.update({s.id for s in subcat_map.values()})

        for old_c in db.query(Category).all():
            if old_c.id not in valid_cat_ids and not old_c.products:
                db.delete(old_c)

        # Eliminar tallas de test
        valid_size_names = {s[0] for s in SIZES}
        for old_s in db.query(Size).all():
            if old_s.name not in valid_size_names:
                # Verificar si está en uso
                used = db.query(ProductVariant).filter(ProductVariant.size_id == old_s.id).first()
                if not used:
                    db.delete(old_s)

        # Eliminar colores de test
        valid_color_names = {c[0] for c in COLORS}
        for old_col in db.query(Color).all():
            if old_col.name not in valid_color_names:
                used = db.query(ProductVariant).filter(ProductVariant.color_id == old_col.id).first()
                if not used:
                    db.delete(old_col)

        db.commit()
        print("Taxonomía de Moda Femenina inicializada exitosamente.")
    except Exception as e:
        db.rollback()
        print("Error durante seed:", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run()
