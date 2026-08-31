# Diagramas de Comunicación - Ciclo 1

A continuación se presentan los diagramas de comunicación para los Casos de Uso del Ciclo 1. Se ha utilizado la notación de **Mermaid (Flowchart)** para representar la interacción entre los objetos (Actor, Interfaz [Boundary], Controlador [Control] y Entidad [Entity]), con flechas numeradas indicando la secuencia de mensajes.

---

### CU01: Iniciar Sesión

```mermaid
flowchart LR
    Actor(("👤\nUsuario"))
    IU(["🖥️\nIU_Login"])
    CTR(("⚙️\nCTR_Auth"))
    ENT[("🗄️\nCE_Usuario")]
    ENT_S[("🗄️\nCE_Sesion")]

    Actor -- "1: +ingresar(email, password)" --> IU
    IU -- "2: +login(email, password)" --> CTR
    CTR -- "3: +select_where(email)" --> ENT
    ENT -. "4: +Datos y Hash" .-> CTR
    CTR -- "5: +create_token()" --> ENT_S
    ENT_S -. "6: +Token JWT" .-> CTR
    CTR -. "7: +Redirigir a Home" .-> IU
```

**Descripción:** El actor ingresa sus credenciales en la interfaz de login. La solicitud se envía al controlador de autenticación, el cual verifica el usuario en la base de datos y, tras validar el hash, genera un token JWT en la entidad de sesión, retornando el acceso.

---

### CU02: Cerrar Sesión

```mermaid
flowchart LR
    Actor(("👤\nUsuario Autenticado"))
    IU(["🖥️\nIU_Dashboard"])
    CTR(("⚙️\nCTR_Auth"))
    ENT[("🗄️\nCE_Sesion")]

    Actor -- "1: +clicLogout()" --> IU
    IU -- "2: +logout(token)" --> CTR
    CTR -- "3: +update_revoked(token)" --> ENT
    ENT -. "4: +Confirmación" .-> CTR
    CTR -. "5: +Limpiar credenciales y redirigir" .-> IU
```

**Descripción:** El usuario autenticado solicita cerrar sesión. El controlador invalida el token activo en la base de datos y la interfaz limpia el almacenamiento local.

---

### CU03: Recuperar Credenciales

```mermaid
flowchart LR
    Actor(("👤\nUsuario"))
    IU(["🖥️\nIU_Recuperar"])
    CTR(("⚙️\nCTR_Auth"))
    ENT[("🗄️\nCE_Usuario")]

    Actor -- "1: +solicitarRecuperacion(email)" --> IU
    IU -- "2: +recover(email)" --> CTR
    CTR -- "3: +verificar_email(email)" --> ENT
    ENT -. "4: +Existe" .-> CTR
    CTR -- "5: +generar_y_enviar_token()" --> CTR
    CTR -. "6: +Mensaje de éxito" .-> IU
    
    Actor -- "7: +enviarNuevaClave(token, nueva_clave)" --> IU
    IU -- "8: +reset_password(token, nueva_clave)" --> CTR
    CTR -- "9: +update_password(hash)" --> ENT
    ENT -. "10: +Actualizado" .-> CTR
    CTR -. "11: +Redirigir a Login" .-> IU
```

**Descripción:** Flujo en dos partes: primero se solicita un token al correo electrónico, y posteriormente se envía dicho token junto con la nueva contraseña para actualizar la entidad del usuario.

---

### CU04: Auto-registro de Cliente

```mermaid
flowchart LR
    Actor(("👤\nCliente Nuevo"))
    IU(["📱\nIU_Registro"])
    CTR(("⚙️\nCTR_Auth"))
    ENT[("🗄️\nCE_Usuario")]

    Actor -- "1: +llenarFormulario(datos)" --> IU
    IU -- "2: +register(datos)" --> CTR
    CTR -- "3: +check_exists(email)" --> ENT
    ENT -. "4: +No existe" .-> CTR
    CTR -- "5: +insert(datos, rol='CLIENTE')" --> ENT
    ENT -. "6: +Usuario Creado" .-> CTR
    CTR -. "7: +Notificar éxito" .-> IU
```

**Descripción:** Un usuario nuevo envía sus datos. El sistema verifica que el correo no esté duplicado, encripta la clave y crea el registro con el rol predeterminado de CLIENTE.

---

### CU05: Gestionar perfiles y roles

```mermaid
flowchart LR
    Actor(("👤\nAdmin (SUPERADMIN)"))
    IU(["🖥️\nIU_Usuarios"])
    CTR(("⚙️\nCTR_Usuarios"))
    ENT[("🗄️\nCE_Usuario")]
    ENT_R[("🗄️\nCE_Rol")]

    Actor -- "1: +crearUsuario(datos, roles)" --> IU
    IU -- "2: +create_user(datos, roles)" --> CTR
    CTR -- "3: +insert(datos)" --> ENT
    ENT -. "4: +ID Usuario" .-> CTR
    CTR -- "5: +assign_roles(id, roles)" --> ENT_R
    ENT_R -. "6: +Roles asignados" .-> CTR
    CTR -. "7: +Actualizar lista" .-> IU
```

**Descripción:** El administrador da de alta un nuevo empleado, registrando su perfil y asignándole los roles correspondientes (ej. CAJERO, ENCARGADO).

---

### CU06: Gestionar sucursales

```mermaid
flowchart LR
    Actor(("👤\nAdministrador"))
    IU(["🖥️\nIU_Sucursales"])
    CTR(("⚙️\nCTR_Sucursales"))
    ENT[("🗄️\nCE_Sucursal")]

    Actor -- "1: +guardarSucursal(datos)" --> IU
    IU -- "2: +create_branch(datos)" --> CTR
    CTR -- "3: +insert(datos)" --> ENT
    ENT -. "4: +Sucursal Creada" .-> CTR
    CTR -. "5: +Actualizar tabla" .-> IU
```

**Descripción:** Se envían los datos (nombre, dirección, teléfono) para registrar una nueva sucursal física en la base de datos.

---

### CU07: Gestionar catálogo

```mermaid
flowchart LR
    Actor(("👤\nAdmin / Encargado"))
    IU(["🖥️\nIU_Productos"])
    CTR(("⚙️\nCTR_Catalogo"))
    ENT_P[("🗄️\nCE_Producto")]
    ENT_V[("🗄️\nCE_Variante")]

    Actor -- "1: +guardarPrenda(datos, variantes)" --> IU
    IU -- "2: +create_product(datos)" --> CTR
    CTR -- "3: +insert(producto)" --> ENT_P
    ENT_P -. "4: +Producto ID" .-> CTR
    CTR -- "5: +insert(variantes)" --> ENT_V
    ENT_V -. "6: +Variantes creadas" .-> CTR
    CTR -. "7: +Actualizar catálogo" .-> IU
```

**Descripción:** Se crea un producto base (ej. Blusa) y se asocian sus distintas variantes de stock (Talla M, Color Rojo, etc.) en un solo flujo transaccional.

---

### CU08: Gestionar proveedores

```mermaid
flowchart LR
    Actor(("👤\nAdmin / Encargado"))
    IU(["🖥️\nIU_Proveedores"])
    CTR(("⚙️\nCTR_Proveedores"))
    ENT[("🗄️\nCE_Proveedor")]

    Actor -- "1: +guardarProveedor(datos)" --> IU
    IU -- "2: +create_supplier(datos)" --> CTR
    CTR -- "3: +insert(datos)" --> ENT
    ENT -. "4: +Proveedor Creado" .-> CTR
    CTR -. "5: +Confirmación" .-> IU
```

**Descripción:** Registro y administración de los proveedores (fabricantes o distribuidores) que suministran mercadería a la cadena.

---

### CU09: Gestionar empleados

```mermaid
flowchart LR
    Actor(("👤\nAdministrador"))
    IU(["🖥️\nIU_Empleados"])
    CTR(("⚙️\nCTR_Empleados"))
    ENT_E[("🗄️\nCE_Empleado")]
    ENT_S[("🗄️\nCE_Sucursal")]

    Actor -- "1: +asignar(usuario_id, sucursal_id)" --> IU
    IU -- "2: +assign_employee(ids)" --> CTR
    CTR -- "3: +vincular(usuario, sucursal)" --> ENT_E
    ENT_E -. "4: +Vinculado" .-> CTR
    CTR -- "5: +actualizar_staff()" --> ENT_S
    ENT_S -. "6: +OK" .-> CTR
    CTR -. "7: +Confirmar asignación" .-> IU
```

**Descripción:** Se vincula a un usuario administrativo (creado en CU05) como empleado formal de una sucursal específica (creada en CU06).

---

### CU10: Registrar compras/ingresos

```mermaid
flowchart LR
    Actor(("👤\nEncargado / Admin"))
    IU(["🖥️\nIU_Ingresos"])
    CTR(("⚙️\nCTR_Inventario"))
    ENT_I[("🗄️\nCE_Ingreso")]
    ENT_S[("🗄️\nCE_Stock")]

    Actor -- "1: +registrarIngreso(lote)" --> IU
    IU -- "2: +register_intake(lote)" --> CTR
    CTR -- "3: +insert(ingreso, proveedor)" --> ENT_I
    ENT_I -. "4: +Ingreso ID" .-> CTR
    CTR -- "5: +incrementar_stock(variantes, cant)" --> ENT_S
    ENT_S -. "6: +Stock actualizado" .-> CTR
    CTR -. "7: +Mostrar éxito" .-> IU
```

**Descripción:** Al recibir mercadería, se registra la entrada (Intake) vinculada al proveedor y se incrementa automáticamente el inventario (Stock) de la sucursal de manera atómica.

---

### CU11: Consultar catálogo (Público)

```mermaid
flowchart LR
    Actor(("👤\nCliente"))
    IU(["🖥️/📱\nIU_Tienda"])
    CTR(("⚙️\nCTR_Catalogo"))
    ENT[("🗄️\nCE_Producto")]

    Actor -- "1: +navegar(filtros)" --> IU
    IU -- "2: +list_products(filtros)" --> CTR
    CTR -- "3: +select_active()" --> ENT
    ENT -. "4: +Lista de Productos" .-> CTR
    CTR -. "5: +Renderizar cuadrícula" .-> IU
```

**Descripción:** El cliente explora la tienda virtual. El sistema consulta únicamente las prendas que están activadas para mostrar sus precios e imágenes.

---

### CU36: Consultar bitácora de auditoría

```mermaid
flowchart LR
    Actor(("👤\nAdmin (SUPERADMIN)"))
    IU(["🖥️\nIU_Auditoria"])
    CTR(("⚙️\nCTR_Auditoria"))
    ENT[("🗄️\nCE_Bitacora")]

    Actor -- "1: +verLogs()" --> IU
    IU -- "2: +get_audit_logs()" --> CTR
    CTR -- "3: +select_all()" --> ENT
    ENT -. "4: +Registros Inmutables" .-> CTR
    CTR -. "5: +Mostrar tabla cronológica" .-> IU
```

**Descripción:** El superadministrador solicita ver el historial de acciones del sistema. El controlador lee la tabla de logs y devuelve la información para su monitoreo.
