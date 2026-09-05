# CLAUDE.md - Guía de Desarrollo para el Asistente AI (Claude)

Este archivo contiene las directrices de codificación, comandos frecuentes y la arquitectura de la plataforma **FashionStore** (Comercio Electrónico con Vestidor Virtual mediante Realidad Aumentada).

## Comandos del Proyecto

### Backend (FastAPI - Python)
- **Instalar dependencias:** `pip install -r requirements.txt` o `uv pip install -r requirements.txt`
- **Configurar entorno:** copiar `.env.example` a `.env` y ajustar `DATABASE_URL` de PostgreSQL
- **Sembrar datos base (roles + admin):** `python seed_admin.py` (desde `backend/`)
- **Iniciar servidor de desarrollo:** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (desde `backend/`; `--host 0.0.0.0` es necesario para que la app móvil en un teléfono físico pueda conectarse)
- **Ejecutar pruebas unitarias:** `pytest`

### Frontend Web (Angular - TypeScript)
- **Instalar dependencias:** `npm install`
- **Iniciar servidor de desarrollo:** `ng serve`
- **Compilar para producción:** `ng build --configuration production`

### Aplicación Móvil (Flutter - Dart)
- **Obtener dependencias:** `flutter pub get`
- **Iniciar en dispositivo/emulador:** `flutter run`
- **Generar código (si usa build_runner):** `flutter pub run build_runner build`

### Base de Datos (PostgreSQL)
- **Crear la base:** desde pgAdmin 4 → `CREATE DATABASE fashionstore;`
- **Crear tablas:** se crean automáticamente al arrancar `uvicorn` (o al correr `seed_admin.py`)
- **Migraciones (opcional / futuro):** Alembic — `alembic upgrade head` / `alembic revision --autogenerate -m "..."`

---

## Estado actual (Ciclo 1)

- **Arquitectura única por paquetes.** El código vive exclusivamente bajo
  `backend/app/packages/`, `frontend-web/src/app/packages/` y
  `mobile/lib/src/packages/` (se eliminó la estructura "plana" antigua).
- **Frontend web:** usa **Bootstrap 5 + bootstrap-icons** (enlazados en `angular.json`)
  más una capa de tema terracota en `src/styles.css`. La URL del backend se configura
  en `src/environments/environment.ts`. El token JWT se inyecta con
  `AuthInterceptor`; las rutas `/admin/*` están protegidas por `AuthGuard`.
- **Backend:** PostgreSQL (SQLAlchemy). CORS restringido a los orígenes de
  `BACKEND_CORS_ORIGINS`. Bcrypt fijado a `4.0.1` por compatibilidad con passlib.
  `main.py` corre "migraciones ligeras" idempotentes (`ALTER TABLE ... ADD COLUMN IF NOT
  EXISTS` + normalización de `users.email` a minúsculas) tras `create_all`, mientras no se
  adopte Alembic.
- **Auth:** el **correo es único e insensible a mayúsculas** (los schemas de
  `seguridad_y_usuarios` lo normalizan a minúsculas en login/registro/recuperación/CU05), para
  que registrarse en la web e iniciar sesión en el móvil coordinen. La app móvil resuelve la
  URL del backend con `--dart-define=API_BASE_URL=` (producción) o `API_HOST`/`API_PORT` (dev);
  ver `mobile/README.md`. `/auth/recover` devuelve `dev_reset_link` solo si SMTP no está
  configurado.
- **Numeración de casos de uso:** lista maestra de **40 CU** en `Contexto.md`
  (`Listado_General_Casos_Uso.md` quedó obsoleto; equivalencias en `Ciclo1.md` §6.3).
- **Documentación del Ciclo 1: un solo archivo, `Ciclo1.md`** — reúne captura de requisitos
  (actores, priorización, 14 fichas de CU, prototipos, modelo de CU con include/extend/herencia),
  análisis (arquitectura, diagramas de comunicación, análisis de clases, acoplamiento/cohesión),
  diseño (4 capas + despliegue, diagramas de secuencia/navegación/estado/tiempo, diseño de datos),
  implementación (rutas, estructura por paquete) y pruebas + trazabilidad CU↔código.
  Los antiguos archivos `*_ciclo1.md` sueltos fueron eliminados tras consolidarse aquí.
  Incluye **15 fichas de CU** (CU01–CU11, CU14, CU36–CU38) más notas sobre CU12/CU13.
- **Casos de uso cubiertos (Ciclo 1):** CU01–CU11, **CU14** (reseñas + favoritos, versión
  ligera), CU36, **CU37** (valoración de inventario / capital invertido por costo promedio
  ponderado) y **CU38** (ajustes de inventario / mermas).
- **Catálogo enriquecido (CU07/CU11):** galería de imágenes por prenda servida desde `/uploads`
  (`POST /catalog/upload-image` + `StaticFiles`), **prendas multicolor** (el color elegido cambia
  fotos y tallas), **categorías con foto**, **oferta directa por prenda** (`products.compare_at_price`
  → precio tachado y −%), y **vista de detalle** de prenda (`/tienda/producto/:id` en web,
  `product_detail_view.dart` en móvil) con guía de tallas y reseñas. Tablas nuevas:
  `product_reviews`, `wishlist_items` (nacen del `create_all`); columnas nuevas vía
  `_COLUMN_UPGRADES` en `main.py`. El catálogo del cliente corre **igual en web y móvil**.
- **`ventas_y_pagos`:** en el Ciclo 1 solo modelos (`orders`, `order_items`, `payments` con
  herencia de tabla única Efectivo/Tarjeta/QR/Crédito, `invoices` con IVA 13 %); sin routers.

---

## Directrices de Programación

### Backend (Python / FastAPI)
- **Estructura por Capas:** Seguir un patrón de arquitectura limpia: `Routers/Controllers` -> `Services (Lógica de Negocio)` -> `Repositories/Models (Acceso a Datos)`.
- **Tipado Estricto:** Usar Type Hints en todas las firmas de funciones y modelos Pydantic para validación.
- **Manejo de Errores:** Lanzar excepciones HTTP detalladas (`HTTPException`) y evitar fugas de información interna en producción.
- **Base de Datos:** Usar SQLAlchemy de forma asíncrona. Toda transacción compleja debe asegurar aislamiento ACID y manejar bloqueos concurrentes.

### Frontend (Angular)
- **Componentes Reactivos:** Uso de `RxJS` para la gestión de flujos de datos.
- **Tipado estricto en TypeScript:** Evitar el uso de `any`. Definir interfaces precisas para las respuestas de la API.
- **Servicios:** Centralizar llamadas HTTPS en servicios dedicados inyectables.

### Móvil (Flutter)
- **Gestión de Estado:** Seguir patrones recomendados como `BLoC` o `Provider`.
- **Estructura:** Separar la lógica de negocio de la interfaz de usuario (UI reactiva).
- **Acceso a Cámara (RA):** Asegurar el manejo correcto de permisos de sistema operativo (Android/iOS) y ciclo de vida de la cámara.

---

## Estilo y Calidad del Código
- **Idioma:** Variables y base de datos en inglés (recomendable para código limpio internacional) o español consistente con la base actual. Comentarios y documentación en español.
- **Nombres:**
  - Python: `snake_case` para variables y funciones; `PascalCase` para clases.
  - TypeScript/Dart: `camelCase` para variables y funciones; `PascalCase` para clases y componentes.
- **Documentación:** Cada endpoint, clase o método complejo debe contar con Docstrings explicativos.
