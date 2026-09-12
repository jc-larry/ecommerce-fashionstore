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
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode != 200) return [];
      return (jsonDecode(r.body) as List).where((p) => p['is_active'] == true).toList();
    } catch (_) {
      return [];
    }
  }

  static Future<List<dynamic>> fetchCategories() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/categories'), headers: await _headers())
          .timeout(_timeout);
      return r.statusCode == 200 ? jsonDecode(r.body) as List : [];
    } catch (_) {
      return [];
    }
  }

  static Future<Map<String, dynamic>?> fetchProduct(int id) async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id'), headers: await _headers())
          .timeout(_timeout);
      return r.statusCode == 200 ? jsonDecode(r.body) as Map<String, dynamic> : null;
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>> fetchReviews(int id) async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id/reviews'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode == 200) return jsonDecode(r.body) as Map<String, dynamic>;
    } catch (_) {}
    return {'summary': {'average': 0, 'count': 0}, 'items': []};
  }

  static Future<bool> submitReview(int id, int rating, String comment) async {
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$id/reviews'),
            headers: await _headers(),
            body: jsonEncode({'rating': rating, 'comment': comment.isEmpty ? null : comment}),
          )
          .timeout(_timeout);
      return r.statusCode == 200 || r.statusCode == 201;
    } catch (_) {
      return false;
    }
  }

  static Future<Map<int, Map<String, dynamic>>> fetchRatingsSummary() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/ratings-summary'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode != 200) return {};
      final out = <int, Map<String, dynamic>>{};
      for (final x in jsonDecode(r.body) as List) {
        out[x['product_id'] as int] = {'average': x['average'], 'count': x['count']};
      }
      return out;
    } catch (_) {
      return {};
    }
  }

  static Future<Set<int>> fetchWishlistIds() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist'), headers: await _headers())
          .timeout(_timeout);
      if (r.statusCode != 200) return {};
      return (jsonDecode(r.body) as List).map<int>((p) => p['id'] as int).toSet();
    } catch (_) {
      return {};
    }
  }

  static Future<List<dynamic>> fetchWishlist() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist'), headers: await _headers())
          .timeout(_timeout);
      return r.statusCode == 200 ? jsonDecode(r.body) as List : [];
    } catch (_) {
      return [];
    }
  }

  static Future<bool> toggleWishlist(int id, bool add) async {
    final uri = Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlist/$id');
    final h = await _headers();
    final r = add
        ? await http.post(uri, headers: h).timeout(_timeout)
        : await http.delete(uri, headers: h).timeout(_timeout);
    return r.statusCode == 200;
  }

  // ---------- BÚSQUEDA Y DISPONIBILIDAD POR SUCURSAL (CU12) ----------
  static Future<Map<String, dynamic>?> fetchFilterOptions() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/filter-options'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as Map<String, dynamic> : null;
  }

  static Future<Map<String, dynamic>> searchProducts({
    String? q,
    int? categoryId,
    int? branchId,
    int? sizeId,
    int? colorId,
    double? minPrice,
    double? maxPrice,
    bool inStockOnly = false,
    String sortBy = 'newest',
    int page = 1,
    int limit = 30,
  }) async {
    final params = <String, String>{
      if (q != null && q.isNotEmpty) 'q': q,
      if (categoryId != null) 'category_id': categoryId.toString(),
      if (branchId != null) 'branch_id': branchId.toString(),
      if (sizeId != null) 'size_id': sizeId.toString(),
      if (colorId != null) 'color_id': colorId.toString(),
      if (minPrice != null) 'min_price': minPrice.toString(),
      if (maxPrice != null) 'max_price': maxPrice.toString(),
      if (inStockOnly) 'in_stock_only': 'true',
      'sort_by': sortBy,
      'page': page.toString(),
      'limit': limit.toString(),
    };

    final uri = Uri.parse('${AuthService.apiBaseUrl}/catalog/products/search').replace(queryParameters: params);
    final r = await http.get(uri, headers: await _headers()).timeout(_timeout);
    if (r.statusCode == 200) return jsonDecode(r.body) as Map<String, dynamic>;
    return {'items': [], 'total': 0, 'page': 1, 'limit': limit, 'total_pages': 1};
  }

  static Future<Map<String, dynamic>?> fetchProductBranchAvailability(int productId) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$productId/branch-availability'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as Map<String, dynamic> : null;
  }

  // ---------- PROMOCIONES Y CUPONES (CU13) ----------
  static Future<Map<String, dynamic>> validateCoupon(String code, double cartTotal) async {
    final uri = Uri.parse('${AuthService.apiBaseUrl}/catalog/coupons/validate');
    final r = await http.post(
      uri,
      headers: await _headers(),
      body: jsonEncode({'code': code, 'cart_total': cartTotal}),
    ).timeout(_timeout);
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  // ---------- WISHLISTS MÚLTIPLES Y COMPARTIBLES (CU14+) ----------
  static Future<List<dynamic>> fetchUserWishlists() async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlists'), headers: await _headers())
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as List : [];
  }

  static Future<Map<String, dynamic>?> createWishlist(String name, {bool isPublic = false}) async {
    final r = await http.post(
      Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlists'),
      headers: await _headers(),
      body: jsonEncode({'name': name, 'is_public': isPublic}),
    ).timeout(_timeout);
    return r.statusCode == 201 ? jsonDecode(r.body) as Map<String, dynamic> : null;
  }

  static Future<Map<String, dynamic>?> fetchSharedWishlist(String shareToken) async {
    final r = await http
        .get(Uri.parse('${AuthService.apiBaseUrl}/catalog/wishlists/shared/$shareToken'))
        .timeout(_timeout);
    return r.statusCode == 200 ? jsonDecode(r.body) as Map<String, dynamic> : null;
  }
}

