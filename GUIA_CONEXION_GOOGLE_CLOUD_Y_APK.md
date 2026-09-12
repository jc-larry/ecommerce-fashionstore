# Guía Paso a Paso: Conexión de la App Móvil (APK) con Google Cloud

Esta guía explica detalladamente cómo conectar la aplicación móvil Android (**APK**) con el backend desplegado en **Google Cloud Platform (GCP)** para que funcione de forma autónoma: **con datos móviles 4G/5G o en cualquier red Wi-Fi**, sin depender de la IP local de tu casa.

---

## 📋 Índice
1. [Obtener la URL pública del Backend en Google Cloud](#paso-1-obtener-la-url-pública-del-backend-en-google-cloud)
2. [Conectar la App instalada de inmediato (Sin Recompilar)](#paso-2-conectar-tu-app-instalada-al-instante-sin-recompilar)
3. [Configurar la URL por defecto en el código fuente de Flutter](#paso-3-configurar-la-url-fija-en-el-código-fuente)
4. [Compilar el nuevo archivo APK de Producción](#paso-4-compilar-el-nuevo-archivo-apk-de-producción)
5. [Verificar que la Base de Datos de Google Cloud tenga los Productos](#paso-5-verificar-el-catálogo-en-la-base-de-datos-de-google-cloud)

---

## Paso 1: Obtener la URL pública del Backend en Google Cloud

Dependiendo de cómo desplegaron el backend en Google Cloud, copia la URL pública asignada:

### Opción A: Si usaron Cloud Run
1. Ingresa a la consola de Google Cloud: [console.cloud.google.com](https://console.cloud.google.com).
2. Ve al menú **Cloud Run** y selecciona el servicio de tu backend (por ejemplo: `fashionstore-backend`).
3. En la parte superior verás la **URL del servicio**, que tiene un formato similar a:  
   `https://fashionstore-backend-xxxx-uc.a.run.app`
4. Tu endpoint base de la API será esa URL agregándole `/api/v1`:  
   👉 `https://fashionstore-backend-xxxx-uc.a.run.app/api/v1`

### Opción B: Si usaron Compute Engine (Máquina Virtual)
1. En la consola de Google Cloud, ve a **Compute Engine > Instancias de VM**.
2. Copia la **IP externa** asignada a la máquina (ejemplo: `34.125.80.200`).
3. Tu endpoint base de la API será esa IP con el puerto 8000:  
   👉 `http://34.125.80.200:8000/api/v1`

### Opción C: Si usaron App Engine
1. En la consola, ve a **App Engine > Panel**.
2. Copia la URL del servicio (ejemplo: `https://fashionstore-dot-proyecto.appspot.com`).
3. Tu endpoint base de la API será:  
   👉 `https://fashionstore-dot-proyecto.appspot.com/api/v1`

> [!TIP]
> **Prueba rápida en el navegador:** Abre la URL en Chrome agregándole `/docs` (ej. `https://TU-URL/docs`). Si abre la documentación interactiva Swagger de FastAPI, tu backend está 100% en línea y listo.

---

## Paso 2: Conectar tu App instalada al instante (Sin Recompilar)

En el APK que ya tienes instalado en tu teléfono puedes apuntar a Google Cloud de inmediato:

1. **Abre la app FashionStore en tu celular.**
2. En la barra inferior, toca la 5ta pestaña: **`Perfil`** (icono de la persona).
3. Toca el botón: **`Iniciar Sesión`**.
4. En la esquina superior derecha de la pantalla de Login (sobre la imagen), toca el **icono de Wi-Fi (`📶`)**.
5. Se abrirá la ventana **"Servidor Backend"**.
6. En el campo de texto, borra lo que haya y escribe tu URL de Google Cloud:
   ```text
   https://TU-URL-DE-GOOGLE-CLOUD/api/v1
   ```
7. Presiona **"Probar Conexión"**. Debe responder:  
   `Conectado exitosamente ✅`
8. Presiona **"Guardar"**.

Al volver a la pestaña de **Catálogo**, todas las prendas se cargarán automáticamente desde Google Cloud, tanto con datos móviles como con cualquier Wi-Fi.

---

## Paso 3: Configurar la URL fija en el código fuente

Para que cualquier nuevo APK que compiles ya venga configurado con Google Cloud por defecto:

1. Abre el archivo:  
   [`mobile/lib/src/packages/seguridad_y_usuarios/auth_service.dart`](file:///c:/Users/MARILYN/Documents/Carpeta%20Esther/Semestre%202-2026/SI%202/Primer_parcial/mobile/lib/src/packages/seguridad_y_usuarios/auth_service.dart)

2. Localiza las líneas 24-30:
   ```dart
   static const String _baseUrlOverride =
       String.fromEnvironment('API_BASE_URL', defaultValue: 'https://TU-URL-DE-GOOGLE-CLOUD/api/v1');
   ```

3. Coloca tu URL de Google Cloud en `defaultValue`. Al hacer esto, la aplicación se conectará automáticamente a Google Cloud desde el primer segundo en que se instale.

---

## Paso 4: Compilar el nuevo archivo APK de Producción

Para generar el archivo instalador `.apk` listo para entregar o instalar:

1. Abre una terminal de **PowerShell** en tu computadora.
2. Navega a la carpeta móvil:
   ```powershell
   cd "C:\Users\MARILYN\Documents\Carpeta Esther\Semestre 2-2026\SI 2\Primer_parcial\mobile"
   ```
3. Ejecuta el comando de compilación optimizado para release:
   ```powershell
   flutter build apk --release --dart-define=API_BASE_URL=https://TU-URL-DE-GOOGLE-CLOUD/api/v1
   ```
4. Al finalizar la compilación (demora aprox. 1-2 minutos), el archivo APK quedará generado en:
   ```text
   mobile\build\app\outputs\flutter-apk\app-release.apk
   ```

### (Opcional) Copiar el APK para descarga directa desde la Web:
Si deseas que cualquier persona pueda descargar el APK entrando al navegador, cópialo a la carpeta de descargas del backend:
```powershell
copy "build\app\outputs\flutter-apk\app-release.apk" "..\backend\uploads\apk\fashionstore.apk"
```
Cualquier usuario podrá descargarlo directamente abriendo:  
👉 `https://TU-URL-DE-GOOGLE-CLOUD/download-apk`

---

## Paso 5: Verificar el Catálogo en la Base de Datos de Google Cloud

Si al abrir la app ves que conecta exitosamente pero dice *"No hay prendas disponibles"*, significa que la base de datos de Google Cloud (Cloud SQL o PostgreSQL) aún no tiene los datos iniciales migrados.

Para poblar las 12 prendas elegantes de moda femenina, categorías y tallas en Google Cloud:

1. Obtén la cadena de conexión `DATABASE_URL` de tu base de datos de Google Cloud:  
   *(Formato: `postgresql://usuario:contraseña@IP_O_HOST:5432/fashionstore`)*
2. En tu terminal local, ejecuta el script de migración apuntando a Google Cloud:
   ```powershell
   cd "C:\Users\MARILYN\Documents\Carpeta Esther\Semestre 2-2026\SI 2\Primer_parcial\backend"
   $env:DATABASE_URL="postgresql://usuario:contraseña@IP_GOOGLE_CLOUD:5432/fashionstore"
   python migrate_master_fashion_data.py
   ```
3. El script insertará automáticamente:
   * 12 Prendas de alta costura femenina con fotografías de calidad.
   * Curva completa de tallas y colores.
   * Inventario por sucursales.
   * Usuarios y roles del sistema.

---

## 🎯 Resumen de Beneficios

Siguiendo estos pasos con Google Cloud:
* ✅ La app funciona **100% independiente de tu PC local**.
* ✅ No requiere estar en la misma red Wi-Fi.
* ✅ Funciona con **datos móviles 4G/5G** desde la calle o en la universidad.
* ✅ El catálogo carga al instante sin necesidad de escribir IPs locales.
