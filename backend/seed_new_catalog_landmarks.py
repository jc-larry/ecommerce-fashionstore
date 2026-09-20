"""
Script de Renovación del Catálogo: Nuevas Prendas con Landmarks Anatómicos
==========================================================================
1. Procesa las 4 imágenes de prendas (remoción de fondo con rembg, canal alfa, PNG limpio).
2. Procesa las 4 fotos de modelos reales (remoción de fondo con rembg, fondo blanco puro).
3. Limpia el catálogo anterior de la BD PostgreSQL.
4. Inserta las 4 nuevas prendas con categorías, colores, tallas, precios, inventario y landmarks.
"""

import sys, os, shutil
from decimal import Decimal
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
import io

# --- Configuración de rutas ---
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_PRODUCTS = os.path.join(BACKEND_DIR, "uploads", "products")
UPLOADS_MODELS = os.path.join(BACKEND_DIR, "uploads", "models")
UPLOADED_DIR = r"C:\Users\MARILYN\.gemini\antigravity-ide\brain\5410cfdd-c52b-4006-898e-b02cf9723cf1\.user_uploaded"

os.makedirs(UPLOADS_PRODUCTS, exist_ok=True)
os.makedirs(UPLOADS_MODELS, exist_ok=True)

# --- Mapeo de archivos fuente ---
GARMENT_FILES = {
    "blusa_peplum_blanca": "media_1789613141606.png",
    "top_dior_beige": "media_1789613196701.png",
    "blusa_camel_botones": "media_1789613214220.png",
    "blazer_chocolate": "media_1789613261133.png",
}

MODEL_FILES = {
    "sofia": "media_1789614335087.jpg",
    "valeria": "media_1789614388646.jpg",
    "lin": "media_1789614410380.jpg",
    "emma": "media_1789614433725.jpg",
    "valeria2": "media_1789614423928.jpg",
}


def process_garment_image(src_path: str, dest_name: str) -> str:
    """Procesa imagen de prenda: remueve fondo con rembg y guarda PNG transparente + JPG con fondo blanco."""
    print(f"  Procesando prenda: {dest_name}...")
    img = Image.open(src_path).convert("RGBA")

    # Recortar el 8% inferior para remover íconos de interfaz / marcas de zoom
    crop_bottom = int(img.height * 0.08)
    if crop_bottom > 0:
        img = img.crop((0, 0, img.width, img.height - crop_bottom))

    # Remoción de fondo con rembg (red neuronal u2net)
    try:
        from rembg import remove
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        result_bytes = remove(img_bytes.getvalue())
        img_no_bg = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    except Exception as e:
        print(f"    [WARN] rembg falló ({e}), usando fallback de umbral blanco...")
        # Fallback: remover fondo blanco/gris claro
        datas = img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        img_no_bg = img.copy()
        img_no_bg.putdata(new_data)

    # Guardar PNG transparente
    png_path = os.path.join(UPLOADS_PRODUCTS, f"{dest_name}.png")
    img_no_bg.save(png_path, "PNG", optimize=True)

    # Guardar JPG con fondo blanco puro de estudio
    white_bg = Image.new("RGBA", img_no_bg.size, (255, 255, 255, 255))
    white_bg.paste(img_no_bg, (0, 0), img_no_bg)
    jpg_path = os.path.join(UPLOADS_PRODUCTS, f"{dest_name}.jpg")
    white_bg.convert("RGB").save(jpg_path, "JPEG", quality=92)

    print(f"    ✅ {png_path}")
    print(f"    ✅ {jpg_path}")
    return f"/uploads/products/{dest_name}.png"


def process_model_image(src_path: str, dest_name: str) -> str:
    """Procesa foto de modelo: remueve fondo con rembg, fondo blanco puro, estandariza a 720x1080."""
    print(f"  Procesando modelo: {dest_name}...")
    img = Image.open(src_path).convert("RGBA")

    # Remoción de fondo con rembg
    try:
        from rembg import remove
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        result_bytes = remove(img_bytes.getvalue())
        person_no_bg = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    except Exception as e:
        print(f"    [WARN] rembg falló ({e}), usando imagen original...")
        person_no_bg = img

    # Estandarizar a lienzo 720x1080 con fondo blanco puro
    target_w, target_h = 720, 1080
    studio_bg = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))

    # Redimensionar manteniendo aspecto y anclando a la base
    aspect = person_no_bg.width / max(1, person_no_bg.height)
    target_aspect = target_w / target_h
    if aspect > target_aspect:
        new_w = target_w
        new_h = int(target_w / aspect)
    else:
        new_h = target_h
        new_w = int(target_h * aspect)

    p_resized = person_no_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
    pos_x = (target_w - new_w) // 2
    pos_y = target_h - new_h  # Anclado a la base

    studio_bg.paste(p_resized, (pos_x, pos_y), p_resized)

    # Guardar PNG
    png_path = os.path.join(UPLOADS_MODELS, f"{dest_name}.png")
    studio_bg.save(png_path, "PNG", optimize=True)

    # Guardar JPG
    jpg_path = os.path.join(UPLOADS_MODELS, f"{dest_name}.jpg")
    studio_bg.convert("RGB").save(jpg_path, "JPEG", quality=92)

    print(f"    ✅ {png_path}")
    print(f"    ✅ {jpg_path}")
    return f"/uploads/models/{dest_name}.png"


def seed_database():
    """Limpia catálogo anterior e inserta las 4 nuevas prendas con landmarks."""
    from sqlalchemy import text
    from app.db.session import engine, SessionLocal, Base
    from app.packages.paquete_catalogo_y_tiendas.models import (
        Category, Product, ProductVariant, ProductImage, Color, Size, Season
    )

    print("\n--- FASE 3: Saneamiento de la Base de Datos ---")
    db = SessionLocal()

    try:
        # 1. Limpiar tablas dependientes
        print("  Limpiando registros anteriores del catálogo...")
        # Orden correcto para respetar foreign keys
        tables_to_clean = [
            "tryon_captures",
            "tryon_session_items",
            "tryon_sessions",
            "inventory_ledger",
            "inventories",
            "purchase_details",
            "purchase_orders",
            "order_items",
            "orders",
            "wishlist_items",
            "product_reviews",
            "product_images",
            "product_variants",
            "products",
        ]
        for tbl in tables_to_clean:
            try:
                db.execute(text(f"DELETE FROM {tbl}"))
                print(f"    🗑️  {tbl} limpiada")
            except Exception:
                db.rollback()
        db.commit()

        # 2. Asegurar categorías necesarias
        print("  Verificando categorías...")
        categories_needed = {
            "Blusas": "Blusas y tops femeninos elegantes de manga corta",
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
            print(f"    📁 Categoría '{cat_name}' id={cat_map[cat_name].id}")

        # 3. Asegurar colores necesarios
        print("  Verificando colores...")
        colors_needed = {
            "Blanco": "#FFFFFF",
            "Beige": "#D4C5A9",
            "Camel": "#A67B5B",
            "Chocolate": "#3E2723",
            "Marfil": "#FFFFF0",
            "Crema": "#FFFDD0",
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
            print(f"    🎨 Color '{col_name}' ({col_hex}) id={color_map[col_name].id}")

        # 4. Asegurar tallas necesarias
        print("  Verificando tallas...")
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

        # 5. Insertar las 4 nuevas prendas
        print("\n  Insertando nuevas prendas...")

        PRENDAS = [
            {
                "name": "Blusa Peplum Plisada Escote V con Botones de Carey",
                "description": (
                    "Blusa femenina plisada con corte peplum y escote en V pronunciado. "
                    "Botones de carey centrales que añaden un toque artesanal y sofisticado. "
                    "Manga corta tipo cap sleeve con caída suave sobre los hombros. "
                    "Abertura plisada en la parte inferior que aporta movimiento y vuelo elegante. "
                    "Confeccionada en tela de lino texturizado ligero, ideal para climas cálidos y eventos semiformal."
                ),
                "base_price": Decimal("189.00"),
                "compare_at_price": Decimal("249.00"),
                "category": "Blusas",
                "color": "Blanco",
                "material": "Lino texturizado",
                "neck_type": "Escote en V pronunciado",
                "sleeve_length": "Manga corta cap sleeve",
                "tags": "peplum,plisada,botones carey,escote V,lino,blanco,elegante",
                "image_file": "blusa_peplum_blanca",
                # Landmarks anatómicos normalizados (0.0 a 1.0)
                "landmarks": {
                    "neck_y": 0.08,       # Escote V comienza alto
                    "neck_depth": 0.22,   # V profundo hasta el 30% de la prenda
                    "shoulder_y": 0.06,   # Hombros en la parte superior
                    "shoulder_width": 0.72,  # Ancho de hombros relativo al ancho de prenda
                    "chest_y": 0.32,      # Línea de busto
                    "waist_y": 0.55,      # Cintura entallada
                    "hem_y": 0.95,        # Bajo con peplum y abertura plisada
                    "type": "peplum_v_neck",
                },
            },
            {
                "name": "Top Sastre Off-Shoulder Cruzado Estilo Haute Couture",
                "description": (
                    "Top sastre de alta costura con escote barco off-shoulder que descubre los hombros con elegancia. "
                    "Diseño cruzado con doble hilera de botones forrados que ciñe y define la cintura. "
                    "Corte peplum con vuelo sutil en la cadera. "
                    "Manga corta estructurada. Confección en crepé grueso con acabado mate premium. "
                    "Inspiración directa de pasarela Haute Couture parisina."
                ),
                "base_price": Decimal("320.00"),
                "compare_at_price": Decimal("450.00"),
                "category": "Tops / Crop Tops",
                "color": "Beige",
                "material": "Crepé grueso acabado mate",
                "neck_type": "Escote barco off-shoulder",
                "sleeve_length": "Manga corta estructurada",
                "tags": "off-shoulder,cruzado,haute couture,beige,sastre,botones,peplum",
                "image_file": "top_dior_beige",
                "landmarks": {
                    "neck_y": 0.12,       # Escote barco más abajo
                    "neck_depth": 0.06,   # Escote poco profundo (barco)
                    "shoulder_y": 0.10,   # Off-shoulder: hombros descubiertos
                    "shoulder_width": 0.82,  # Muy amplio por off-shoulder
                    "chest_y": 0.30,
                    "waist_y": 0.52,
                    "hem_y": 0.92,
                    "type": "off_shoulder_double_breasted",
                },
            },
            {
                "name": "Blusa Estructurada Cuello Redondo con Botones Dorados de Relieve",
                "description": (
                    "Blusa femenina de corte entallado con cuello redondo caja cerrado. "
                    "Cierre frontal con botones dorados de relieve estilo medallón que aportan un acento lujoso. "
                    "Manga corta ligeramente por encima del codo. "
                    "Dos bolsillos de solapa en la cintura que definen la silueta. "
                    "Confección en lino estructurado con acabado tipo gamuza suave. "
                    "Color camel / canela perfecto para temporadas de transición otoño-primavera."
                ),
                "base_price": Decimal("210.00"),
                "compare_at_price": Decimal("285.00"),
                "category": "Blusas",
                "color": "Camel",
                "material": "Lino estructurado acabado gamuza",
                "neck_type": "Cuello redondo caja cerrado",
                "sleeve_length": "Manga corta sobre el codo",
                "tags": "estructurada,cuello redondo,botones dorados,camel,bolsillos,entallada",
                "image_file": "blusa_camel_botones",
                "landmarks": {
                    "neck_y": 0.05,
                    "neck_depth": 0.04,   # Cuello cerrado
                    "shoulder_y": 0.07,
                    "shoulder_width": 0.68,
                    "chest_y": 0.30,
                    "waist_y": 0.54,
                    "hem_y": 0.93,
                    "type": "crew_neck_structured",
                },
            },
            {
                "name": "Blazer Peplum Manga Corta con Solapa Clásica y Botones Dorados",
                "description": (
                    "Blazer femenino de manga corta con solapa de muesca clásica y corte peplum acampanado. "
                    "Cierre frontal con tres botones dorados de relieve estilo escudo. "
                    "Corte sastre entallado que define la cintura con vuelo en las caderas. "
                    "Forro interior parcial para mayor comodidad. "
                    "Confeccionado en paño de mezcla con acabado liso aterciopelado. "
                    "Color chocolate oscuro sofisticado para eventos formales y de oficina."
                ),
                "base_price": Decimal("350.00"),
                "compare_at_price": Decimal("480.00"),
                "category": "Blazers",
                "color": "Chocolate",
                "material": "Paño mezcla acabado aterciopelado",
                "neck_type": "Solapa de muesca clásica en V",
                "sleeve_length": "Manga corta sobre el codo",
                "tags": "blazer,peplum,manga corta,solapa,botones dorados,chocolate,sastre,formal",
                "image_file": "blazer_chocolate",
                "landmarks": {
                    "neck_y": 0.06,
                    "neck_depth": 0.18,   # Solapa V moderada
                    "shoulder_y": 0.05,
                    "shoulder_width": 0.76,  # Blazer: hombros más definidos
                    "chest_y": 0.28,
                    "waist_y": 0.50,
                    "hem_y": 0.94,
                    "type": "blazer_notch_lapel_peplum",
                },
            },
        ]

        garment_image_urls = {}
        for prenda_data in PRENDAS:
            # Crear producto
            cat = cat_map[prenda_data["category"]]
            product = Product(
                name=prenda_data["name"],
                description=prenda_data["description"],
                base_price=prenda_data["base_price"],
                compare_at_price=prenda_data["compare_at_price"],
                category_id=cat.id,
                is_active=True,
                material=prenda_data["material"],
                neck_type=prenda_data["neck_type"],
                sleeve_length=prenda_data["sleeve_length"],
                tags=prenda_data["tags"],
            )
            db.add(product)
            db.flush()
            print(f"    👗 Prenda '{product.name}' id={product.id}")

            # Imagen principal
            img_url = garment_image_urls.get(prenda_data["image_file"],
                                              f"/uploads/products/{prenda_data['image_file']}.png")
            color = color_map[prenda_data["color"]]
            pi = ProductImage(
                product_id=product.id,
                color_id=color.id,
                image_url=img_url,
                is_primary=True,
            )
            db.add(pi)

            # Variantes de talla
            for sz_name in sizes_needed:
                sz = size_map[sz_name]
                sku = f"FS-{prenda_data['image_file'].upper().replace('_', '')[:8]}-{prenda_data['color'].upper()[:3]}-{sz_name}"
                variant = ProductVariant(
                    product_id=product.id,
                    color_id=color.id,
                    size_id=sz.id,
                    sku=sku,
                    is_active=True,
                )
                db.add(variant)
            db.flush()
            print(f"      ↳ {len(sizes_needed)} variantes de talla creadas ({', '.join(sizes_needed)})")

        # 6. Crear inventario por sucursal
        print("\n  Creando inventario por sucursal...")
        try:
            from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
            from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory
            branches = db.query(Branch).all()
            all_variants = db.query(ProductVariant).all()
            inv_count = 0
            for branch in branches:
                for variant in all_variants:
                    # Verificar si ya existe
                    existing_inv = db.query(Inventory).filter(
                        Inventory.branch_id == branch.id,
                        Inventory.variant_id == variant.id
                    ).first()
                    if not existing_inv:
                        stock = 20 + (variant.id % 15)  # Stock entre 20 y 34
                        inv = Inventory(
                            branch_id=branch.id,
                            variant_id=variant.id,
                            stock_actual=stock,
                            stock_min=5,
                        )
                        db.add(inv)
                        inv_count += 1
            db.flush()
            print(f"    📦 {inv_count} registros de inventario creados")
        except Exception as e:
            print(f"    [INFO] Inventario no creado (puede no existir la tabla aún): {e}")

        db.commit()
        print("\n✅ Base de datos actualizada exitosamente con las 4 nuevas prendas.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante el seed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    print("=" * 70)
    print("  RENOVACIÓN DEL CATÁLOGO FASHIONSTORE")
    print("  4 Nuevas Prendas + 4 Modelos Reales + Landmarks Anatómicos")
    print("=" * 70)

    # FASE 1: Procesar imágenes de prendas
    print("\n--- FASE 1: Procesamiento de Imágenes de Prendas ---")
    garment_urls = {}
    for dest_name, src_file in GARMENT_FILES.items():
        src_path = os.path.join(UPLOADED_DIR, src_file)
        if os.path.isfile(src_path):
            url = process_garment_image(src_path, dest_name)
            garment_urls[dest_name] = url
        else:
            print(f"  ⚠️ Archivo no encontrado: {src_path}")

    # FASE 2: Procesar fotos de modelos
    print("\n--- FASE 2: Procesamiento de Fotos de Modelos Reales ---")
    model_urls = {}
    for dest_name, src_file in MODEL_FILES.items():
        src_path = os.path.join(UPLOADED_DIR, src_file)
        if os.path.isfile(src_path):
            url = process_model_image(src_path, dest_name)
            model_urls[dest_name] = url
        else:
            print(f"  ⚠️ Archivo no encontrado: {src_path}")

    # FASE 3: Seed de la base de datos
    seed_database()

    print("\n" + "=" * 70)
    print("  ✅ PROCESO COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
