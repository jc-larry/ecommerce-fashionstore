# Especificación de Casos de Uso — Ciclo 1 (FashionStore)

Este documento especifica, en formato formal, los casos de uso implementados en el
**Ciclo 1**: autenticación y usuarios, catálogo y sucursales, proveedores e ingreso de
mercadería, consulta de catálogo del cliente y bitácora de auditoría. Los nombres de
tablas y roles coinciden con `BaseDeDatos.md` y con el código implementado.

---

## 1. Actores del Ciclo 1

| # | Actor | Tipo | Interviene en |
| :-- | :--- | :--- | :--- |
| 1 | **Visitante** (usuario anónimo, no autenticado) | Humano primario | CU11 |
| 2 | **Cliente** (rol `CLIENTE`) | Humano primario | CU01, CU02, CU03, CU04, CU11 |
| 3 | **Superadmin** (rol `SUPERADMIN`) | Humano primario | CU01, CU02, CU05, CU06, CU07, CU08, CU09, CU10, CU36 |
| 4 | **Encargado de sucursal** (rol `ENCARGADO`) | Humano primario | CU01, CU02, CU10 |
| 5 | **Cajero** (rol `CAJERO`) | Humano primario | CU01, CU02 |
| 6 | **Proveedor** | Humano de apoyo | Entidad registrada por el personal (CU08) y referenciada en CU10; no inicia sesión en el Ciclo 1 |
| 7 | **Servicio de correo (SMTP)** | Sistema externo | CU03 (entrega del enlace de recuperación) |
| 8 | **Reloj del sistema / Temporizador** | Actor "Tiempo" | CU02 (expiración del JWT y del token de recuperación, cierre por inactividad) |

> **Separación cliente / personal:** el auto-registro (CU04) **siempre** crea el rol
> `CLIENTE`; el formulario no permite elegir rol y el backend lo fuerza. Las cuentas de
> personal (`SUPERADMIN`, `ENCARGADO`, `CAJERO`) solo las crea un `SUPERADMIN` desde
> CU05. Es el esquema estándar de seguridad de un e-commerce: nadie se auto-registra
> como administrador.

## 2. Matriz Actor ↔ Caso de uso (Ciclo 1)

| Caso de uso | Visitante | Cliente | Superadmin | Encargado | Cajero |
| :--- | :---: | :---: | :---: | :---: | :---: |
| CU01 Iniciar sesión | | ✅ | ✅ | ✅ | ✅ |
| CU02 Cerrar sesión | | ✅ | ✅ | ✅ | ✅ |
| CU03 Recuperar credenciales | ✅¹ | ✅¹ | ✅¹ | ✅¹ | ✅¹ |
| CU04 Auto-registro de cliente | ✅ | | | | |
| CU05 Gestionar perfiles y roles | | | ✅ | | |
| CU06 Gestionar sucursales | | | ✅ | | |
| CU07 Gestionar catálogo | | | ✅ | | |
| CU08 Gestionar proveedores | | | ✅ | | |
| CU09 Gestionar empleados | | | ✅ | | |
| CU10 Registrar ingresos de mercadería | | | ✅ | ✅ | |
| CU11 Consultar catálogo | ✅ | ✅ | ✅ | ✅ | ✅ |
| CU36 Consultar bitácora de auditoría | | | ✅ | | |

¹ CU03 siempre lo inicia un **usuario no autenticado** (olvidó su contraseña), sin
importar el rol de esa cuenta.

---

## 3. Especificación de los casos de uso

### CU01: Iniciar sesión [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU01 : Iniciar sesión |
| **Propósito** | Restringir y asegurar el acceso a la plataforma (Web / Móvil), autenticando la identidad del usuario. |
| **Descripción** | Un usuario registrado (Cliente o personal administrativo) ingresa sus credenciales; el sistema le asigna un token de sesión (JWT) y lo enruta según su rol: el personal al panel administrativo y el cliente a la tienda. |
| **Actores** | Cliente, Superadmin, Encargado, Cajero. |
| **Actor iniciador** | Usuario no autenticado (Cliente o empleado). |
| **Tablas** | `users`, `roles`, `user_roles`, `session_tokens`, `audit_logs` |
| **Precondición** | El usuario está registrado y su estado lógico es "Activo" (`is_active = true`). |
| **Flujo principal** | 1. El actor abre la app móvil o el sitio web.<br>2. El sistema muestra el formulario de inicio de sesión.<br>3. El actor introduce Correo y Contraseña y envía la petición.<br>4. El sistema verifica que el usuario exista y compara el hash de la contraseña (BCrypt).<br>5. El sistema genera un JWT único (con `jti` e `iat`) y expiración de 60 min, y guarda la sesión en `session_tokens`.<br>6. El sistema registra la acción `LOGIN` en `audit_logs` (usuario, IP).<br>7. El sistema devuelve el token y los roles; el frontend enruta: personal → `/admin/dashboard`, cliente → `/tienda`. |
| **Post condición** | El usuario queda autenticado hasta que expire o se revoque su JWT. El ingreso queda registrado en la bitácora. |
| **Excepciones** | **E1: Credenciales inválidas** (falla el paso 4): el sistema detiene el flujo y notifica "Correo electrónico o contraseña incorrectos".<br>**E2: Usuario inactivo** (falla la precondición): el sistema notifica "Cuenta de usuario desactivada" e impide el acceso.<br>**E3: Sin conexión con el servidor:** el cliente muestra "No se pudo conectar con el servidor". |

---

### CU02: Cerrar sesión [Prioridad: Media]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU02 : Cerrar sesión |
| **Propósito** | Finalizar de forma segura la sesión activa de un usuario en su dispositivo. |
| **Descripción** | El usuario invalida su token de acceso actual para que nadie pueda operar a su nombre en ese dispositivo. También lo dispara el sistema por vencimiento o inactividad. |
| **Actores** | Cualquier usuario autenticado; Reloj del sistema (cierre automático). |
| **Actor iniciador** | Usuario autenticado (o el Temporizador del sistema). |
| **Tablas** | `session_tokens`, `audit_logs` |
| **Precondición** | El usuario tiene una sesión abierta con un JWT válido. |
| **Flujo principal** | 1. El actor pulsa "Cerrar sesión" (en **web**: sidebar del panel o menú del header de la tienda; en **móvil**: menú de la barra superior del catálogo).<br>2. El sistema pide confirmación.<br>3. El sistema envía el token actual al servidor.<br>4. El sistema marca el registro del token como revocado (`is_revoked = true`).<br>5. El sistema registra `LOGOUT` en `audit_logs`.<br>6. El sistema borra las credenciales del almacenamiento local y redirige al login. |
| **Post condición** | La sesión queda invalidada; todo intento futuro de usar el mismo JWT se rechaza (HTTP 401). |
| **Excepciones** | **E1: Token ya expirado o inválido:** el sistema solo limpia los datos locales y redirige al login.<br>**E2: Cierre automático:** al vencer el JWT (60 min) o tras 15 min de inactividad, el sistema revoca la sesión y obliga a iniciar sesión de nuevo. |

---

### CU03: Recuperar credenciales [Prioridad: Media]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU03 : Recuperar credenciales |
| **Propósito** | Permitir que un usuario restablezca su contraseña cuando la olvidó. |
| **Descripción** | El usuario solicita el restablecimiento con su correo; el sistema genera un token temporal y le envía **un enlace por correo electrónico**. La pantalla de "nueva contraseña" **solo se abre al tocar ese enlace** (con el token ya incluido en la URL) — **nunca se pide un token/código a mano**. El enlace vence a los 5 minutos y es de un solo uso. Se hace así por seguridad: un código dictado por teléfono puede ser robado por ingeniería social; un enlace solo funciona desde el buzón del propio usuario. |
| **Actores** | Usuario no autenticado; Servicio de correo (SMTP). |
| **Actor iniciador** | Usuario no autenticado. |
| **Tablas** | `users` (`reset_token`, `reset_token_expires`), `audit_logs` |
| **Precondición** | El usuario conoce el correo con el que se registró. |
| **Flujo principal** | 1. El actor entra a "¿Olvidaste tu contraseña?" e ingresa su correo.<br>2. El sistema genera un token único con vencimiento de 5 minutos y envía por SMTP un correo con el enlace `<FRONTEND_URL>/recover?token=…`.<br>3. El sistema muestra **solo** la confirmación *"Si el correo está registrado, te llegó un enlace. Revísalo. Vence en 5 minutos."* — sin ningún campo de token ni contraseña.<br>4. El actor abre el enlace desde su bandeja de entrada.<br>5. El enlace abre la página web "Nueva contraseña" **con el token ya aplicado** (oculto); el actor solo escribe y confirma la nueva contraseña.<br>6. El sistema valida el token y su vigencia, actualiza el hash de la contraseña y anula el token.<br>7. El sistema registra `RECOVER` / `RESET_PASSWORD` en `audit_logs` y redirige al inicio de sesión. |
| **Post condición** | La contraseña queda modificada y el token temporal queda inservible. |
| **Nota móvil** | En la app, el paso 1 llega hasta la confirmación "revisa tu correo". El restablecimiento (paso 5) se realiza en la **página web** que abre el enlace (responsiva); la app no tiene pantalla de "pegar token". |
| **Excepciones** | **E1: Correo no registrado:** por seguridad el sistema no revela si el correo existe; responde siempre el mensaje neutro.<br>**E2: Token expirado o ya usado** (falla el paso 6): el sistema alerta "El enlace es inválido o expiró (5 minutos)" y obliga a solicitar uno nuevo.<br>**E3: SMTP no disponible:** el token igualmente se genera; en desarrollo el enlace se registra en la consola del servidor. |

---

### CU04: Auto-registro de cliente [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU04 : Auto-registro de cliente |
| **Propósito** | Permitir que una persona cree su propia cuenta de cliente, desde la app móvil o el sitio web. |
| **Descripción** | El visitante ingresa sus datos básicos; el sistema crea el usuario y le asigna automáticamente el rol `CLIENTE`. No es posible elegir otro rol. |
| **Actores** | Visitante (usuario nuevo). |
| **Actor iniciador** | Usuario no registrado (app móvil o sitio web). |
| **Tablas** | `users`, `roles`, `user_roles`, `audit_logs` |
| **Precondición** | El correo ingresado no está registrado previamente. |
| **Flujo principal** | 1. El actor entra a "Crear cuenta" en la app o en la web.<br>2. El sistema muestra el formulario (Nombres, Apellidos, Teléfono, Correo, Contraseña).<br>3. El actor completa el formulario, acepta los términos y envía.<br>4. El sistema valida el formato del correo y que no exista.<br>5. El sistema valida la fortaleza de la contraseña (≥8, mayúscula, minúscula, número, carácter especial).<br>6. El sistema encripta la contraseña (BCrypt), crea el usuario y le asigna el rol `CLIENTE`.<br>7. El sistema registra `REGISTER` en `audit_logs` y notifica el éxito.<br>8. El actor inicia sesión (CU01) y accede a la tienda. |
| **Post condición** | Se crea un usuario activo con rol `CLIENTE`. |
| **Excepciones** | **E1: Correo duplicado** (falla el paso 4): "El correo electrónico ya se encuentra registrado".<br>**E2: Contraseña débil** (falla el paso 5): el sistema indica los requisitos incumplidos.<br>**E3: Contraseñas no coinciden:** el sistema lo advierte antes de enviar. |

---

### CU05: Gestionar perfiles y roles [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU05 : Gestionar perfiles y roles |
| **Propósito** | Administrar las cuentas del personal interno y asignarles permisos mediante roles. |
| **Descripción** | El Superadmin crea cuentas para el personal (`ENCARGADO`, `CAJERO`) o para otros administradores, edita sus datos y roles, y los da de baja lógicamente. |
| **Actores** | Superadmin. |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `users`, `roles`, `user_roles`, `audit_logs` |
| **Precondición** | El iniciador está autenticado con el rol `SUPERADMIN`. |
| **Flujo principal** | 1. El Superadmin entra al módulo "Usuarios y Roles".<br>2. El sistema muestra el listado de usuarios (con filtro por rol y búsqueda).<br>3. El Superadmin pulsa "Nuevo Usuario" y completa el formulario, marcando uno o más roles.<br>4. El sistema valida el correo, encripta la contraseña, crea el usuario y le asigna los roles.<br>5. El sistema registra `INSERT` (o `UPDATE` / desactivación) en `audit_logs`.<br>6. El sistema actualiza el listado. |
| **Post condición** | Se crea, edita o desactiva la cuenta del personal solicitada. |
| **Excepciones** | **E1: Correo existente:** el sistema informa "El correo electrónico ya existe".<br>**E2: Falta de permisos:** si un usuario sin rol `SUPERADMIN` intenta acceder a esta ruta, el sistema devuelve **HTTP 403** ("No tiene permisos suficientes"). |

---

### CU06: Gestionar sucursales [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU06 : Gestionar sucursales |
| **Propósito** | Mantener el registro de las tiendas físicas de la cadena y su personal asignado. |
| **Descripción** | El Superadmin registra nuevas sucursales (nombre, dirección, teléfono, coordenadas, estado), las edita, las desactiva y asigna o retira empleados (`ENCARGADO` / `CAJERO`) de cada una. |
| **Actores** | Superadmin. |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `branches`, `branch_employees`, `users`, `audit_logs` |
| **Precondición** | El Superadmin está autenticado. |
| **Flujo principal** | 1. El actor entra al módulo "Sucursales" y ve las tarjetas de las sucursales.<br>2. El actor pulsa "Nueva Sucursal" e ingresa nombre, dirección, teléfono y coordenadas.<br>3. El sistema valida que el nombre no exista y guarda la sucursal.<br>4. El actor asigna un `ENCARGADO` o `CAJERO` existente a la sucursal.<br>5. El sistema valida que el usuario tenga rol `ENCARGADO` o `CAJERO` y lo vincula en `branch_employees`.<br>6. El sistema registra la operación en `audit_logs`. |
| **Post condición** | La cadena cuenta con la sucursal registrada y su personal asignado, lista para recibir inventario. |
| **Excepciones** | **E1: Nombre de sucursal duplicado:** el sistema lo rechaza.<br>**E2: Datos obligatorios faltantes:** el sistema rechaza el formulario si falta el nombre o la dirección.<br>**E3: Empleado con rol inválido:** solo se pueden asignar usuarios con rol `ENCARGADO` o `CAJERO`. |

---

### CU07: Gestionar catálogo [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU07 : Gestionar catálogo |
| **Propósito** | Administrar las prendas, sus parámetros (categorías, tallas, colores, temporadas) y sus variantes (color + talla + SKU). |
| **Descripción** | El Superadmin parametriza el catálogo y da de alta, edita u oculta prendas, definiendo por cada una su categoría, temporada, precio base y sus variantes. |
| **Actores** | Superadmin. *(En ciclos posteriores se prevé habilitar también al Encargado.)* |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `products`, `product_variants`, `product_images`, `categories`, `seasons`, `colors`, `sizes`, `audit_logs` |
| **Precondición** | Deben existir al menos una categoría, una talla y un color parametrizados. |
| **Flujo principal** | 1. El actor entra al módulo "Catálogo".<br>2. El actor agrega, si hace falta, categorías, tallas, colores o temporadas (alta rápida).<br>3. El actor pulsa "Nueva Prenda" e ingresa nombre, descripción, precio base, categoría y temporada.<br>4. El actor define una o más variantes (color + talla + SKU).<br>5. El sistema valida los SKU y la unicidad de la combinación producto+color+talla, y guarda la estructura Prenda → Variantes.<br>6. El sistema registra `INSERT` en `audit_logs`.<br>7. El actor puede editar la prenda u **ocultarla** del catálogo (baja lógica, `is_active = false`). |
| **Post condición** | La prenda queda creada, modificada u oculta; si está visible aparecerá en la tienda del cliente (CU11) y podrá abastecerse (CU10). |
| **Excepciones** | **E1: SKU o combinación color/talla repetida:** el sistema rechaza la variante.<br>**E2: Falta de permisos:** HTTP 403 si el rol no es `SUPERADMIN`. |

---

### CU08: Gestionar proveedores [Prioridad: Media]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU08 : Gestionar proveedores |
| **Propósito** | Mantener el directorio de proveedores (fabricantes o distribuidores) que abastecen ropa a la cadena. |
| **Descripción** | El Superadmin registra, edita y elimina proveedores (NIT, nombre, contacto, teléfono, correo, dirección) para usarlos en los ingresos de mercadería. |
| **Actores** | Superadmin. |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `suppliers`, `audit_logs` |
| **Precondición** | Estar autenticado con el rol `SUPERADMIN`. |
| **Flujo principal** | 1. El actor entra al módulo "Proveedores" y ve el listado (con búsqueda).<br>2. El actor pulsa "Nuevo Proveedor" y completa NIT, nombre y datos de contacto.<br>3. El sistema valida que el NIT no exista y registra el proveedor.<br>4. El sistema registra `INSERT` en `audit_logs` y actualiza la lista.<br>5. El actor puede editar o eliminar un proveedor. |
| **Post condición** | El proveedor queda disponible para seleccionarse en los ingresos de mercadería (CU10). |
| **Excepciones** | **E1: NIT duplicado:** "El NIT del proveedor ya se encuentra registrado".<br>**E2: Falta de permisos:** HTTP 403 si el rol no es `SUPERADMIN`. |

---

### CU09: Gestionar empleados [Prioridad: Media]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU09 : Gestionar empleados de sucursal |
| **Propósito** | Dar de alta al personal de tienda (encargados y cajeros) y asignarlo a una sucursal. |
| **Descripción** | Un empleado es un **usuario con rol `ENCARGADO` o `CAJERO`** vinculado a una sucursal. Este caso de uso combina la creación de la cuenta (CU05) con la asignación a una sucursal (CU06): el Superadmin registra al empleado con su rol y su sucursal en un solo paso, y puede desactivarlo. |
| **Actores** | Superadmin. |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `users`, `roles`, `user_roles`, `branch_employees`, `branches`, `audit_logs` |
| **Precondición** | Debe existir al menos una sucursal (CU06). |
| **Flujo principal** | 1. El actor entra al módulo "Empleados"; el sistema lista los usuarios con rol `ENCARGADO`/`CAJERO` y su sucursal asignada.<br>2. El actor pulsa "Nuevo Empleado" e ingresa nombre, correo, teléfono, contraseña temporal, rol (`ENCARGADO` o `CAJERO`) y sucursal.<br>3. El sistema crea el usuario con ese rol (CU05).<br>4. El sistema lo asigna a la sucursal elegida en `branch_employees` (CU06).<br>5. El sistema registra la operación en `audit_logs` y actualiza el listado.<br>6. El actor puede desactivar a un empleado (baja lógica del usuario). |
| **Post condición** | El empleado queda registrado con su rol y asignado a trabajar en la sucursal indicada. |
| **Excepciones** | **E1: Correo existente:** el sistema informa "El correo electrónico ya existe" y no crea la cuenta.<br>**E2: Empleado ya asignado a esa sucursal:** el sistema lo advierte.<br>**E3: Falta de permisos:** HTTP 403 si el rol no es `SUPERADMIN`. |

> **Nota:** el Ciclo 1 no registra datos de contratación (cargo, salario, horario, fecha
> de ingreso). Si se requirieran, se añadiría una tabla `employees(user_id, branch_id,
> position, salary, hired_at, …)`; hoy la relación laboral se modela con el **rol** del
> usuario y la tabla asociativa `branch_employees`.

---

### CU10: Registrar compras / ingresos de mercadería [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU10 : Registrar compras e ingresos de mercadería |
| **Propósito** | Incrementar el stock de las prendas en una sucursal tras recibir mercadería de un proveedor, dejando trazabilidad y valoración del inventario. |
| **Descripción** | El Encargado o el Superadmin registra una entrada de varias variantes a una sucursal, indicando proveedor, cantidad y costo unitario de cada una; el sistema actualiza el stock y el libro mayor de inventario de forma atómica (ACID). |
| **Actores** | Superadmin, Encargado de sucursal. |
| **Actor iniciador** | Superadmin / Encargado. |
| **Tablas** | `purchase_orders`, `purchase_details`, `inventory`, `inventory_ledger`, `suppliers`, `branches`, `product_variants`, `audit_logs` |
| **Precondición** | El proveedor (CU08), la sucursal (CU06) y las variantes de la prenda (CU07) ya existen. |
| **Flujo principal** | 1. El actor entra a "Mercadería" → "Ingreso de Nueva Mercadería".<br>2. El actor selecciona Proveedor y Sucursal destino.<br>3. El actor añade filas: por cada una, Variante + Cantidad + Costo Unitario.<br>4. El sistema calcula el subtotal por fila y el total del ingreso.<br>5. El actor pulsa "Registrar Ingreso de Mercadería".<br>6. En una sola transacción, el sistema: crea la cabecera en `purchase_orders`, el detalle en `purchase_details`, **suma las cantidades al stock** en `inventory` (creándolo si no existía) y escribe un movimiento `INGRESO` por variante en `inventory_ledger` con su costo unitario y la referencia `OC-{id}`.<br>7. El sistema registra `INSERT` sobre `purchase_orders` en `audit_logs`.<br>8. El panel "Ingresos Recientes" muestra el nuevo documento. |
| **Post condición** | El stock de la sucursal aumenta y las prendas quedan disponibles para venta o reserva. El movimiento queda valorado (promedio ponderado) y es auditable. |
| **Excepciones** | **E1: Cantidad o costo inválidos** (≤ 0): el sistema deniega la operación.<br>**E2: Proveedor, sucursal o variante inexistente:** HTTP 404.<br>**E3: Falta de permisos:** HTTP 403 si el rol no es `SUPERADMIN` ni `ENCARGADO`.<br>**E4: Fallo a mitad de la transacción:** se revierte todo (no queda stock ni documento a medias). |

---

### CU11: Consultar catálogo (cliente) [Prioridad: Alta]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU11 : Consultar catálogo — *vista de solo lectura (Ciclo 1)* |
| **Propósito** | Permitir que cualquier persona vea las prendas disponibles de la tienda. |
| **Descripción** | El actor entra a la tienda (web `/tienda` o móvil) y ve la grilla de prendas **visibles** (`is_active = true`): foto principal, nombre, categoría y precio base, con búsqueda por texto y filtro por categoría. |
| **Actores** | Visitante, Cliente (y también el personal). |
| **Actor iniciador** | Visitante o Cliente. |
| **Tablas** | `products`, `product_variants`, `product_images`, `categories` (solo lectura) |
| **Precondición** | Existe al menos una prenda activa en el catálogo (CU07). |
| **Flujo principal** | 1. El actor abre la tienda en la web o la app.<br>2. El sistema consulta el catálogo público (`GET /api/v1/catalog/products`).<br>3. El sistema muestra la grilla de prendas activas con su precio.<br>4. El actor busca por texto o filtra por categoría y navega las fichas. |
| **Post condición** | Ninguna afectación de datos (solo lectura). |
| **Excepciones** | **E1: Catálogo vacío:** el sistema muestra "No hay prendas disponibles por el momento".<br>**E2: Sin conexión (móvil):** el sistema muestra un aviso de conexión en lugar de quedarse cargando. |

> **Alcance de CU11 en el Ciclo 1:** solo consulta y filtro por categoría. El filtrado
> avanzado por talla/color/precio (CU12), la disponibilidad por sucursal (CU13), el
> carrito, el pago y el vestidor virtual corresponden a los ciclos 2 y 3.

---

### CU36: Consultar bitácora de auditoría [Prioridad: Media]

| Campo | Descripción |
| :--- | :--- |
| **Caso de Uso** | CU36 : Consultar bitácora de auditoría |
| **Propósito** | Garantizar la trazabilidad y la seguridad del sistema (requisito no funcional de auditoría). |
| **Descripción** | El Superadmin revisa un registro **inmutable** de todas las acciones sensibles: quién, cuándo, qué tabla y registro, qué cambió y desde qué IP. |
| **Actores** | Superadmin. |
| **Actor iniciador** | Superadmin. |
| **Tablas** | `audit_logs` (solo lectura) |
| **Precondición** | Estar autenticado con el rol `SUPERADMIN`. |
| **Flujo principal** | 1. El Superadmin entra a "Auditoría".<br>2. El sistema consulta `audit_logs` ordenada por fecha descendente.<br>3. El sistema formatea las fechas y el JSON de detalles (`new_values`) y presenta la tabla, con filtro por tipo de acción.<br>4. El actor revisa el historial (`LOGIN`, `LOGOUT`, `REGISTER`, `RECOVER`, `INSERT`, `UPDATE`, `DELETE`). |
| **Post condición** | Ninguna afectación de datos (solo lectura). |
| **Excepciones** | **E1: Falta de permisos:** cualquier usuario sin rol `SUPERADMIN` recibe **HTTP 403** al intentar acceder. |
