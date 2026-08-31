# Estructura de Paquetes - Frontend Web (Angular)

Cada subdirectorio dentro de `packages/` corresponde a un paquete lógico del diagrama UML del sistema FashionStore.
Dentro de cada paquete se almacenan los **componentes**, **servicios** y **guardas** relacionados con sus respectivos casos de uso.

| Paquete | Casos de Uso | Estado |
|---------|-------------|--------|
| `security/` | CU01-CU05, CU36 | Ciclo 1 ✅ |
| `catalog/` | CU07 | Ciclo 1 ✅ |
| `branches/` | CU06, CU09 | Ciclo 1 ✅ |
| `suppliers/` | CU08 | Ciclo 1 ✅ |
| `merchandise/` | CU10 | Ciclo 1 ✅ |
| `sales/` | CU13-CU15 | Ciclo 2 🔜 |
| `reservations/` | CU11, CU12, CU26, CU27 | Ciclo 2 🔜 |
| `logistics/` | CU29, CU30 | Ciclo 3 🔜 |
| `ai_analytics/` | CU10_AR, CU19-CU23, CU33-CU35 | Ciclo 3 🔜 |
| `notifications/` | CU25 | Ciclo 2 🔜 |
