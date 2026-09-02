# Paquetes del Sistema — App Móvil (Flutter)

Cada subdirectorio corresponde a uno de los **8 paquetes lógicos** del diagrama UML de
FashionStore (mismos nombres en español que el backend y el frontend web).

> Numeración oficial: la **lista maestra de 40 CU** de `Contexto.md`.
> En el **Ciclo 1** el móvil es exclusivo del **cliente final**: solo cubre CU01–CU04 y CU11.

| Paquete | Casos de uso | Alcance móvil Ciclo 1 | Estado |
|---------|--------------|-----------------------|--------|
| `seguridad_y_usuarios/` | CU01, CU02, CU03, CU04, CU05, CU36 | CU01–CU04 (login, registro, recuperación) | Ciclo 1 ✅ |
| `catalogo_y_tiendas/` | CU06, CU07, CU09, CU11, CU12–CU14 | CU11 (consultar catálogo, solo lectura) | Ciclo 1 ✅ (CU11) |
| `inventario_y_proveedores/` | CU08, CU10, CU37, CU38, CU15, CU16 | — (solo web) | Ciclo 1 (web) |
| `ventas_y_pagos/` | CU17–CU25 | carrito y checkout móvil | Ciclo 2 🔜 |
| `reservas_y_citas/` | CU26, CU27, CU28 | reservar desde el móvil | Ciclo 3 🔜 |
| `envios_y_logistica/` | CU29, CU30, CU31 | rastreo de pedido | Ciclo 3 🔜 |
| `inteligente_y_analitica/` | CU32, CU33, CU34, CU35, CU39 | vestidor virtual RA, voz | Ciclo 3 🔜 |
| `notificaciones/` | CU40 | push al cliente | Ciclo 3 🔜 |
