# FashionStore · Frontend Web (Angular 16)

Panel administrativo del Ciclo 1. Consume la API FastAPI.

## Puesta en marcha

```bash
cd frontend-web
npm install
ng serve
```

Abrir http://localhost:4200 → redirige a `/login`.
Inicia sesión con el admin sembrado en el backend (`admin@fashionstore.com` / `Admin123!`).

## Configuración

- **URL del backend:** `src/environments/environment.ts` (`apiUrl`).
- **Estilos:** Bootstrap 5 + bootstrap-icons (en `angular.json`) + tema terracota en `src/styles.css`.

## Estructura (por paquetes UML)

```
src/app/packages/
├── seguridad_y_usuarios/   # login, register, recover, usuarios_roles, audit,
│                           # auth.service, auth.guard, auth.interceptor, users.service
├── catalogo_y_tiendas/     # branches, products, employees, catalogo.service
├── inventario_y_proveedores/ # suppliers, merchandise, inventario.service
└── dashboard/
```

## Casos de uso

CU01 (login), CU02 (logout), CU03 (recuperación), CU04 (registro), CU05 (usuarios y
roles), CU06 (sucursales), CU07 (catálogo), CU08 (proveedores), CU09 (empleados),
CU10 (mercadería), CU36 (auditoría).
