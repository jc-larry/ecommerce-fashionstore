import 'dart:convert';
import 'package:http/http.dart' as http;
import '../seguridad_y_usuarios/auth_service.dart';

/// [CU17 / CU18 / CU20 / CU24] Cliente HTTP de Ventas y Pagos para la app móvil:
/// Carrito, checkout omnicanal polimórfico, facturación fiscal IVA 13% e historial de compras.
class VentasApi {
  static const Duration _timeout = Duration(seconds: 15);

  static Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await AuthService.getToken();
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// [CU17] Obtener el carrito digital del usuario autenticado.
  static Future<Map<String, dynamic>?> fetchCart() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/sales/cart'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) {
        return jsonDecode(r.body) as Map<String, dynamic>;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  /// [CU17] Añadir prenda al carrito con control estricto de existencias físicas.
  static Future<Map<String, dynamic>> addToCart(int variantId, int quantity) async {
    final r = await http
        .post(
          Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items'),
          headers: await _headers(),
          body: jsonEncode({'variant_id': variantId, 'quantity': quantity}),
        )
        .timeout(_timeout);

    if (r.statusCode == 200) {
      return {'ok': true, 'data': jsonDecode(r.body)};
    }
    final err = jsonDecode(r.body);
    return {'ok': false, 'detail': err['detail'] ?? 'No se pudo agregar la prenda.'};
  }

  /// [CU17] Actualizar cantidad de un ítem en el carrito.
  static Future<Map<String, dynamic>> updateCartItem(int itemId, int quantity) async {
    final r = await http
        .put(
          Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items/$itemId'),
          headers: await _headers(),
          body: jsonEncode({'quantity': quantity}),
        )
        .timeout(_timeout);

    if (r.statusCode == 200) {
      return {'ok': true, 'data': jsonDecode(r.body)};
    }
    final err = jsonDecode(r.body);
    return {'ok': false, 'detail': err['detail'] ?? 'Error al modificar cantidad.'};
  }

  /// [CU17] Eliminar un ítem del carrito.
  static Future<bool> removeCartItem(int itemId) async {
    final r = await http
        .delete(
          Uri.parse('${AuthService.apiBaseUrl}/sales/cart/items/$itemId'),
          headers: await _headers(),
        )
        .timeout(_timeout);
    return r.statusCode == 200;
  }

  /// [CU17] Vaciar completamente el carrito de compras.
  static Future<bool> clearCart() async {
    final r = await http
        .delete(
          Uri.parse('${AuthService.apiBaseUrl}/sales/cart/clear'),
          headers: await _headers(),
        )
        .timeout(_timeout);
    return r.statusCode == 200;
  }

  /// [CU18 / CU20] Procesar compra omnicanal con medio de pago polimórfico y comprobante fiscal.
  static Future<Map<String, dynamic>> checkout(Map<String, dynamic> payload) async {
    final r = await http
        .post(
          Uri.parse('${AuthService.apiBaseUrl}/sales/checkout'),
          headers: await _headers(),
          body: jsonEncode(payload),
        )
        .timeout(_timeout);

    if (r.statusCode == 201) {
      return {'ok': true, 'data': jsonDecode(r.body)};
    }
    final err = jsonDecode(r.body);
    return {'ok': false, 'detail': err['detail'] ?? 'No se pudo completar la compra.'};
  }

  /// [CU24] Historial de compras y pedidos del cliente.
  static Future<List<dynamic>> fetchMyOrders() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/sales/orders/my-orders'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) {
      return jsonDecode(r.body) as List<dynamic>;
    }
    return [];
  }

  /// [CU24] Detalle de una compra específica con comprobante fiscal.
  static Future<Map<String, dynamic>?> fetchOrder(int id) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/sales/orders/$id'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) {
      return jsonDecode(r.body) as Map<String, dynamic>;
    }
    return null;
  }

  /// Obtener sucursales físicas disponibles para despacho/retiro.
  static Future<List<dynamic>> fetchBranches() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/branches'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) {
      return jsonDecode(r.body) as List<dynamic>;
    }
    return [];
  }
}
