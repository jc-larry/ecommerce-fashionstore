# Estructura de Paquetes — Frontend Web (Angular)

Cada subdirectorio de `packages/` corresponde a **uno de los 8 paquetes lógicos** del diagrama
UML de FashionStore (mismos nombres en español que el backend y el móvil). Dentro de cada
paquete se guardan los **componentes**, **servicios**, **guardas** e **interceptores**
relacionados con sus casos de uso.

> Numeración oficial: la **lista maestra de 40 CU** de `Contexto.md`. Ver trazabilidad
> completa CU ↔ componente ↔ endpoint en `Ciclo1.md` §6.1.

| Paquete | Subcarpetas / componentes | Casos de uso | Estado |
|---------|---------------------------|--------------|--------|
| `seguridad_y_usuarios/` | `login/`, `register/`, `recover/`, `usuarios_roles/`, `audit/`, `auth.service`, `auth.guard`, `auth.interceptor`, `users.service` | CU01, CU02, CU03, CU04, CU05, CU36 | Ciclo 1 ✅ |
| `catalogo_y_tiendas/` | `branches/`, `products/`, `employees/`, `store/` (store-home), `catalogo.service` | CU06, CU07, CU09, CU11 | Ciclo 1 ✅ |
| `inventario_y_proveedores/` | `suppliers/`, `merchandise/`, `valuation/` 🔜, `adjustments/` 🔜, `inventario.service` | CU08, CU10, **CU37**, **CU38** | Ciclo 1 ✅ (CU37/CU38 en curso) |
| `ventas_y_pagos/` | — | CU12–CU25 (carrito, checkout con herencia de pagos, POS, factura IVA 13 %, cotización, devoluciones, arqueo, historial) | Ciclo 2 🔜 |
| `reservas_y_citas/` | — | CU26, CU27, CU28 | Ciclo 3 🔜 |
| `envios_y_logistica/` | — | CU29, CU30, CU31 | Ciclo 3 🔜 |
| `inteligente_y_analitica/` | — | CU32, CU33, CU34, CU35, CU39 | Ciclo 3 🔜 |
| `notificaciones/` | — | CU40 | Ciclo 3 🔜 |

**Otros directorios fuera de `packages/`:** `dashboard/` es el panel de bienvenida del personal
(enrutado tras CU01); no es un paquete UML.

> **Nota:** las carpetas `audit/`, `reports/` sueltas dentro de `packages/` son restos de una
> estructura anterior en inglés y quedan **obsoletas**; el código vivo de auditoría está en
> `seguridad_y_usuarios/audit/`.
