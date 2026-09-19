"""Fix: truncar productos y re-insertar."""
from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    # Obtener tablas existentes
    result = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
    tables = [row[0] for row in result]
    print("Tablas existentes:", tables)

    # Truncar solo las que existen
    to_truncate = [t for t in ['product_images', 'product_variants', 'products'] if t in tables]
    if to_truncate:
        sql = f"TRUNCATE TABLE {', '.join(to_truncate)} RESTART IDENTITY CASCADE"
        print(f"Ejecutando: {sql}")
        db.execute(text(sql))
        db.commit()
        print("Truncadas correctamente")

    count = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
    print(f"Productos restantes: {count}")
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
