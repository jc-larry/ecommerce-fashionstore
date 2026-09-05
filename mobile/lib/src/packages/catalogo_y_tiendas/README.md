# Paquete `catalogo_y_tiendas` — App Móvil (Flutter)

Casos de uso del Ciclo 1:

- **CU11 — Consultar catálogo (cliente).** Navegación por categorías (con foto), grilla
  lookbook con oferta / ★ promedio / ♥, y **vista de detalle** de prenda: galería, selección
  de color que cambia fotos y tallas disponibles, guía de tallas, descripción y entrega
  estimada. Paridad con la web.
- **CU14 — Reseñas y favoritos (versión ligera).** Una reseña por prenda (1–5★ + comentario,
  editable, sin moderación) desde el detalle; favoritos (♥) con pantalla "Favoritos".

## Archivos

| Archivo | Rol |
| :-- | :-- |
| `catalog_api.dart` | Cliente HTTP del catálogo (productos, categorías, detalle, reseñas, ratings-summary, wishlist). Inyecta el token si hay sesión. |
| `catalogo_view.dart` | CU11 — home de la tienda: buscador, tira de categorías, hero, grilla lookbook. |
| `product_detail_view.dart` | CU11 + CU14 — detalle de prenda: galería (PageView), selector de color, tallas por color, guía de tallas (bottom sheet), descripción (ExpansionTile), reseñas (promedio + lista + formulario). |
| `wishlist_view.dart` | CU14 — grilla de prendas favoritas, ♥ para quitar. |
| `store_shell.dart` | Barra inferior del cliente: Inicio · Catálogo · Carrito (próximamente) · Favoritos · Perfil (el "cerrar sesión" vive aquí). Es la pantalla a la que entra el cliente tras el login. |
| `branches/` | Sin UI móvil en el Ciclo 1 (gestión de sucursales es solo web). |

## Diferido al Ciclo 2

CU12 (buscar/filtrar por precio/talla/color/ocasión + disponibilidad por sucursal),
CU13 (cupones y campañas de temporada), y la ampliación de CU14 (wishlist múltiple,
reseñas con moderación). El carrito (CU17) aparece deshabilitado ("próximamente").

## Backend consumido (`/api/v1/catalog`)

`GET /products`, `GET /products/{id}`, `GET /ratings-summary`,
`GET|POST /products/{id}/reviews`, `GET /wishlist`, `POST|DELETE /wishlist/{product_id}`.
Las imágenes se resuelven con `CatalogApi.resolveImage` (quita `/api/v1` de la base y sirve
desde `/uploads`).
