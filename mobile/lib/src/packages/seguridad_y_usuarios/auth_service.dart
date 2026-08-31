import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// [CU01-CU04] Servicio de autenticación para la app móvil.
/// Consume la API REST de FastAPI del paquete `seguridad_y_usuarios`.
class AuthService {
  /// Host del backend según dónde se ejecute la app. Se puede sobrescribir al
  /// arrancar con:  flutter run --dart-define=API_HOST=<ip>
  ///  - Dispositivo físico (mismo Wi-Fi que la PC) → IP LAN de la PC
  ///  - Emulador Android  → 10.0.2.2
  ///  - Emulador iOS / Flutter web → 127.0.0.1
  /// El valor por defecto es la IP Wi-Fi de la PC de desarrollo (dispositivo físico).
  static const String _host = String.fromEnvironment(
    'API_HOST',
    defaultValue: '192.168.0.12',
  );

  /// Base pública de la API (la usan también otras vistas, p. ej. el catálogo).
  static const String apiBaseUrl = 'http://$_host:8000/api/v1';
  static const String _baseUrl = '$apiBaseUrl/auth';
  static const Duration _timeout = Duration(seconds: 15);

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
        'No se pudo conectar con el servidor. Verifica que el backend esté corriendo '
        'y que la dirección del servidor sea la correcta para tu dispositivo.',
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
        return {'success': true, 'message': data['message']};
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

      if (response.statusCode == 200) {
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
