import 'package:flutter/material.dart';
import 'catalog_api.dart';
import 'product_detail_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU11] Catálogo de la tienda (móvil): categorías, grilla lookbook con
/// foto/precio/oferta/★/♥. [CU14] toggle de favorito.
class CatalogoView extends StatefulWidget {
  const CatalogoView({super.key});

  @override
  State<CatalogoView> createState() => _CatalogoViewState();
}

class _CatalogoViewState extends State<CatalogoView> {
  List<dynamic> _products = [];
  List<dynamic> _categories = [];
  Map<int, Map<String, dynamic>> _ratings = {};
  Set<int> _wishlist = {};
  bool _loading = true;
  String _search = '';
  int? _catFilter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final results = await Future.wait([
      CatalogApi.fetchProducts(),
      CatalogApi.fetchCategories(),
      CatalogApi.fetchRatingsSummary(),
      CatalogApi.fetchWishlistIds(),
    ]);
    if (!mounted) return;
    setState(() {
      _products = results[0] as List;
      _categories = results[1] as List;
      _ratings = results[2] as Map<int, Map<String, dynamic>>;
      _wishlist = results[3] as Set<int>;
      _loading = false;
    });
  }

  List<dynamic> get _filtered {
    final t = _search.trim().toLowerCase();
    return _products.where((p) {
      final txt = t.isEmpty || '${p['name']} ${p['description'] ?? ''}'.toLowerCase().contains(t);
      final catId = p['category']?['id'] ?? p['category_id'];
      final cat = _catFilter == null || catId == _catFilter;
      return txt && cat;
    }).toList();
  }

  String? _primaryImage(Map<String, dynamic> p) {
    final imgs = p['images'] as List? ?? [];
    if (imgs.isEmpty) return null;
    final primary = imgs.firstWhere((i) => i['is_primary'] == true, orElse: () => imgs.first);
    final url = CatalogApi.resolveImage(primary['image_url'] as String?);
    return url.isEmpty ? null : url;
  }

  Future<void> _toggleWish(Map<String, dynamic> p) async {
    final id = p['id'] as int;
    final wished = _wishlist.contains(id);
    final ok = await CatalogApi.toggleWishlist(id, !wished);
    if (ok && mounted) {
      setState(() => wished ? _wishlist.remove(id) : _wishlist.add(id));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: const Text('FashionStore', style: TextStyle(color: _ink, fontWeight: FontWeight.bold)),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : RefreshIndicator(
              onRefresh: _load,
              color: _brand,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  // Buscador
                  TextField(
                    onChanged: (v) => setState(() => _search = v),
                    decoration: InputDecoration(
                      hintText: 'Buscar colecciones…',
                      prefixIcon: const Icon(Icons.search, color: _muted),
                      filled: true, fillColor: Colors.white, isDense: true,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Categorías
                  if (_categories.isNotEmpty) ...[
                    const Text('Categorías', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 84,
                      child: ListView(scrollDirection: Axis.horizontal, children: [
                        _catChip(null, 'Todas', null),
                        ..._categories.map((c) => _catChip(c['id'] as int, c['name'] as String, c['image_url'] as String?)),
                      ]),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Hero
                  if (_catFilter == null)
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(colors: [_brand, Color(0xFFA95848)]),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('TENDENCIAS DE TEMPORADA', style: TextStyle(color: Colors.white70, fontSize: 10, letterSpacing: 1.5)),
                        SizedBox(height: 4),
                        Text('La nueva colección ya está aquí',
                            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                        SizedBox(height: 4),
                        Text('Prendas femeninas para cada momento.', style: TextStyle(color: Colors.white70, fontSize: 12)),
                      ]),
                    ),
                  const SizedBox(height: 16),

                  Text(
                    _catFilter == null
                        ? 'Nuevos Ingresos'
                        : (_categories.firstWhere((c) => c['id'] == _catFilter, orElse: () => {'name': ''})['name'] as String),
                    style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
                  ),
                  const SizedBox(height: 8),

                  if (_filtered.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Center(child: Text('No hay prendas disponibles por el momento.', style: TextStyle(color: _muted))),
                    )
                  else
                    GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _filtered.length,
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2, crossAxisSpacing: 14, mainAxisSpacing: 14, childAspectRatio: 0.6),
                      itemBuilder: (_, i) => _card(_filtered[i] as Map<String, dynamic>),
                    ),
                ],
              ),
            ),
    );
  }

  Widget _catChip(int? id, String name, String? imageUrl) {
    final active = _catFilter == id;
    final url = imageUrl == null ? '' : CatalogApi.resolveImage(imageUrl);
    return GestureDetector(
      onTap: () => setState(() => _catFilter = id),
      child: Container(
        width: 64,
        margin: const EdgeInsets.only(right: 12),
        child: Column(children: [
          Container(
            width: 54, height: 54,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: id == null ? const Color(0xFFF6E3DD) : const Color(0xFFEFE7E3),
              border: Border.all(color: active ? _brand : Colors.transparent, width: 2),
              image: url.isNotEmpty ? DecorationImage(image: NetworkImage(url), fit: BoxFit.cover) : null,
            ),
            child: url.isEmpty
                ? Icon(id == null ? Icons.grid_view : Icons.checkroom, color: id == null ? _brand : const Color(0xFFA99C98), size: 20)
                : null,
          ),
          const SizedBox(height: 3),
          Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10, color: active ? _brand : _muted, fontWeight: active ? FontWeight.w600 : FontWeight.normal)),
        ]),
      ),
    );
  }

  Widget _card(Map<String, dynamic> p) {
    final img = _primaryImage(p);
    final base = (p['base_price'] as num).toDouble();
    final cmp = p['compare_at_price'] == null ? null : (p['compare_at_price'] as num).toDouble();
    final disc = p['discount_percent'] as int? ?? 0;
    final r = _ratings[p['id']];
    final wished = _wishlist.contains(p['id']);

    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ProductDetailView(productId: p['id'] as int)))
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
                          errorBuilder: (_, __, ___) => const Center(child: Icon(Icons.broken_image_outlined, size: 32, color: Color(0xFFD4CECB))))
                      : const Center(child: Icon(Icons.image_outlined, size: 36, color: Color(0xFFD4CECB))),
                ),
              ),
              if (disc > 0)
                Positioned(top: 6, left: 6, child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: const Color(0xFFD2624C), borderRadius: BorderRadius.circular(999)),
                  child: Text('-$disc%', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                )),
              Positioned(top: 4, right: 4, child: GestureDetector(
                onTap: () => _toggleWish(p),
                child: Container(
                  width: 28, height: 28,
                  decoration: const BoxDecoration(shape: BoxShape.circle, color: Colors.white70),
                  child: Icon(wished ? Icons.favorite : Icons.favorite_border, size: 15, color: wished ? _brand : _muted),
                ),
              )),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.all(10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p['category']?['name'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, color: _muted)),
              Text(p['name'] as String, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink)),
              const SizedBox(height: 3),
              Row(children: [
                Text('Bs. ${base.toStringAsFixed(0)}', style: const TextStyle(fontWeight: FontWeight.bold, color: _brand, fontSize: 13)),
                if (cmp != null) ...[
                  const SizedBox(width: 5),
                  Text('Bs. ${cmp.toStringAsFixed(0)}',
                      style: const TextStyle(decoration: TextDecoration.lineThrough, color: Color(0xFFA99C98), fontSize: 11)),
                ],
              ]),
              if (r != null && (r['count'] as int) > 0)
                Row(children: [
                  const Icon(Icons.star, size: 12, color: Color(0xFFE8B04B)),
                  const SizedBox(width: 2),
                  Text('${(r['average'] as num).toStringAsFixed(1)} (${r['count']})',
                      style: const TextStyle(fontSize: 11, color: _muted)),
                ]),
            ]),
          ),
        ]),
      ),
    );
  }
}
