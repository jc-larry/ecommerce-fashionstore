import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// [CU01-CU04] Servicio de autenticación para la app móvil.
/// Consume la API REST de FastAPI del paquete `seguridad_y_usuarios`.
class AuthService {
  // === Configuración del backend ===================================================
  // Prioridad: 1) API_BASE_URL (URL completa)  2) API_HOST + API_PORT.
  //
  // DESPLIEGUE (producción): pasar la URL pública completa, p. ej.
  //   flutter run  --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
  //   flutter build apk --dart-define=API_BASE_URL=https://fashionstore-api.tudominio.com/api/v1
  //
  // DESARROLLO (elige según dónde corre la app):
  //   - Dispositivo físico en el mismo Wi-Fi → la IP LAN de la PC:
  //       --dart-define=API_HOST=192.168.x.x
  //   - Emulador Android → --dart-define=API_HOST=10.0.2.2
  //   - Emulador iOS / Flutter web/desktop → --dart-define=API_HOST=127.0.0.1
  //
  // El backend debe correr con host 0.0.0.0 para que un teléfono lo alcance:
  //   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  static const String _baseUrlOverride =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const String _host =
      String.fromEnvironment('API_HOST', defaultValue: '10.10.151.229');
  static const String _port =
      String.fromEnvironment('API_PORT', defaultValue: '8000');

  static String? _customApiBaseUrl;

  /// Base pública de la API (la usan también otras vistas, p. ej. el catálogo).
  static String get apiBaseUrl {
    if (_customApiBaseUrl != null && _customApiBaseUrl!.isNotEmpty) {
      return _customApiBaseUrl!;
    }
    if (_baseUrlOverride.isNotEmpty) {
      return _baseUrlOverride;
    }
    return 'http://$_host:$_port/api/v1';
  }

  static String get _baseUrl => '$apiBaseUrl/auth';
  static const Duration _timeout = Duration(seconds: 15);

  /// Cargar URL personalizada guardada en preferencias (si existe).
  static Future<void> init() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('custom_api_base_url');
      if (saved != null && saved.trim().isNotEmpty) {
        _customApiBaseUrl = saved.trim();
      }
    } catch (_) {}
  }

  /// Permite cambiar dinámicamente la IP/URL del backend desde la app sin cables.
  static Future<void> setCustomBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    var clean = url.trim();
    while (clean.endsWith('/')) {
      clean = clean.substring(0, clean.length - 1);
    }
    if (!clean.endsWith('/api/v1') && !clean.contains('/api/')) {
      clean = '$clean/api/v1';
    }
    _customApiBaseUrl = clean;
    await prefs.setString('custom_api_base_url', clean);
  }

  /// Probar conectividad con el backend
  static Future<bool> testConnection([String? urlToTest]) async {
    var target = urlToTest != null && urlToTest.trim().isNotEmpty ? urlToTest.trim() : apiBaseUrl;
    while (target.endsWith('/')) {
      target = target.substring(0, target.length - 1);
    }
    if (!target.endsWith('/api/v1') && !target.contains('/api/')) {
      target = '$target/api/v1';
    }
    try {
      final r = await http.get(Uri.parse('$target/branches')).timeout(const Duration(seconds: 4));
      return r.statusCode == 200;
    } catch (_) {
      try {
        final r = await http.get(Uri.parse(target.replaceAll('/api/v1', '/docs'))).timeout(const Duration(seconds: 4));
        return r.statusCode == 200;
      } catch (_) {
        return false;
      }
    }
  }

  static Map<String, dynamic> _fail(String message) => {'success': false, 'message': message};

  static Map<String, dynamic> _parseError(http.Response r, String fallback) {
    try {
      final body = jsonDecode(r.body);
      return _fail(body is Map && body['detail'] != null ? body['detail'].toString() : fallback);
    } catch (_) {
      return _fail('$fallback (código ${r.statusCode})');
    }
  }

  static Map<String, dynamic> _networkError(Object e) {
    if (e is SocketException || e is HttpException) {
      return _fail(
        'No se pudo conectar con el servidor ($apiBaseUrl). Verifica que el backend '
        'esté corriendo y que la dirección sea la correcta para tu dispositivo '
        '(--dart-define=API_HOST o API_BASE_URL).',
      );
    }
    return _fail('El servidor no respondió a tiempo. Inténtalo de nuevo.');
  }

  // --- [CU01] Iniciar sesión ---
  static Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/login'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(_timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('token', data['access_token']);
        await prefs.setString('user', jsonEncode(data['user']));
        await prefs.setStringList('roles', List<String>.from(data['roles'] ?? const []));
        return {'success': true, 'data': data};
      }
      return _parseError(response, 'Correo o contraseña incorrectos');
    } catch (e) {
      return _networkError(e);
    }
  }

  // --- [CU02] Cerrar sesión ---
  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('token');
    if (token != null) {
      try {
        await http.post(
          Uri.parse('$_baseUrl/logout'),
          headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
        ).timeout(_timeout);
      } catch (_) {}
    }
    await prefs.remove('token');
    await prefs.remove('user');
    await prefs.remove('roles');
  }

  // --- [CU03] Recuperar credenciales ---
  static Future<Map<String, dynamic>> recover(String email) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/recover'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email}),
          )
          .timeout(_timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {
          'success': true,
          'message': data['message'],
          // Solo presente si el backend corre sin SMTP (modo desarrollo).
          'devResetLink': data['dev_reset_link'],
        };
      }
      return _parseError(response, 'No se pudo enviar el enlace de recuperación');
    } catch (e) {
      return _networkError(e);
    }
  }

  // El restablecimiento de la contraseña (reset-password) se realiza en la página
  // web que abre el enlace del correo, no dentro de la app.

  // --- [CU04] Auto-registro de cliente ---
  static Future<Map<String, dynamic>> register({
    required String firstName,
    required String lastName,
    required String email,
    required String phone,
    required String password,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('$_baseUrl/register'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'first_name': firstName,
              'last_name': lastName,
              'email': email,
              'phone': phone,
              'password': password,
            }),
          )
          .timeout(_timeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        return {'success': true, 'data': data};
      }
      return _parseError(response, 'No se pudo registrar la cuenta');
    } catch (e) {
      return _networkError(e);
    }
  }

  // --- Utilidades ---
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('token');
  }

  static Future<bool> isLoggedIn() async {
    final token = await getToken();
    return token != null;
  }
}
