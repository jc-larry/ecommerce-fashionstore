# Casos de Uso y Arquitectura de Paquetes - Ciclo 1

Este documento detalla los casos de uso a ser desarrollados e implementados durante el **Ciclo 1** de la plataforma de comercio electrónico FashionStore, así como el **diseño arquitectónico de paquetes (UML)** que regirá el desarrollo integral del sistema. 

Para mantener consistencia absoluta entre la documentación y el código fuente, los paquetes físicos en el código asumen los nombres exactos en español definidos en la arquitectura (utilizando formato `snake_case` para compatibilidad de lenguajes).

---

## 1. Diseño Arquitectónico: Los 8 Paquetes del Sistema

El sistema se ha modelado estrictamente en **8 paquetes lógicos**.

### 📦 1. Paquete de Seguridad y Usuarios (`seguridad_y_usuarios`)
**Propósito:** Autenticación (JWT), RBAC (Roles) y gestión de perfiles.
* **CU01:** Iniciar sesión
* **CU02:** Cerrar sesión
* **CU03:** Recuperar credenciales
* **CU04:** Auto-registro cliente
* **CU05:** Gestionar perfiles y roles
* **CU36:** Consultar bitácora de auditoría

### 📦 2. Paquete de Catálogo y Tiendas (`catalogo_y_tiendas`)
**Propósito:** Administra sucursales físicas, su personal y el catálogo unificado de prendas.
* **CU06:** Gestionar sucursales
* **CU07:** Gestionar catálogo
* **CU09:** Gestionar empleados de sucursal
* **CU11:** Consultar catálogo *(cliente / visitante)*
* **CU12:** Buscar y filtrar catálogo avanzado — *(Ciclo 2)*
* **CU13:** Consultar disponibilidad por sucursal — *(Ciclo 2)*

### 📦 3. Paquete de Inventario y Proveedores (`inventario_y_proveedores`)
**Propósito:** Controla el stock físico real, los proveedores y el abastecimiento.
* **CU08:** Gestionar proveedores
* **CU10:** Registrar compras e ingresos de mercadería
* **CU14:** Inventario general y transferencias entre tiendas — *(Ciclo 2)*
* **CU15:** Alertas automáticas de stock mínimo/máximo — *(Ciclo 2)*
* **CU21:** Actualización automática del inventario (trigger) — *(Ciclo 2)*

### 📦 4. Paquete de Ventas y Pagos (`ventas_y_pagos`) - *(Ciclo 2)*
**Propósito:** Transaccionalidad (carrito, checkout Stripe, POS presencial).
* **CU16 / CU17 / CU18 / CU19 / CU20**

### 📦 5. Paquete de Reservas y Citas (`reservas_y_citas`) - *(Ciclo 3)*
**Propósito:** Flujo online-to-offline para probarse ropa en tienda.
* **CU24 / CU25 / CU26 / CU27**

### 📦 6. Paquete de Envíos y Logística (`envios_y_logistica`) - *(Ciclo 3)*
**Propósito:** Traslado físico (delivery) y tracking.
* **CU29 / CU30**

### 📦 7. Paquete Inteligente y Analítica (`inteligente_y_analitica`) - *(Ciclo 3)*
**Propósito:** Realidad Aumentada, Chatbots y NLP.
* **CU22 / CU23 / CU31 / CU32 / CU33 / CU34 / CU35**

### 📦 8. Paquete de Notificaciones (`notificaciones`) - *(Ciclo 3)*
**Propósito:** Alertas en tiempo real.
* **CU28**

---

## 2. Implementación del Ciclo 1 (Móvil vs Web)

> [!IMPORTANT]
> **Alcance por canal en el Ciclo 1:**
> - **App Móvil (Flutter):** exclusiva para el **cliente final** (autenticación y consulta de catálogo). No incluye funciones administrativas.
> - **Frontend Web (Angular):** atiende **dos audiencias** en el mismo sitio, separadas por rol tras el inicio de sesión:
>   - **Personal** (`SUPERADMIN` / `ENCARGADO` / `CAJERO`) → **panel administrativo** (`/admin/...`).
>   - **Cliente** (`CLIENTE`) → **tienda del cliente** (`/tienda`): registro, inicio de sesión, recuperación de credenciales y consulta del catálogo desde el navegador (web responsive).
> - **Separación cliente / administrador:** el registro público (`CU04`) **siempre** crea rol `CLIENTE`; las cuentas de personal solo las crea un `SUPERADMIN` desde `CU05` (o `CU09` para encargados/cajeros).

| ID | Caso de uso | Móvil (Flutter) | Web (Angular) | Backend (FastAPI) | Paquete UML Exacto |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **CU01** | Iniciar sesión (cliente y personal) | ✅ Sí | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |
| **CU02** | Cerrar sesión | ✅ Sí | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |
| **CU03** | Recuperar credenciales (enlace por correo, 5 min) | ✅ Sí | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |
| **CU04** | Auto-registro de cliente | ✅ Sí | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |
| **CU05** | Gestionar perfiles y roles (alta de personal) | ❌ No | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |
| **CU06** | Gestionar sucursales | ❌ No | ✅ Sí | ✅ Sí | `catalogo_y_tiendas` |
| **CU07** | Gestionar catálogo | ❌ No | ✅ Sí | ✅ Sí | `catalogo_y_tiendas` |
| **CU08** | Gestionar proveedores | ❌ No | ✅ Sí | ✅ Sí | `inventario_y_proveedores` |
| **CU09** | Gestionar empleados | ❌ No | ✅ Sí | ✅ Sí | `catalogo_y_tiendas` |
| **CU10** | Registrar compras/ingresos | ❌ No | ✅ Sí | ✅ Sí | `inventario_y_proveedores` |
| **CU11** | Consultar catálogo (cliente) — *vista de solo lectura* | ✅ Sí | ✅ Sí | ✅ Sí | `catalogo_y_tiendas` |
| **CU36** | Consultar bitácora de auditoría | ❌ No | ✅ Sí | ✅ Sí | `seguridad_y_usuarios` |

> **Nota sobre CU11:** en el Ciclo 1 el cliente ya **consulta el catálogo** (listado de prendas visibles con búsqueda y filtro por categoría) tanto en web como en móvil. El filtrado avanzado por talla/color/precio, el carrito y la reserva/vestidor virtual quedan para los ciclos 2 y 3.

---

## 3. Estructura Física de Paquetes (Español Estricto)

### Backend (FastAPI - Python)
```text
backend/app/packages/
├── seguridad_y_usuarios/
├── catalogo_y_tiendas/
├── inventario_y_proveedores/
├── ventas_y_pagos/
├── reservas_y_citas/
├── envios_y_logistica/
├── inteligente_y_analitica/
└── notificaciones/
```

### Frontend Web (Angular)
```text
frontend-web/src/app/packages/
├── seguridad_y_usuarios/
├── catalogo_y_tiendas/
├── inventario_y_proveedores/
├── ventas_y_pagos/
├── reservas_y_citas/
├── envios_y_logistica/
├── inteligente_y_analitica/
└── notificaciones/
```

### Aplicación Móvil (Flutter)
```text
mobile/lib/src/packages/
├── seguridad_y_usuarios/
├── catalogo_y_tiendas/
├── inventario_y_proveedores/
├── ventas_y_pagos/
├── reservas_y_citas/
├── envios_y_logistica/
├── inteligente_y_analitica/
└── notificaciones/
```
