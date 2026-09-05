import 'package:flutter/material.dart';
import 'catalog_api.dart';
import 'product_detail_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU14] Prendas favoritas del cliente (móvil).
class WishlistView extends StatefulWidget {
  const WishlistView({super.key});

  @override
  State<WishlistView> createState() => _WishlistViewState();
}

class _WishlistViewState extends State<WishlistView> {
  List<dynamic> _products = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await CatalogApi.fetchWishlist();
    if (!mounted) return;
    setState(() { _products = p; _loading = false; });
  }

  Future<void> _remove(Map<String, dynamic> p) async {
    final ok = await CatalogApi.toggleWishlist(p['id'] as int, false);
    if (ok && mounted) setState(() => _products.removeWhere((x) => x['id'] == p['id']));
  }

  String? _img(Map<String, dynamic> p) {
    final imgs = p['images'] as List? ?? [];
    if (imgs.isEmpty) return null;
    final primary = imgs.firstWhere((i) => i['is_primary'] == true, orElse: () => imgs.first);
    final u = CatalogApi.resolveImage(primary['image_url'] as String?);
    return u.isEmpty ? null : u;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.white, elevation: 0,
        title: const Text('Mis favoritos', style: TextStyle(color: _ink, fontWeight: FontWeight.bold)),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : _products.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text('Todavía no has guardado prendas. Toca el ♥ en cualquier prenda para agregarla aquí.',
                        textAlign: TextAlign.center, style: TextStyle(color: _muted)),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  color: _brand,
                  child: GridView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _products.length,
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2, crossAxisSpacing: 14, mainAxisSpacing: 14, childAspectRatio: 0.68),
                    itemBuilder: (_, i) {
                      final p = _products[i] as Map<String, dynamic>;
                      final img = _img(p);
                      return GestureDetector(
                        onTap: () => Navigator.push(context,
                                MaterialPageRoute(builder: (_) => ProductDetailView(productId: p['id'] as int)))
                            .then((_) => _load()),
                        child: Container(
                          decoration: BoxDecoration(
                            color: Colors.white, borderRadius: BorderRadius.circular(16),
                            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 4))],
                          ),
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Expanded(
                              child: Stack(children: [
                                ClipRRect(
                                  borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                                  child: Container(
                                    width: double.infinity, color: const Color(0xFFF1EBE8),
                                    child: img != null
                                        ? Image.network(img, fit: BoxFit.cover,
                                            errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined, color: Color(0xFFD4CECB)))
                                        : const Center(child: Icon(Icons.image_outlined, size: 34, color: Color(0xFFD4CECB))),
                                  ),
                                ),
                                Positioned(top: 4, right: 4, child: GestureDetector(
                                  onTap: () => _remove(p),
                                  child: Container(
                                    width: 28, height: 28,
                                    decoration: const BoxDecoration(shape: BoxShape.circle, color: Colors.white70),
                                    child: const Icon(Icons.favorite, size: 15, color: _brand),
                                  ),
                                )),
                              ]),
                            ),
                            Padding(
                              padding: const EdgeInsets.all(10),
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text(p['name'] as String, maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink)),
                                Text('Bs. ${(p['base_price'] as num).toStringAsFixed(0)}',
                                    style: const TextStyle(fontWeight: FontWeight.bold, color: _brand, fontSize: 13)),
                              ]),
                            ),
                          ]),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
