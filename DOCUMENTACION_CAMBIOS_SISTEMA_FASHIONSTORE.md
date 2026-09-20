# Documentación Técnica de Cambios Aplicados — FashionStore

**Grupo #29 — Sistemas de Información II (UAGRM - Semestre 2-2026)**  
**Proyecto:** Plataforma de Comercio Electrónico para Tienda de Ropa con Vestidor Virtual (RA)  
**Fecha:** 19 de Septiembre de 2026  
**Autores:** Condori Diaz & Larrazabal Rojas  
**Docente:** MSc. Ing. Angélica Garzón Cuéllar  

---

## 1. Resumen Ejecutivo

En cumplimiento estricto con los requerimientos planteados para el primer parcial y las observaciones de la auditoría de ingeniería de software, se ha efectuado una actualización integral en las tres capas del sistema (Backend FastAPI, Frontend Web Angular y Base de Datos PostgreSQL), orientada a:

1. **Purificación de la Estructura de Paquetes**: Garantizar que tanto en el código fuente (Backend, Web y Móvil) como en la documentación del sistema existan **única y exclusivamente los 8 paquetes lógicos del diseño UML**.
2. **Visualización Gráfica Interactiva en la Bitácora de Auditoría (CU36)**: Incorporación de 4 tarjetas KPI y 3 gráficas analíticas interactivas para análisis de accesos y mutaciones de datos.
3. **Reporte de Demanda Histórica y Decisión de Reposición por Prenda (CU35)**: Nuevo módulo analítico para evaluar la curva de ventas de cualquier prenda a lo largo del tiempo, calcular su velocidad de rotación y generar un dictamen gerencial cuantitativo de reorden a proveedores.
4. **Subsanación de Reglas de Negocio y Auditoría**:
   - Corrección matemática del Costo Promedio Ponderado (CPP) al completar transferencias inter-sucursal.
   - Incorporación de bloqueo pesimista (`with_for_update()`) en checkouts y reservas para evitar condiciones de carrera.
   - Segregación formal de estados de stock (`stock_reservado` y `stock_en_transito`).
   - Adición del modelo de entidad `Collection` (Colecciones de moda) en cumplimiento de RF05 / RF23.

---

## 2. Normalización de Paquetes (Alineación con `PaquetesUML.md`)

### 2.1 Los 8 Paquetes Oficiales del Sistema

De acuerdo a la especificación de `PaquetesUML.md`, el sistema se organiza en exactamente 8 subsistemas cohesivos:

```
├── 1. seguridad_y_usuarios       (CU01–CU05, CU36)
├── 2. catalogo_y_tiendas         (CU06, CU07, CU09, CU11–CU14)
├── 3. inventario_y_proveedores   (CU08, CU10, CU15, CU16, CU37, CU38)
├── 4. ventas_y_pagos             (CU17–CU25)
├── 5. reservas_y_citas           (CU26–CU28)
├── 6. envios_y_logistica         (CU29–CU31)
├── 7. inteligente_y_analitica    (CU32–CU35, CU39)
└── 8. notificaciones             (CU40)
```

### 2.2 Acciones de Reestructuración Ejecutadas

- **Frontend Web (`frontend-web/src/app/`)**:
  - Se detectó que el directorio `dashboard/` residía erróneamente dentro de `packages/`.
  - Como el propio `README.md` estipula (*"dashboard/ es el panel de bienvenida del personal; no es un paquete UML"*), se trasladó a `frontend-web/src/app/dashboard/`.
  - Se actualizaron todas las referencias de enrutamiento en `app-routing.module.ts`, `app.module.ts` y las importaciones relativas de servicios dentro de `dashboard.component.ts`.
  - **Estado actual**: `frontend-web/src/app/packages/` contiene exactamente los 8 directorios lógicos.
- **App Móvil Flutter (`mobile/lib/src/packages/`)**:
  - Se eliminaron las carpetas residuales vacías `audit/` y `reports/`.
  - **Estado actual**: `mobile/lib/src/packages/` contiene exactamente los 8 paquetes de diseño.
- **Backend FastAPI (`backend/app/packages/`)**:
  - Preserva la arquitectura 1:1 con los 8 sub-paquetes Python.

---

## 3. Bitácora de Auditoría con Visualizaciones Gráficas (CU36)

### 3.1 Ubicación
- **Frontend**: `frontend-web/src/app/packages/seguridad_y_usuarios/audit/`
- **Ruta**: `/admin/audit`
- **Backend**: `GET /api/v1/audit/logs`

### 3.2 Nuevos Componentes Visuales

1. **4 Tarjetas KPI Ejecutivas**:
   - **Total Eventos**: Recuento consolidado de transacciones auditadas.
   - **Seguridad & Accesos**: Eventos de autenticación (`LOGIN`, `LOGOUT`).
   - **Mutaciones DB**: Operaciones sobre registros (`INSERT`, `UPDATE`, `DELETE`).
   - **Operadores Activos**: Total de usuarios únicos con actividad registrada.
2. **Gráfica 1: Distribución por Tipo de Acción**:
   - Barras horizontales proporcionales con porcentaje, conteo, icono temático y código de color según severidad.
   - **Filtro al Clic**: Al pulsar sobre cualquier acción (ej: `DELETE`), la tabla de auditoría se filtra automáticamente.
3. **Gráfica 2: Top Módulos Afectados**:
   - Representación porcentual de las tablas más modificadas (`users`, `orders`, `inventory`, `products`, `branches`, etc.).
4. **Gráfica 3: Actividad Cronológica Reciente**:
   - Gráfico de barras temporales agrupado por fecha para detectar picos de actividad o accesos anómalos.
5. **Barra de Filtros Activos**:
   - Indicadores tipo píldora de los filtros aplicados con enlace de reseteo rápido.

---

## 4. Reporte de Demanda por Prenda y Decisión de Reposición (CU35)

### 4.1 Objetivo de Negocio
Permitir a la gerencia de Casa Matriz seleccionar cualquier prenda del catálogo, evaluar su curva de ventas histórica a lo largo del tiempo (3, 6 o 12 meses) y determinar con base en métricas objetivas **si conviene o es urgente realizar pedidos de reposición a proveedores**, así como la cantidad sugerida de unidades.

### 4.2 Especificación del Endpoint Backend

- **Ruta**: `GET /api/v1/analytics/reports/product-sales-trend`
- **Parámetros**:
  - `product_id` (int, requerido): ID de la prenda a analizar.
  - `months` (int, opcional, defecto 6): Ventana temporal hacia atrás.
- **Lógica Matemática**:
  - **Unidades Vendidas e Ingresos**: Suma agregada sobre `OrderItem` en órdenes `PAGADA`.
  - **Velocidad Semanal**:
    $$\text{Velocidad} = \frac{\text{Unidades Vendidas Totales}}{\text{Meses} \times 4.33}$$
  - **Días de Cobertura de Stock**:
    $$\text{Días de Stock} = \frac{\text{Stock Total en Sucursales}}{\text{Velocidad Semanal} / 7}$$
  - **Algoritmo de Dictamen Gerencial**:
    - **`URGENTE_REORDENAR`** ($\le 10$ días de cobertura con ventas activas): Semáforo Rojo.
    - **`CONVIENE_PEDIR`** ($11 - 25$ días de cobertura): Semáforo Amarillo.
    - **`STOCK_ADECUADO`** ($26 - 60$ días de cobertura): Semáforo Verde.
    - **`BAJA_ROTACION`** ($> 60$ días de cobertura o sin ventas): Semáforo Azul/Gris.
  - **Lote Sugerido de Reposición**:
    $$\text{Lote Sugerido} = \max(10, \lceil (\text{Velocidad Semanal} \times 4.33) - \text{Stock Actual} \rceil)$$

### 4.3 Vista Frontend Web (`/admin/reports` → Pestaña "Demanda y Pedidos por Prenda")
- Selector desplegable de prendas con buscador de texto en tiempo real.
- Botonera para conmutar rango (3 meses, 6 meses, 1 año).
- **Banner Ejecutivo de Semáforo**: Alerta de alto impacto con recomendación y lote sugerido.
- **4 Tarjetas KPI**: Stock Actual en Tiendas, Unidades Vendidas, Velocidad Semanal y Días de Cobertura.
- **Gráfica de Barras Cronológicas**: Comportamiento semanal/mensual con alturas proporcionales.
- **Existencias por Sucursal**: Cuadro de existencias en cada punto físico.
- **Tabla de Variantes (Talla y Color)**: Desglose por SKU con existencias, ventas y badge de acción recomendada (`Reponer`, `Bajo`, `OK`).

---

## 5. Subsanaciones de Negocio, Inventarios y Base de Datos

### 5.1 Recálculo de Costo Promedio Ponderado en Transferencias
- **Archivo**: `backend/app/packages/inventario_y_proveedores/merchandise/routers.py`
- **Corrección**: Al completar una transferencia inter-sucursal (`status == 'COMPLETADA'`), si la sucursal de destino ya tenía existencias, se recalcula el costo promedio ponderado en vez de únicamente sumar el stock escalar:
  ```python
  prev_stock = dest_inv.stock_actual
  prev_cost = float(dest_inv.avg_cost or 0.0)
  new_stock = prev_stock + d.quantity
  if new_stock > 0:
      dest_inv.avg_cost = round(((prev_stock * prev_cost) + (d.quantity * unit_cost)) / new_stock, 2)
  dest_inv.stock_actual = new_stock
  ```

### 5.2 Bloqueo Pesimista en Concurrencia Transaccional
- **Archivos**:
  - `backend/app/packages/ventas_y_pagos/routers.py` (Líneas 365, 417, 1095)
  - `backend/app/packages/reservas_y_citas/routers.py` (Línea 254)
- **Corrección**: Se incorporó `.with_for_update()` en las consultas de `Inventory` durante el checkout, la conversión de cotizaciones y la creación de reservas de probador. Esto bloquea a nivel de fila en PostgreSQL para evitar carreras que resulten en sobreventa o stock negativo.

### 5.3 Segregación de Estados de Stock
- **Archivo**: `backend/app/packages/inventario_y_proveedores/merchandise/models.py`
- **Campos incorporados**:
  - `stock_reservado`: Prendas apartadas para citas físicas de vestidor (CU26).
  - `stock_en_transito`: Mercadería en tránsito entre sucursales.
- **Migración registrada en `main.py`**:
  ```sql
  ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_reservado INT NOT NULL DEFAULT 0;
  ALTER TABLE inventory ADD COLUMN IF NOT EXISTS stock_en_transito INT NOT NULL DEFAULT 0;
  ```

### 5.4 Modelo `Collection` (Colecciones y Cápsulas de Moda)
- **Archivo**: `backend/app/packages/catalogo_y_tiendas/models.py`
- **Requisito Cátedra**: RF05 / RF23 ("temporadas y colecciones").
- **Estructura**:
  ```python
  class Collection(Base):
      __tablename__ = "collections"
      id: Mapped[int] = mapped_column(primary_key=True)
      name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
      description: Mapped[Optional[str]] = mapped_column(String(255))
      season_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True)
      is_active: Mapped[bool] = mapped_column(Boolean, default=True)
      banner_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
  ```
- **Relación**: `Product.collection_id` vinculado con `ON DELETE SET NULL`.
- **Migración registrada en `main.py`**:
  ```sql
  ALTER TABLE products ADD COLUMN IF NOT EXISTS collection_id INTEGER REFERENCES collections(id) ON DELETE SET NULL;
  ```

---

## 6. Validación Técnica y Compilación

| Capa / Módulo | Comando de Validación | Resultado |
|:---|:---|:---:|
| **Backend (Python)** | `python -m py_compile backend/app/main.py ...` | **Exitoso (Code 0)** |
| **Frontend Web (Angular)** | `npx ng build --configuration development` | **Exitoso (Code 0)** |
| **Trazabilidad de Paquetes** | Inspección de `backend/`, `frontend-web/` y `mobile/` | **8 paquetes exactos en todas las capas** |

---

## 7. Conclusión

Con estas adecuaciones, la plataforma **FashionStore** perfecciona su correspondencia arquitectónica con el diseño UML, enriquece sustancialmente la experiencia analítica para la toma de decisiones de inventario y compras, y eleva la robustez contable y transaccional del sistema a los estándares más exigentes de la cátedra de Sistemas de Información II.
