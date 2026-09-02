# fashionstore_mobile

App móvil (Flutter) de FashionStore. En el **Ciclo 1** es exclusiva del **cliente final**:
inicio de sesión (CU01), cierre de sesión (CU02), recuperación de credenciales (CU03),
auto-registro (CU04) y consulta del catálogo (CU11).

## Configuración de la URL del backend

La app resuelve la URL de la API en este orden:

1. **`API_BASE_URL`** — URL completa (incluye `/api/v1`). Úsalo para **producción**:
   ```
   flutter run       --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
   flutter build apk --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
   ```
2. **`API_HOST`** (+ opcional `API_PORT`, por defecto `8000`) — para **desarrollo**:
   | Dónde corre la app | `--dart-define=API_HOST=` |
   |---|---|
   | Dispositivo físico en el mismo Wi-Fi que la PC | la IP LAN de la PC (p. ej. `192.168.1.20`) |
   | Emulador Android | `10.0.2.2` |
   | Emulador iOS / Flutter web / desktop | `127.0.0.1` |

El backend debe correr accesible desde el dispositivo:
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notas de autenticación

- El **correo es insensible a mayúsculas**: registrarse en la web e iniciar sesión en el móvil
  (o al revés) siempre coordina; el backend normaliza el correo a minúsculas.
- La **recuperación de contraseña** se pide desde la app, pero la pantalla de "nueva
  contraseña" se abre desde el **enlace del correo** (página web responsiva), nunca dentro de
  la app. Si el backend corre sin SMTP configurado, la app muestra el enlace directo (modo
  desarrollo).

## Getting Started (Flutter)

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [online documentation](https://docs.flutter.dev/)
