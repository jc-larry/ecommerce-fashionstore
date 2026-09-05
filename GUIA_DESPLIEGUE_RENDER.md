# Guía Paso a Paso: Despliegue en Render Cloud (100% Sin Docker)

Esta guía detalla la secuencia exacta para desplegar la plataforma completa **FashionStore** (Base de Datos PostgreSQL, Backend FastAPI y Frontend Web Angular) en la plataforma **Render Cloud** (https://render.com) utilizando entornos nativos administrados (**sin contenedores Docker**).

---

## 🏗️ Arquitectura en Render Cloud

```
+-------------------------------------------------------------------------------+
|                               RENDER CLOUD                                    |
|                                                                               |
|  1. PostgreSQL Database          2. FastAPI Web Service      3. Angular Site  |
|     [fashionstore-db]  <======   [fashionstore-backend] <=== [fashionstore-web]
|     PostgreSQL Nativo            Python 3.11 Nativo           Static Site SPA |
+-------------------------------------------------------------------------------+
```

---

## 📋 Requisitos Previos
1. Cuenta gratuita en [Render.com](https://render.com) (inicia sesión con tu cuenta de GitHub).
2. El repositorio subido a GitHub: `https://github.com/jc-larry/ecommerce-fashionstore.git`.

---

## PASO 1: Desplegar la Base de Datos (PostgreSQL Nativo)

1. En el panel principal de **Render**, haz clic en el botón **`New +`** (arriba a la derecha) y selecciona **`PostgreSQL`**.
2. Completa los siguientes campos:
   * **Name:** `fashionstore-db`
   * **Database:** `fashionstore`
   * **User:** `postgres`
   * **Region:** Selecciona la más cercana (ejemplo: *Ohio (US East)* u *Oregon (US West)*).  
     > [!IMPORTANT]
     > Anota la región elegida. Todos los demás servicios deben estar en esta **misma región** para máxima velocidad.
   * **PostgreSQL Version:** `15` o `16` (la que sugiera por defecto).
   * **Instance Type:** Selecciona **`Free`**.
3. Haz clic en **`Create Database`**.
4. Espera 1 minuto hasta que el estado cambie a **`Available`**.
5. Desplázate hacia abajo hasta la sección **Connections** y copia el valor de **`Internal Database URL`**  
   *(Se parece a: `postgres://postgres:clave123@dpg-xxxx-a:5432/fashionstore`)*.

---

## PASO 2: Desplegar el Backend (FastAPI en Python Nativo)

1. En Render, haz clic en **`New +`** y selecciona **`Web Service`**.
2. Elige la opción **`Build and deploy from a Git repository`** y conecta tu repositorio:  
   `jc-larry/ecommerce-fashionstore`.
3. Configura los parámetros técnicos:
   * **Name:** `fashionstore-backend`
   * **Region:** La misma región que elegiste para la base de datos.
   * **Branch:** `main`
   * **Root Directory:** `backend` *(¡Muy importante! Para que busque los archivos dentro de la carpeta backend)*.
   * **Runtime:** `Python 3`
   * **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   * **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   * **Instance Type:** **`Free`**

4. Baja a la sección **`Environment Variables`** y agrega las siguientes variables (clic en **`Add Environment Variable`**):

| Clave (Key) | Valor (Value) |
| :--- | :--- |
| `DATABASE_URL` | Pega la **Internal Database URL** que copiaste en el Paso 1. |
| `SECRET_KEY` | `fashionstore_super_secure_production_secret_key_2026` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `BACKEND_CORS_ORIGINS` | `*` |
| `FRONTEND_URL` | `https://fashionstore-web.onrender.com` *(O la URL que te asigne Render en el paso 4)* |

5. Haz clic en **`Create Web Service`**.
6. Render comenzará a compilar e instalar las dependencias de Python. Cuando finalice el despliegue verás el mensaje:
   `Application startup complete.` y el estado en verde **`Live`**.
7. Copia la URL pública asignada a tu backend (arriba a la izquierda, debajo del nombre del servicio):  
   Ejemplo: `https://fashionstore-backend.onrender.com`.

---

## PASO 3: Inicializar Usuarios y Catálogo Oficial en Producción

Con la base de datos y el backend activos, debes inicializar el usuario Superadmin y la taxonomía de moda femenina.

1. En el panel de Render, entra a tu Web Service **`fashionstore-backend`**.
2. En el menú lateral izquierdo, haz clic en la pestaña **`Shell`**.
3. Haz clic en **`Connect`** para abrir la terminal de comandos del servidor en la nube.
4. Ejecuta el comando para crear el administrador:
   ```bash
   python seed_admin.py
   ```
   *Verás:* `Usuario Superadmin creado exitosamente: admin@fashionstore.com / Admin123!`
5. A continuación, ejecuta el comando para cargar las categorías y tallas:
   ```bash
   python seed_fashion_taxonomy.py
   ```
   *Verás:* `Taxonomía de Moda Femenina inicializada exitosamente.`

---

## PASO 4: Conectar la URL del Backend en el Frontend

Antes de desplegar el frontend, actualizamos el archivo de producción de Angular con la URL real de tu backend en Render.

1. Abre el archivo [frontend-web/src/environments/environment.prod.ts](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/frontend-web/src/environments/environment.prod.ts).
2. Reemplaza la URL por la URL real de tu backend de Render terminada en `/api/v1`:
   ```typescript
   export const environment = {
     production: true,
     apiUrl: 'https://fashionstore-backend.onrender.com/api/v1', // <-- Coloca tu URL real de Render aquí
   };
   ```
3. Guarda el archivo, haz commit y push a GitHub:
   ```bash
   git add frontend-web/src/environments/environment.prod.ts
   git commit -m "chore: configurar url de backend de render en environment de produccion"
   git push origin main
   ```

---

## PASO 5: Desplegar el Frontend Web (Angular en Static Site Nativo)

1. En Render, haz clic en **`New +`** y selecciona **`Static Site`**.
2. Conecta tu repositorio de GitHub: `jc-larry/ecommerce-fashionstore`.
3. Configura los parámetros técnicos:
   * **Name:** `fashionstore-web`
   * **Branch:** `main`
   * **Root Directory:** `frontend-web` *(¡Muy importante!)*
   * **Build Command:**
     ```bash
     npm install && npm run build -- --configuration production
     ```
   * **Publish Directory:**
     ```bash
     dist/fashionstore-web
     ```
4. **Regla de Reescritura para Single Page Application (CRÍTICO en Angular):**
   * Desplázate hacia abajo hasta la sección **`Redirects/Rewrites`**.
   * Haz clic en **`Add Rule`**:
     * **Source:** `/*`
     * **Destination:** `/index.html`
     * **Action:** `Rewrite`
   > [!IMPORTANT]
   > Esta regla es obligatoria para que al recargar la página en rutas como `/tienda`, `/admin/catalogo` o `/login`, el servidor no devuelva un error 404 y permita a Angular manejar la navegación.
5. Haz clic en **`Create Static Site`**.
6. Render instalará los paquetes de Node.js, compilará el proyecto Angular y publicará el sitio web en vivo.

---

## PASO 6: Verificación en Vivo del Sistema

Una vez desplegados los tres servicios, abre la URL pública de tu Static Site (ej. `https://fashionstore-web.onrender.com`) y verifica:
1. **Inicio de Sesión:** Ingresa con `admin@fashionstore.com` y `Admin123!`.
2. **Catálogo de Prendas ([CU07]):** Comprueba las categorías en acordeón (Ropa Superior, Ropa Inferior, etc.), las curvas de tallas (Letras vs Números) y la paleta de colores.
3. **Sucursales con Mapa Interactivo ([CU06]):** Abre el formulario de *"Nueva sucursal"*, verifica que cargue el mapa interactivo de OpenStreetMap y prueba arrastrar el marcador para actualizar las coordenadas.
4. **Tienda Virtual ([CU11]):** Entra al catálogo público de prendas y comprueba las fotografías y filtros.

---

## 🛠️ Solución de Preguntas Frecuentes

* **¿Por qué el backend tarda un poco en responder la primera vez?**  
  En el plan gratuito de Render, los Web Services se suspenden tras 15 minutos de inactividad. Al recibir una petición, tardan unos 30-45 segundos en reactivarse (spin-up). Una vez activo, responde de forma instantánea.
* **¿Qué pasa si modifico código en el futuro?**  
  Render tiene integración continua (CI/CD) automática. Cada vez que hagas `git push origin main`, Render detectará los cambios y re-desplegará el servicio correspondiente de manera automática.
