# Suppliers Package - [CU08]
from app.packages.inventario_y_proveedores.suppliers.models import Supplier
from app.packages.inventario_y_proveedores.suppliers.routers import router

__all__ = ["Supplier", "router"]
