# Diagramas de Secuencia - Ciclo 1 (FashionStore)

A continuación se presentan los **Diagramas de Secuencia** para los 12 casos de uso del Ciclo 1. Siguiendo tus indicaciones, se ha utilizado la nomenclatura **DSC** (Diagrama de Secuencia de Caso de uso) para diferenciarlos claramente de los diagramas de comunicación.

---

### DSC001: Iniciar sesión

```mermaid
sequenceDiagram
    actor U as Usuario (No Autenticado)
    participant IU as IU_Login
    participant CTR as CTR_Auth
    participant CE_U as CE_Usuario
    participant CE_S as CE_SessionToken

    U->>+IU: 1: ingresar(email, password)
    IU->>+CTR: 2: login(email, password)
    CTR->>+CE_U: 3: select_where(email)
    CE_U-->>-CTR: 4: Datos y Hash
    Note over CTR: Verifica contraseña
    CTR->>+CE_S: 5: create_token()
    CE_S-->>-CTR: 6: Token JWT
    CTR-->>-IU: 7: Token JWT y Datos
    IU-->>-U: 8: Redirigir a Home()
```

---

### DSC002: Cerrar sesión

```mermaid
sequenceDiagram
    actor U as Usuario (Autenticado)
    participant IU as IU_Dashboard
    participant CTR as CTR_Auth
    participant CE_S as CE_SessionToken
    participant BD as CE_Bitacora

    U->>+IU: 1: clicLogout()
    IU->>+CTR: 2: logout(token)
    CTR->>+CE_S: 3: update_revoked(token)
    CE_S-->>-CTR: 4: Confirmación
    CTR->>+BD: 5: insert(LOGOUT)
    BD-->>-CTR: 6: Confirmación
    CTR-->>-IU: 7: Éxito
    IU-->>-U: 8: Limpiar credenciales y redirigir
```

---

### DSC003: Recuperar credenciales

```mermaid
sequenceDiagram
    actor U as Usuario (Cliente/Empleado)
    participant IU as IU_Recover
    participant CTR as CTR_Auth
    participant CE_U as CE_Usuario

    U->>+IU: 1: solicitarRecuperacion(email)
    IU->>+CTR: 2: recover(email)
    CTR->>+CE_U: 3: verificar_email(email)
    CE_U-->>-CTR: 4: Existe
    Note over CTR: Genera token seguro
    CTR->>CTR: 5: generar_y_enviar_token()
    CTR-->>-IU: 6: Mensaje de éxito
    IU-->>-U: 7: Mostrar aviso de correo
    
    Note over U, CE_U: El usuario abre el enlace del correo
    
    U->>+IU: 8: enviarNuevaClave(token, nueva_clave)
    IU->>+CTR: 9: reset_password(token, nueva_clave)
    CTR->>+CE_U: 10: update_password(hash)
    CE_U-->>-CTR: 11: Actualizado
    CTR-->>-IU: 12: Éxito
    IU-->>-U: 13: Redirigir a Login()
```

---

### DSC004: Auto-registro de cliente

```mermaid
sequenceDiagram
    actor C as Cliente Nuevo
    participant IU as IU_Register
    participant CTR as CTR_Auth
    participant CE_U as CE_Usuario

    C->>+IU: 1: llenarFormulario(datos)
    IU->>+CTR: 2: register(datos)
    CTR->>+CE_U: 3: check_exists(email)
    CE_U-->>-CTR: 4: No existe
    CTR->>+CE_U: 5: insert(datos, rol='CLIENTE')
    CE_U-->>-CTR: 6: Usuario Creado
    CTR-->>-IU: 7: Respuesta 201 Created
    IU-->>-C: 8: Notificar éxito y redirigir
```

---

### DSC005: Gestionar perfiles y roles

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_UsuariosRoles
    participant CTR as CTR_Users
    participant CE_U as CE_Usuario

    A->>+IU: 1: crearUsuario(datos, roles)
    IU->>+CTR: 2: create_user(datos, roles)
    CTR->>+CE_U: 3: insert(datos)
    CE_U-->>-CTR: 4: ID Usuario
    CTR->>+CE_U: 5: assign_roles(id, roles)
    CE_U-->>-CTR: 6: Roles asignados
    CTR-->>-IU: 7: Usuario Creado
    IU-->>-A: 8: Actualizar lista en UI
```

---

### DSC006: Gestionar sucursales

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_Branches
    participant CTR as CTR_Branches
    participant CE_B as CE_Sucursal

    A->>+IU: 1: registrar(datos)
    IU->>+CTR: 2: create_branch(datos)
    CTR->>+CE_B: 3: check_exists(nombre)
    CE_B-->>-CTR: 4: No existe
    CTR->>+CE_B: 5: insert_branch(datos)
    CE_B-->>-CTR: 6: Sucursal Creada
    CTR-->>-IU: 7: 201 Created
    IU-->>-A: 8: Actualizar lista en UI
```

---

### DSC007: Gestionar catálogo

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_Products
    participant CTR as CTR_Products
    participant CE_P as CE_Producto
    participant CE_V as CE_Variante

    A->>+IU: 1: registrar(datos, variantes)
    IU->>+CTR: 2: create_product(datos, variantes)
    CTR->>+CE_P: 3: insert_product(datos)
    CE_P-->>-CTR: 4: ID Producto
    
    loop Por cada variante
        CTR->>+CE_V: 5: insert_variants(variantes)
        CE_V-->>-CTR: 6: Confirmación
    end
    
    CTR-->>-IU: 7: Producto Creado
    IU-->>-A: 8: Actualizar UI
```

---

### DSC008: Gestionar proveedores

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_Suppliers
    participant CTR as CTR_Suppliers
    participant CE_S as CE_Proveedor

    A->>+IU: 1: registrar(datos)
    IU->>+CTR: 2: create_supplier(datos)
    CTR->>+CE_S: 3: check_exists(nit)
    CE_S-->>-CTR: 4: No existe
    CTR->>+CE_S: 5: insert_supplier(datos)
    CE_S-->>-CTR: 6: Proveedor Creado
    CTR-->>-IU: 7: 201 Created
    IU-->>-A: 8: Actualizar lista en UI
```

---

### DSC009: Gestionar empleados

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_Branches
    participant CTR as CTR_Branches
    participant CE_B as CE_Sucursal

    A->>+IU: 1: asignarSucursal(empleado, sucursal)
    IU->>+CTR: 2: assign_employee(sucursal_id, usuario_id)
    CTR->>+CE_B: 3: check_exists(sucursal_id, usuario_id)
    CE_B-->>-CTR: 4: Válidos
    CTR->>+CE_B: 5: insert_assign(sucursal_id, usuario_id)
    CE_B-->>-CTR: 6: Asignación Completada
    CTR-->>-IU: 7: Éxito
    IU-->>-A: 8: Actualizar UI
```

---

### DSC010: Registrar compras/ingresos

```mermaid
sequenceDiagram
    actor E as Encargado / Superadmin
    participant IU as IU_Merchandise
    participant CTR as CTR_Inventory
    participant CE_C as CE_Compra
    participant CE_I as CE_Inventario

    E->>+IU: 1: registrar(datos)
    IU->>+CTR: 2: register_intake(datos)
    CTR->>CTR: 3: check_relations(proveedor_id, sucursal_id)
    CTR->>+CE_C: 4: insert_purchase(cabecera)
    CE_C-->>-CTR: 5: ID Compra
    
    loop Por cada detalle
        CTR->>+CE_C: 6: insert_detail(detalle)
        CE_C-->>-CTR: 7: OK
        CTR->>+CE_I: 8: increment_stock(detalle)
        CE_I-->>-CTR: 9: OK
    end
    
    CTR-->>-IU: 10: Ingreso Completado
    IU-->>-E: 11: Notificar éxito y limpiar
```

---

### DSC011: Consultar catálogo

```mermaid
sequenceDiagram
    actor C as Cliente
    participant IU as IU_StoreHome
    participant CTR as CTR_Products
    participant CE_P as CE_Producto

    C->>+IU: 1: entrarATienda()
    IU->>+CTR: 2: get_products()
    CTR->>+CE_P: 3: select_active()
    CE_P-->>-CTR: 4: Lista de productos activos
    CTR-->>-IU: 5: JSON Array
    IU-->>-C: 6: Mostrar lista de prendas
```

---

### DSC036: Consultar bitácora de auditoría

```mermaid
sequenceDiagram
    actor A as Superadmin
    participant IU as IU_Audit
    participant CTR as CTR_Users
    participant CE_A as CE_AuditLog

    A->>+IU: 1: verLogs()
    IU->>+CTR: 2: get_audit_logs()
    CTR->>+CE_A: 3: select_all()
    CE_A-->>-CTR: 4: Registros inmutables
    CTR-->>-IU: 5: JSON Array
    IU-->>-A: 6: Mostrar tabla cronológica
```
