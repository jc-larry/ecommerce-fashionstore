# Diseño Físico de Base de Datos (PostgreSQL)

Este documento detalla el diseño de la base de datos relacional para la plataforma **FashionStore** utilizando **PostgreSQL** (gestionado mediante **pgAdmin 4**). El diseño se ha estructurado siguiendo estrictamente las formas normales (**1NF, 2NF y 3NF**) y aplicando las mejores prácticas de la industria en cuanto a integridad referencial, tipos de datos óptimos e indexación para soportar de manera concurrente tanto a la aplicación móvil como a la plataforma web.

---

## 1. Validación de Normas Normales (Normalización)

Para garantizar la consistencia, evitar redundancias y prevenir anomalías de inserción, actualización y borrado, el esquema físico se normalizó a la **Tercera Forma Normal (3NF)**:

* **Primera Forma Normal (1NF)**: Todos los atributos contienen valores atómicos y no existen grupos repetitivos. 
  * *Ejemplo*: Las tallas y colores de las prendas no se guardan como cadenas o arreglos separados por comas dentro de la tabla de productos, sino como entidades individuales en sus respectivas tablas (`sizes`, `colors`).
* **Segunda Forma Normal (2NF)**: Está en 1NF y todos los atributos no clave dependen de forma completa de la clave primaria (no hay dependencias parciales).
  * *Ejemplo*: El stock real no se almacena en la tabla de productos ni de variantes, sino en la tabla intermedia `inventory` vinculada a una sucursal (`branch_id`) y a una variante (`variant_id`). Esto separa las existencias físicas del catálogo base.
* **Tercera Forma Normal (3NF)**: Está en 2NF y no existen dependencias transitivas (ningún atributo no clave depende de otro atributo no clave; todos dependen únicamente de la clave primaria).
  * *Ejemplo*: Los datos de las sucursales (`branch_name`, `address`) y los datos de los empleados se almacenan por separado. La asociación se realiza mediante una tabla intermedia `branch_employees`, evitando repetir la dirección de la sucursal en cada registro de empleado.

---

## 2. Esquema Físico de Tablas (DDL)

A continuación se definen las tablas agrupadas por sus respectivos paquetes del sistema.

### 2.1 Paquete de Seguridad y Usuarios (Security & Access Control) — *(Ciclo 1)*

#### Tabla: `roles`
Almacena los perfiles de usuario autorizados.
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL, -- 'SUPERADMIN', 'ENCARGADO', 'CAJERO', 'CLIENTE'
    description VARCHAR(255)
);
```

#### Tabla: `users`
Almacena la información de autenticación y datos básicos de clientes y personal.
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
```

#### Tabla: `user_roles`
Tabla intermedia para la relación N:N entre usuarios y roles.
```sql
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);
```

#### Tabla: `session_tokens`
Tokens JWT activos y revocados para control de sesiones concurrentes.
```sql
CREATE TABLE session_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `audit_logs` (Bitácora Auditora)
Almacena el rastro de auditoría de todas las escrituras críticas en el sistema.
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER, -- NULL si es un trigger del sistema
    action VARCHAR(50) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
    table_name VARCHAR(100) NOT NULL,
    row_id INTEGER NOT NULL,
    old_values JSONB, -- Valores previos a la modificación
    new_values JSONB, -- Nuevos valores insertados/modificados
    ip_address VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

---

### 2.2 Paquete de Catálogo y Tiendas (Catalog & Branch Management) — *(Ciclo 1)*

#### Tabla: `branches`
Sucursales físicas de la cadena.
```sql
CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);
```

#### Tabla: `branch_employees`
Asociación del personal administrativo (encargados y cajeros) a sus sucursales correspondientes.
```sql
CREATE TABLE branch_employees (
    branch_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (branch_id, user_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Tabla: `categories`
Categorías de prendas (ej. Camisas, Pantalones, Vestidos).
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255)
);
```

#### Tabla: `seasons`
Temporadas comerciales.
```sql
CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL, -- 'PRIMAVERA 2026', 'INVIERNO 2026'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);
```

#### Tabla: `colors`
Catálogo estructurado de colores.
```sql
CREATE TABLE colors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    hex_code VARCHAR(7) UNIQUE NOT NULL -- ej. '#FF5733'
);
```

#### Tabla: `sizes`
Catálogo estructurado de tallas.
```sql
CREATE TABLE sizes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL -- 'S', 'M', 'L', 'XL'
);
```

#### Tabla: `products`
Ficha técnica base de las prendas.
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL,
    category_id INTEGER NOT NULL,
    season_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE SET NULL
);
```

#### Tabla: `product_variants`
Variantes físicas por combinación única de Producto, Color y Talla (Soporta SKU único).
```sql
CREATE TABLE product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color_id INTEGER NOT NULL,
    size_id INTEGER NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price_override DECIMAL(10, 2), -- Precio específico de variante si aplica
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE RESTRICT,
    FOREIGN KEY (size_id) REFERENCES sizes(id) ON DELETE RESTRICT,
    CONSTRAINT unique_product_color_size UNIQUE (product_id, color_id, size_id)
);
```

#### Tabla: `product_images`
Fotografías asociadas a variantes de color del producto.
```sql
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    color_id INTEGER NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE RESTRICT
);
```

---

### 2.3 Paquete de Inventario y Proveedores (Inventory & Supply Management) — *(Ciclo 1)*

#### Tabla: `suppliers`
Proveedores de indumentaria.
```sql
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    nit VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    address VARCHAR(255)
);
```

#### Tabla: `inventory`  *(Ciclo 1)*
Stock físico real, **costo promedio ponderado vigente** y límites mínimos/máximos estructurados
por Sucursal y Variante de Producto.
```sql
CREATE TABLE inventory (
    branch_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    stock_actual INTEGER DEFAULT 0 NOT NULL,
    avg_cost DECIMAL(10, 2) DEFAULT 0 NOT NULL, -- Costo promedio ponderado vigente (CU10 / CU37)
    stock_minimo INTEGER DEFAULT 5 NOT NULL,
    stock_maximo INTEGER DEFAULT 100 NOT NULL,
    PRIMARY KEY (branch_id, variant_id),
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);
```

> **Costo promedio ponderado (CU10, CU37, CU38).** Cada **ingreso** (CU10) recalcula:
> `avg_cost = (stock_previo · avg_previo + cantidad · costo_unitario_lote) / (stock_previo + cantidad)`.
> Las **salidas** (venta, reserva, ajuste) **no** modifican `avg_cost`; se valoran al `avg_cost`
> vigente y así se registra su `unit_cost` en `inventory_ledger`.
> **CU37** — capital invertido = `Σ (inventory.stock_actual · inventory.avg_cost)` (global o por
> sucursal). Nunca se usa el último costo unitario.
> **CU38** — un ajuste (merma/daño/pérdida/conteo) escribe un movimiento `AJUSTE` en
> `inventory_ledger` con `unit_cost = avg_cost` vigente y `reference_id = 'AJU-<id>'`.

#### Tabla: `inventory_ledger` (Libro Mayor de Inventario)
Historial y movimientos físicos valorados por Promedio Ponderado.
```sql
CREATE TABLE inventory_ledger (
    id BIGSERIAL PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL, -- Positivo para ingresos, negativo para salidas
    movement_type VARCHAR(20) NOT NULL, -- 'INGRESO', 'VENTA', 'RESERVA', 'AJUSTE', 'TRANSFERENCIA'
    unit_cost DECIMAL(10, 2) NOT NULL, -- Costo de compra o costo promedio al momento de la salida
    reference_id VARCHAR(50), -- ID de Orden de Compra o Venta relacionada
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);
```

#### Tabla: `purchase_orders` (Órdenes de compra / Ingresos de mercadería)
Cabecera del ingreso de mercadería recibido de un proveedor en una sucursal (CU10).
```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'COMPLETADO' NOT NULL, -- 'COMPLETADO', 'CANCELADO'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);
```

#### Tabla: `purchase_details`
Detalle de cada variante recibida en una orden de compra, con su costo unitario.
```sql
CREATE TABLE purchase_details (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

---

### 2.4 Paquete de Ventas y Pagos (Sales & POS/Payment Management)

> **Estado:** las tablas `payments` e `invoices` se crean ya en el **Ciclo 1** como modelos
> SQLAlchemy (respaldo del diagrama de clases del análisis: jerarquías `MedioDePago` y
> `Comprobante`), **sin routers** todavía. `orders` / `order_items` y el resto se activan en el
> **Ciclo 2**.

#### Tabla: `orders`  *(modelo, Ciclo 2)*
Cabecera de pedidos web/móvil y caja POS.
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL, -- Cliente o Anónimo en POS
    branch_id INTEGER NOT NULL, -- Sucursal donde se procesa
    channel VARCHAR(10) DEFAULT 'ONLINE' NOT NULL, -- 'ONLINE', 'POS' (tienda física)
    status VARCHAR(20) DEFAULT 'PENDIENTE' NOT NULL, -- 'PENDIENTE', 'PAGADO', 'COMPLETADO', 'CANCELADO'
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);
```

#### Tabla: `order_items`  *(modelo, Ciclo 2)*
Detalle de las prendas vendidas.
```sql
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

#### Tabla: `payments`  *(modelo, Ciclo 1)* — herencia de tabla única (STI)
Medios de pago modelados por **generalización**: `MedioDePago` ⭅ `Efectivo` / `Tarjeta` / `QR` /
`Crédito`. El discriminador es `payment_type`; las columnas específicas de cada subtipo son
anulables (solo se llenan según el tipo).
```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    payment_type VARCHAR(20) NOT NULL, -- 'EFECTIVO', 'TARJETA', 'QR', 'CREDITO' (discriminador)
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'CONFIRMADO' NOT NULL, -- 'PENDIENTE', 'CONFIRMADO', 'RECHAZADO'
    paid_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    -- Efectivo:
    cash_received DECIMAL(10, 2),      -- monto entregado por el cliente
    cash_change DECIMAL(10, 2),        -- vuelto
    -- Tarjeta:
    card_brand VARCHAR(20),
    card_last4 VARCHAR(4),
    gateway_reference VARCHAR(80),     -- token no reutilizable (Stripe)
    -- QR:
    qr_reference VARCHAR(80),
    -- Crédito:
    credit_due_date DATE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);
```

#### Tabla: `invoices`  *(modelo, Ciclo 1)* — herencia `Comprobante` ⭅ `Factura` / `NotaDeEntrega`
```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE,
    doc_type VARCHAR(15) NOT NULL, -- 'FACTURA', 'NOTA_ENTREGA'
    tax_rate DECIMAL(4, 3) DEFAULT 0.130 NOT NULL, -- IVA 13 %
    subtotal DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    control_code VARCHAR(40),          -- código de control (solo FACTURA)
    customer_nit VARCHAR(20),
    customer_name VARCHAR(150),
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT
);
```

> Otras tablas del paquete (Ciclo 2, aún no modeladas): `cash_sessions` (arqueo de caja, CU23),
> `credit_notes` (devoluciones y cambios, CU22), `quotes` (cotización, CU21),
> `coupons` (CU13, en `catalogo_y_tiendas`).

---

### 2.5 Paquete de Reservas (Reservations & Appointments) — *(modelo, Ciclo 3)*

#### Tabla: `reservations`
Reservas físicas programadas en tienda para pruebas.
```sql
CREATE TABLE reservations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDIENTE' NOT NULL, -- 'PENDIENTE', 'PREPARADA', 'COMPLETADA', 'CANCELADA'
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Bloqueo de stock temporal
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT
);
```

#### Tabla: `reservation_items`
Detalle de prendas a probarse.
```sql
CREATE TABLE reservation_items (
    id SERIAL PRIMARY KEY,
    reservation_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1 NOT NULL,
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT
);
```

---

## 3. Índices de Rendimiento (Buenas Prácticas)

Para garantizar respuestas ultrarrápidas en la aplicación móvil y el panel web administrativo, se añaden los siguientes índices de base de datos estratégicos en PostgreSQL:

1. **Búsquedas de Catálogo**: Índice compuesto para acelerar el filtrado de variantes por color y talla.
   ```sql
   CREATE INDEX idx_variants_search ON product_variants(product_id, color_id, size_id);
   ```
2. **Control de Stock**: Acelera la validación de inventario antes del checkout y las alertas de stock mínimo.
   ```sql
   CREATE INDEX idx_inventory_stock ON inventory(branch_id, variant_id) INCLUDE (stock_actual);
   ```
3. **Autenticación**: Búsqueda inmediata de usuarios por correo electrónico.
   ```sql
   CREATE INDEX idx_users_email ON users(email) WHERE is_active = TRUE;
   ```
4. **Historial de Auditoría (Bitácora)**: Búsquedas eficientes de logs por fecha e IP.
   ```sql
   CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
   ```
