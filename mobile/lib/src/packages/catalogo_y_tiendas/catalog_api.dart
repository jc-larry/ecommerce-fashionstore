import 'dart:convert';
import 'package:http/http.dart' as http;
import '../seguridad_y_usuarios/auth_service.dart';

/// [CU11 / CU14] Cliente HTTP del catálogo de la tienda (móvil):
/// prendas, categorías, detalle, reseñas y favoritos.
class CatalogApi {
  static const Duration _timeout = Duration(seconds: 15);

  static Future<Map<String, String>> _headers({bool json = true}) async {
    final token = await AuthService.getToken();
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Resuelve una URL relativa de imagen (`/uploads/...`) a absoluta.
  static String resolveImage(String? url) {
    if (url == null || url.isEmpty) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    final base = AuthService.apiBaseUrl.replaceAll('/api/v1', '');
    return '$base${url.startsWith('/') ? '' : '/'}$url';
  }

  static Future<List<dynamic>> fetchProducts() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode != 200) return [];
    return (jsonDecode(r.body) as List).where((p) => p['is_active'] == true).toList();
  }

  static Future<List<dynamic>> fetchCategories() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/categories'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as List : [];
  }

  static Future<Map<String, dynamic>?> fetchProduct(int id) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as Map<String, dynamic> : null;
  }

  static Future<Map<String, dynamic>> fetchReviews(int id) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id/reviews'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode == 200) return jsonDecode(r.body) as Map<String, dynamic>;
    return {'summary': {'average': 0, 'count': 0}, 'items': []};
  }

  static Future<bool> submitReview(int id, int rating, String comment) async {
    final r = await http
        .post(
          Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id/reviews'),
          headers: await _headers(),
          body: jsonEncode({'rating': rating, 'comment': comment.isEmpty ? null : comment}),
        )
        .timeout(_timeout);
    return r.statusCode == 200 || r.statusCode == 201;
  }

  static Future<Map<int, Map<String, dynamic>>> fetchRatingsSummary() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/ratings-summary'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode != 200) return {};
    final out = <int, Map<String, dynamic>>{};
    for (final x in jsonDecode(r.body) as List) {
      out[x['product_id'] as int] = {'average': x['average'], 'count': x['count']};
    }
    return out;
  }

  static Future<Set<int>> fetchWishlistIds() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist'), headers: await _headers())
        .timeout(_timeout);
    if (r.statusCode != 200) return {};
    return (jsonDecode(r.body) as List).map<int>((p) => p['id'] as int).toSet();
  }

  static Future<List<dynamic>> fetchWishlist() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as List : [];
  }

  static Future<bool> toggleWishlist(int id, bool add) async {
    final uri = Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist/$id');
    final h = await _headers();
    final r = add
        ? await http.post(uri, headers: h).timeout(_timeout)
        : await http.delete(uri, headers: h).timeout(_timeout);
    return r.statusCode == 200;
  }
}
