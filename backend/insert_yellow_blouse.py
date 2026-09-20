"""
Script para insertar la nueva prenda al catálogo:
Blusa Romántica Escote V Encaje Butter Yellow
"""
import os
import sys
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.packages.paquete_catalogo_y_tiendas.models import Category, Color, Size, Product, ProductVariant, ProductImage
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger

def insert_blouse():
    db = SessionLocal()
    try:
        # 1. Verificar o registrar el Color 'Amarillo Pastel / Butter Yellow'
        color = db.query(Color).filter(Color.name.ilike("%Amarillo%")).first()
        if not color:
            color = Color(name="Amarillo Pastel / Butter Yellow", hex_code="#FBE8A6")
            db.add(color)
            db.flush()
            print(f"Color creado: ID {color.id} - {color.name}")
        else:
            print(f"Color existente encontrado: ID {color.id} - {color.name}")

        # 2. Verificar categoría Blusas (ID 13) o buscar por nombre
        cat = db.query(Category).filter(Category.name.ilike("%Blusa%")).first()
        if not cat:
            cat = db.query(Category).first()
        print(f"Categoría asignada: ID {cat.id} - {cat.name}")

        # 3. Buscar si ya existe el producto con el mismo nombre para no duplicar
        prod_name = "Blusa Romántica Escote V Encaje Butter Yellow"
        product = db.query(Product).filter(Product.name == prod_name).first()
        if not product:
            product = Product(
                name=prod_name,
                description=(
                    "Delicada blusa femenina en tono mantequilla pastel con escote en V "
                    "realzado por finos festones de encaje bordado floral. Confeccionada en mezcla "
                    "de lino y algodón transpirable, corte fluido con mangas cortas fruncidas y "
                    "cierre frontal con botones nacarados al tono. Una prenda etérea, romántica y "
                    "sofisticada imprescindible para el catálogo de moda femenina."
                ),
                base_price=Decimal("189.00"),
                compare_at_price=Decimal("229.00"),
                category_id=cat.id,
                is_active=True,
                material="Lino & Algodón Suave con Detalle de Encaje Francés",
                neck_type="Escote en V con Bordado de Encaje Floral",
                sleeve_length="Manga Corta Fruncida",
                tags="Blusa, Encaje, Butter Yellow, Amarillo Pastel, Romántica, Casual Chic, Mujer",
            )
            db.add(product)
            db.flush()
            print(f"Producto creado con éxito: ID {product.id} - {product.name}")
        else:
            print(f"Producto ya existía: ID {product.id} - {product.name}. Actualizando atributos...")
            product.description = (
                "Delicada blusa femenina en tono mantequilla pastel con escote en V "
                "realzado por finos festones de encaje bordado floral. Confeccionada en mezcla "
                "de lino y algodón transpirable, corte fluido con mangas cortas fruncidas y "
                "cierre frontal con botones nacarados al tono. Una prenda etérea, romántica y "
                "sofisticada imprescindible para el catálogo de moda femenina."
            )
            product.base_price = Decimal("189.00")
            product.compare_at_price = Decimal("229.00")
            product.category_id = cat.id
            product.is_active = True
            product.material = "Lino & Algodón Suave con Detalle de Encaje Francés"
            product.neck_type = "Escote en V con Bordado de Encaje Floral"
            product.sleeve_length = "Manga Corta Fruncida"
            product.tags = "Blusa, Encaje, Butter Yellow, Amarillo Pastel, Romántica, Casual Chic, Mujer"
            db.flush()

        # 4. Asignar Imagen Primaria del producto
        image_url = "/uploads/products/blusa_amarilla_encaje.png"
        existing_img = db.query(ProductImage).filter(
            ProductImage.product_id == product.id,
            ProductImage.image_url == image_url
        ).first()

        if not existing_img:
            # Desmarcar otras si existen
            db.query(ProductImage).filter(ProductImage.product_id == product.id).update({"is_primary": False})
            new_img = ProductImage(
                product_id=product.id,
                color_id=color.id,
                image_url=image_url,
                is_primary=True
            )
            db.add(new_img)
            db.flush()
            print(f"Imagen principal registrada: {image_url}")
        else:
            existing_img.is_primary = True
            existing_img.color_id = color.id
            db.flush()
            print(f"Imagen principal ya existía: {image_url}")

        # 5. Registrar variantes de tallas (XS, S, M, L, XL)
        sizes = db.query(Size).filter(Size.category_type == "TOPS").all()
        if not sizes:
            sizes = db.query(Size).filter(Size.name.in_(["XS", "S", "M", "L", "XL"])).all()

        branches = db.query(Branch).all()
        created_variants = []

        for sz in sizes:
            if sz.name not in ["XS", "S", "M", "L", "XL"]:
                continue
            sku = f"BLU-ENC-YEL-{sz.name}"
            variant = db.query(ProductVariant).filter(
                ProductVariant.product_id == product.id,
                ProductVariant.size_id == sz.id,
                ProductVariant.color_id == color.id
            ).first()

            if not variant:
                # Comprobar SKU unico
                variant_by_sku = db.query(ProductVariant).filter(ProductVariant.sku == sku).first()
                if variant_by_sku:
                    sku = f"BLU-ENC-YEL-{sz.name}-{product.id}"
                
                variant = ProductVariant(
                    product_id=product.id,
                    size_id=sz.id,
                    color_id=color.id,
                    sku=sku,
                    is_active=True
                )
                db.add(variant)
                db.flush()
                print(f"Variante creada: SKU {variant.sku} (Talla {sz.name})")
            
            created_variants.append(variant)

            # 6. Sembrar Inventario para cada sucursal
            for br in branches:
                inv = db.query(Inventory).filter(
                    Inventory.branch_id == br.id,
                    Inventory.variant_id == variant.id
                ).first()

                if not inv:
                    inv = Inventory(
                        branch_id=br.id,
                        variant_id=variant.id,
                        stock_actual=12,
                        avg_cost=Decimal("75.00"),
                        stock_minimo=3,
                        stock_maximo=50
                    )
                    db.add(inv)
                    db.flush()
                    print(f"  -> Stock asignado en sucursal '{br.name}': 12 unidades")

        db.commit()
        print("\n=======================================================")
        print(f"¡PRENDA AGREGADA AL CATÁLOGO CON ÉXITO!")
        print(f"ID Producto: {product.id}")
        print(f"Nombre: {product.name}")
        print(f"Precio: Bs. {product.base_price}")
        print(f"Imagen: {image_url}")
        print(f"Variantes creadas: {len(created_variants)}")
        print("=======================================================")

    except Exception as e:
        db.rollback()
        print(f"Error al insertar prenda: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    insert_blouse()
