import 'package:flutter/material.dart';
import 'catalog_api.dart';
import '../ventas_y_pagos/ventas_api.dart';
import '../ventas_y_pagos/cart_view.dart';
import '../seguridad_y_usuarios/auth_service.dart';
import '../seguridad_y_usuarios/login_view.dart';
import '../reservas_y_citas/reserve_fitting_view.dart';
import '../inteligente_y_analitica/virtual_tryon_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU11] Detalle de prenda (móvil) + [CU14] reseñas y favorito.
/// Prenda multicolor: elegir color cambia fotos y tallas disponibles.
/// [CU12] Disponibilidad física por sucursal de la variante elegida.
/// [CU26] Reservar la prenda para probarla en una sucursal con stock.
class ProductDetailView extends StatefulWidget {
  final int productId;

  /// Talla a preseleccionar (p. ej. la recomendada por el vestidor virtual).
  final String? initialSizeName;
  const ProductDetailView({super.key, required this.productId, this.initialSizeName});

  @override
  State<ProductDetailView> createState() => _ProductDetailViewState();
}

class _ProductDetailViewState extends State<ProductDetailView> {
  Map<String, dynamic>? _product;
  List<dynamic> _reviews = [];
  double _ratingAvg = 0;
  int _ratingCount = 0;
  bool _loading = true;

  int? _colorId;
  int? _sizeId;
  bool _inWishlist = false;
  bool _addingToCart = false;

  int _myRating = 0;
  final _commentCtrl = TextEditingController();
  bool _savingReview = false;

  final _pageCtrl = PageController();
  int _page = 0;

  // [CU12] Stock por sucursal y datos de cada sucursal (horario, cierre temporal).
  Map<String, dynamic>? _availability;
  List<dynamic> _branches = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _commentCtrl.dispose();
    _pageCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final p = await CatalogApi.fetchProduct(widget.productId);
    final rv = await CatalogApi.fetchReviews(widget.productId);
    final wl = await CatalogApi.fetchWishlistIds();
    final av = await CatalogApi.fetchProductBranchAvailability(widget.productId);
    List<dynamic> branches = [];
    try {
      branches = await VentasApi.fetchBranches();
    } catch (_) {}
    if (!mounted) return;
    setState(() {
      _product = p;
      _reviews = rv['items'] as List;
      _ratingAvg = (rv['summary']['average'] as num).toDouble();
      _ratingCount = rv['summary']['count'] as int;
      _inWishlist = p != null && wl.contains(p['id']);
      _loading = false;
      final colors = _colors;
      _availability = av;
      _branches = branches;
      _colorId = colors.isNotEmpty ? colors.first['id'] as int : null;
      _syncSize();
      _applyInitialSize();
      for (final r in _reviews) {
        if (r['is_mine'] == true) {
          _myRating = r['rating'] as int;
          _commentCtrl.text = (r['comment'] ?? '') as String;
        }
      }
    });
  }

  List<Map<String, dynamic>> get _colors {
    final seen = <int, Map<String, dynamic>>{};
    for (final v in (_product?['variants'] as List? ?? [])) {
      final c = v['color'];
      if (c != null && !seen.containsKey(c['id'])) seen[c['id'] as int] = c as Map<String, dynamic>;
    }
    return seen.values.toList();
  }

  List<String> get _galleryUrls {
    final imgs = (_product?['images'] as List? ?? []);
    final forColor = imgs.where((i) => i['color_id'] == _colorId).toList();
    final chosen = forColor.isNotEmpty ? forColor : imgs;
    chosen.sort((a, b) => (b['is_primary'] == true ? 1 : 0) - (a['is_primary'] == true ? 1 : 0));
    return chosen.map<String>((i) => CatalogApi.resolveImage(i['image_url'] as String?)).toList();
  }

  /// Todas las tallas del producto, marcando cuáles hay para el color elegido.
  List<Map<String, dynamic>> get _sizeOptions {
    const order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', 'ÚNICA', 'UNICA'];
    final all = <int, String>{};
    for (final v in (_product?['variants'] as List? ?? [])) {
      all[v['size']['id'] as int] = v['size']['name'] as String;
    }
    final avail = (_product?['variants'] as List? ?? [])
        .where((v) => v['color_id'] == _colorId && v['is_active'] == true)
        .map((v) => v['size']['id'] as int)
        .toSet();
    final list = all.entries
        .map((e) => {'id': e.key, 'name': e.value, 'available': avail.contains(e.key)})
        .toList();
    int rk(String n) {
      final numVal = int.tryParse(n);
      if (numVal != null) return 100 + numVal;
      final i = order.indexOf(n.toUpperCase());
      return i < 0 ? 500 : i;
    }
    list.sort((a, b) => rk(a['name'] as String) - rk(b['name'] as String));
    return list;
  }

  void _syncSize() {
    final avail = _sizeOptions.where((s) => s['available'] == true).toList();
    _sizeId = avail.isNotEmpty ? avail.first['id'] as int : null;
  }

  /// Preselecciona la talla pedida (color incluido) si existe alguna variante activa con ella.
  void _applyInitialSize() {
    final wanted = widget.initialSizeName?.trim().toUpperCase();
    if (wanted == null || wanted.isEmpty) return;
    for (final v in (_product?['variants'] as List? ?? [])) {
      if (v['is_active'] == true && (v['size']?['name'] ?? '').toString().toUpperCase() == wanted) {
        _colorId = v['color_id'] as int?;
        _sizeId = v['size']['id'] as int?;
        return;
      }
    }
  }

  Future<void> _reloadAvailability() async {
    final av = await CatalogApi.fetchProductBranchAvailability(widget.productId);
    if (mounted) setState(() => _availability = av);
  }

  /// [CU12] Stock de la variante (color + talla) elegida en cada sucursal.
  List<Map<String, dynamic>> get _branchStock {
    final variants = (_availability?['variants'] as List?) ?? const [];
    Map<String, dynamic>? variant;
    for (final v in variants) {
      if (v['color_id'] == _colorId && v['size_id'] == _sizeId) {
        variant = Map<String, dynamic>.from(v as Map);
        break;
      }
    }
    if (variant == null) return const [];
    return ((variant['branches'] as List?) ?? const []).map<Map<String, dynamic>>((b) {
      final full = _branches.cast<Map?>().firstWhere(
            (br) => br?['id'] == b['branch_id'],
            orElse: () => null,
          ) ?? const {};
      final stock = (b['stock'] as num?)?.toInt() ?? 0;
      return {
        'id': b['branch_id'],
        'name': b['branch_name'] ?? full['name'] ?? 'Sucursal',
        'city': b['city'] ?? full['city'] ?? 'Santa Cruz',
        'stock': stock,
        'closed': full['is_temporarily_closed'] == true,
        'closure_reason': full['closure_reason'],
        'fitting_room': full['has_fitting_room'] ?? true,
        'opening_time': (full['opening_time'] ?? '09:00').toString(),
        'closing_time': (full['closing_time'] ?? '21:00').toString(),
        'days_open': (full['days_open'] ?? 'Lunes a Sábado').toString(),
      };
    }).toList()
      ..sort((a, b) => (b['stock'] as int).compareTo(a['stock'] as int));
  }

  String get _selectedColorName {
    for (final c in _colors) {
      if (c['id'] == _colorId) return (c['name'] ?? '').toString();
    }
    return '';
  }

  String get _selectedSizeName {
    for (final s in _sizeOptions) {
      if (s['id'] == _sizeId) return s['name'] as String;
    }
    return '';
  }

  /// [CU26] Abre la reserva para probador en la sucursal elegida (requiere sesión).
  Future<void> _reserveAt(Map<String, dynamic> branch) async {
    final vId = _selectedVariantExact;
    if (vId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona color y talla antes de reservar.')),
      );
      return;
    }
    if (!await AuthService.isLoggedIn()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Inicia sesión para reservar la prenda en probador.')),
      );
      Navigator.push(context, MaterialPageRoute(builder: (_) => const LoginView()));
      return;
    }
    if (!mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ReserveFittingView(
          variantId: vId,
          productName: (_product?['name'] ?? 'Prenda').toString(),
          colorName: _selectedColorName,
          sizeName: _selectedSizeName,
          unitPrice: (_product?['base_price'] as num).toDouble(),
          branch: FittingBranch(
            id: branch['id'] as int,
            name: branch['name'].toString(),
            city: branch['city'].toString(),
            stock: branch['stock'] as int,
            openingTime: branch['opening_time'] as String,
            closingTime: branch['closing_time'] as String,
            daysOpen: branch['days_open'] as String,
          ),
        ),
      ),
    );
    // La reserva descuenta stock en la sucursal: refrescar la disponibilidad.
    _reloadAvailability();
  }

  /// Variante exacta color + talla (sin caer en la primera variante como hace el carrito).
  int? get _selectedVariantExact {
    for (final v in (_product?['variants'] as List? ?? [])) {
      if (v['color_id'] == _colorId && v['size']?['id'] == _sizeId) return v['id'] as int;
    }
    return null;
  }

  Future<void> _toggleWishlist() async {
    final ok = await CatalogApi.toggleWishlist(widget.productId, !_inWishlist);
    if (ok && mounted) setState(() => _inWishlist = !_inWishlist);
  }

  Future<void> _submitReview() async {
    if (_myRating < 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Elige una calificación (1 a 5 estrellas).')),
      );
      return;
    }
    setState(() => _savingReview = true);
    final ok = await CatalogApi.submitReview(widget.productId, _myRating, _commentCtrl.text.trim());
    if (!mounted) return;
    setState(() => _savingReview = false);
    if (ok) {
      final rv = await CatalogApi.fetchReviews(widget.productId);
      if (!mounted) return;
      setState(() {
        _reviews = rv['items'] as List;
        _ratingAvg = (rv['summary']['average'] as num).toDouble();
        _ratingCount = rv['summary']['count'] as int;
      });
    }
  }

  int? get _selectedVariantId {
    if (_product == null || _colorId == null || _sizeId == null) return null;
    final vars = _product!['variants'] as List? ?? [];
    for (final v in vars) {
      if (v['color_id'] == _colorId && v['size']?['id'] == _sizeId) {
        return v['id'] as int;
      }
    }
    return vars.isNotEmpty ? vars.first['id'] as int : null;
  }

  Future<void> _addToCart() async {
    final vId = _selectedVariantId;
    if (vId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona color y talla disponibles.')),
      );
      return;
    }

    setState(() => _addingToCart = true);
    final res = await VentasApi.addToCart(vId, 1);
    if (!mounted) return;
    setState(() => _addingToCart = false);

    if (res['ok']) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('¡Prenda añadida al carrito!'),
          action: SnackBarAction(
            label: 'Ver Carrito',
            textColor: Colors.amberAccent,
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => const CartView()));
            },
          ),
        ),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['detail'] ?? 'Stock insuficiente.')),
      );
    }
  }

  void _sizeGuide() {
    final cat = (_product?['category']?['name'] ?? '').toString().toLowerCase();
    final isBottom = cat.contains('jean') || cat.contains('pant') || cat.contains('short') || cat.contains('falda') || cat.contains('inferior');
    final isShoe = cat.contains('calzado') || cat.contains('zapato') || cat.contains('sandalia') || cat.contains('bota');

    TableRow row(List<String> cells, {bool head = false}) => TableRow(
          children: cells
              .map((c) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Text(c, style: TextStyle(fontWeight: head ? FontWeight.bold : FontWeight.normal, fontSize: 13)),
                  ))
              .toList(),
        );

    showModalBottomSheet(
      context: context,
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            isShoe ? 'Guía de tallas Calzado (cm)' : (isBottom ? 'Guía de tallas Pantalones / Jeans (cm)' : 'Guía de tallas Ropa Femenina (cm)'),
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink),
          ),
          const SizedBox(height: 12),
          if (isShoe)
            Table(children: [
              row(['Talla (EU)', 'Largo del Pie (cm)'], head: true),
              row(['35', '22.5 cm']),
              row(['36', '23.0 cm']),
              row(['37', '23.5 cm']),
              row(['38', '24.5 cm']),
              row(['39', '25.0 cm']),
              row(['40', '25.5 cm']),
            ])
          else if (isBottom)
            Table(children: [
              row(['Talla', 'Cintura (cm)', 'Cadera (cm)'], head: true),
              row(['26 / XS', '60–64', '86–90']),
              row(['28 / S', '64–68', '90–94']),
              row(['30 / M', '68–74', '94–100']),
              row(['32 / L', '74–80', '100–106']),
              row(['34 / XL', '80–86', '106–112']),
              row(['36 / XXL', '86–94', '112–120']),
            ])
          else
            Table(children: [
              row(['Talla', 'Busto (cm)', 'Cintura (cm)', 'Cadera (cm)'], head: true),
              row(['XS', '80–84', '60–64', '86–90']),
              row(['S', '84–88', '64–68', '90–94']),
              row(['M', '88–92', '68–72', '94–98']),
              row(['L', '92–98', '72–78', '98–104']),
              row(['XL', '98–104', '78–84', '104–110']),
            ]),
          const SizedBox(height: 10),
          const Text('Si estás entre dos tallas, te recomendamos elegir la mayor para mayor comodidad.', style: TextStyle(fontSize: 12, color: _muted)),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: _ink,
        actions: [
          IconButton(
            icon: Icon(_inWishlist ? Icons.favorite : Icons.favorite_border, color: _brand),
            onPressed: _loading ? null : _toggleWishlist,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : _product == null
              ? const Center(child: Text('Esta prenda ya no está disponible.', style: TextStyle(color: _muted)))
              : _content(),
      bottomNavigationBar: _loading || _product == null ? null : _bottomBar(),
    );
  }

  /// Acciones principales fijas abajo: no se pierden al hacer scroll por la galería.
  Widget _bottomBar() {
    final base = (_product!['base_price'] as num).toDouble();
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 10, offset: const Offset(0, -2))],
        ),
        child: Row(children: [
          Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              _selectedSizeName.isEmpty ? 'Precio' : 'Talla $_selectedSizeName',
              style: const TextStyle(fontSize: 11, color: _muted),
            ),
            Text('Bs. ${base.toStringAsFixed(0)}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: _brand)),
          ]),
          const SizedBox(width: 10),
          IconButton.outlined(
            tooltip: 'Reservar en tienda',
            onPressed: _showReserveSheet,
            icon: const Icon(Icons.storefront_outlined, color: _brand),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: SizedBox(
              height: 46,
              child: ElevatedButton.icon(
                onPressed: _addingToCart ? null : _addToCart,
                icon: _addingToCart
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.shopping_bag_outlined, size: 20),
                label: Text(_addingToCart ? 'Añadiendo…' : 'Añadir al carrito', style: const TextStyle(fontSize: 14)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _content() {
    final p = _product!;
    final base = (p['base_price'] as num).toDouble();
    final cmp = p['compare_at_price'] == null ? null : (p['compare_at_price'] as num).toDouble();
    final disc = p['discount_percent'] as int? ?? 0;
    final urls = _galleryUrls;

    return ListView(
      children: [
        // Galería compacta: la prenda se ve completa y deja espacio para talla y acciones.
        SizedBox(
          height: (MediaQuery.of(context).size.height * 0.45).clamp(260.0, 440.0),
          child: Container(
            color: const Color(0xFFF3EEEB),
            child: Stack(children: [
              PageView.builder(
                controller: _pageCtrl,
                itemCount: urls.isEmpty ? 1 : urls.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) => urls.isEmpty
                    ? const Center(child: Icon(Icons.image_outlined, size: 48, color: Color(0xFFC9BCB7)))
                    : Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: Image.network(urls[i], fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => const Center(
                                child: Icon(Icons.broken_image_outlined, size: 40, color: Color(0xFFD4CECB)))),
                      ),
              ),
              if (disc > 0)
                Positioned(top: 12, left: 12, child: _pill('-$disc%', const Color(0xFFD2624C))),
              if (urls.length > 1)
                Positioned(
                  bottom: 10, right: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: Colors.black54, borderRadius: BorderRadius.circular(10)),
                    child: Text('${_page + 1}/${urls.length}', style: const TextStyle(color: Colors.white, fontSize: 11)),
                  ),
                ),
            ]),
          ),
        ),
        if (urls.length > 1)
          SizedBox(
            height: 64,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              itemCount: urls.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => GestureDetector(
                onTap: () => _pageCtrl.animateToPage(i, duration: const Duration(milliseconds: 250), curve: Curves.easeOut),
                child: Container(
                  width: 48,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: i == _page ? _brand : const Color(0xFFE5DFDC), width: i == _page ? 2 : 1),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: Image.network(urls[i], fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const SizedBox.shrink()),
                ),
              ),
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text((p['category']?['name'] ?? '').toString().toUpperCase(),
                style: const TextStyle(fontSize: 11, color: _muted, letterSpacing: 1)),
            const SizedBox(height: 4),
            Text(p['name'] as String, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 6),
            Row(children: [
              _stars(_ratingAvg),
              const SizedBox(width: 6),
              Text('${_ratingAvg.toStringAsFixed(1)} ($_ratingCount ${_ratingCount == 1 ? 'reseña' : 'reseñas'})',
                  style: const TextStyle(fontSize: 12, color: _muted)),
            ]),
            const SizedBox(height: 10),
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text('Bs. ${base.toStringAsFixed(0)}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: _brand)),
              if (cmp != null) ...[
                const SizedBox(width: 8),
                Text('Bs. ${cmp.toStringAsFixed(0)}', style: const TextStyle(decoration: TextDecoration.lineThrough, color: Color(0xFFA99C98))),
                const SizedBox(width: 6),
                Text('-$disc%', style: const TextStyle(color: Color(0xFF2E7D32), fontWeight: FontWeight.bold, fontSize: 13)),
              ],
            ]),
            const SizedBox(height: 16),

            // Color
            if (_colors.isNotEmpty) ...[
              const Text('Color', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
              const SizedBox(height: 8),
              Wrap(spacing: 10, children: _colors.map((c) {
                final selected = c['id'] == _colorId;
                return GestureDetector(
                  onTap: () => setState(() { _colorId = c['id'] as int; _page = 0; _syncSize(); }),
                  child: Container(
                    width: 32, height: 32,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _hex(c['hex_code'] as String?),
                      border: Border.all(color: selected ? _brand : const Color(0xFFD4CECB), width: selected ? 3 : 1),
                    ),
                  ),
                );
              }).toList()),
              const SizedBox(height: 16),
            ],

            // Talla
            if (_sizeOptions.isNotEmpty) ...[
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                const Text('Talla', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
                TextButton(onPressed: _sizeGuide, child: const Text('Guía de tallas', style: TextStyle(color: _brand))),
              ]),
              const SizedBox(height: 6),
              Wrap(spacing: 8, children: _sizeOptions.map((s) {
                final selected = s['id'] == _sizeId;
                final avail = s['available'] == true;
                return GestureDetector(
                  onTap: avail ? () => setState(() => _sizeId = s['id'] as int) : null,
                  child: Opacity(
                    opacity: avail ? 1 : 0.35,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: selected ? _brand : Colors.white,
                        border: Border.all(color: selected ? _brand : const Color(0xFFD4CECB)),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: Text(s['name'] as String,
                          style: TextStyle(fontWeight: FontWeight.w600, color: selected ? Colors.white : _ink)),
                    ),
                  ),
                );
              }).toList()),
              const SizedBox(height: 16),
            ],

            // Descripción
            if ((p['description'] ?? '').toString().isNotEmpty)
              ExpansionTile(
                title: const Text('Descripción', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
                tilePadding: EdgeInsets.zero,
                childrenPadding: const EdgeInsets.only(bottom: 12),
                initiallyExpanded: true,
                children: [Text(p['description'] as String, style: const TextStyle(color: _muted, fontSize: 13))],
              ),
            const SizedBox(height: 8),
            const Row(children: [
              Icon(Icons.local_shipping_outlined, size: 16, color: Color(0xFF2E7D32)),
              SizedBox(width: 6),
              Text('Entrega estimada: 3–5 días hábiles', style: TextStyle(fontSize: 12, color: Color(0xFF2E7D32))),
            ]),
            const SizedBox(height: 16),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _showReserveSheet,
                  icon: const Icon(Icons.storefront_outlined, size: 18),
                  label: const Text('Reservar en tienda', style: TextStyle(fontSize: 13)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => VirtualTryonView(
                        initialProductId: widget.productId,
                        initialProductName: (_product?['name'] ?? '').toString(),
                        initialProduct: _product,
                      ),
                    ),
                  ),
                  icon: const Icon(Icons.checkroom, size: 18),
                  label: const Text('Vestidor virtual', style: TextStyle(fontSize: 13)),
                ),
              ),
            ]),

            const SizedBox(height: 20),
            _availabilitySection(),

            const Divider(height: 36),
            _reviewsSection(),
          ]),
        ),
      ],
    );
  }

  /// [CU26] Hoja con las sucursales que tienen la talla/color elegidos para reservar.
  void _showReserveSheet() {
    final options = _branchStock
        .where((b) => (b['stock'] as int) > 0 && b['closed'] != true && b['fitting_room'] != false)
        .toList();
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Reservar para probar en tienda', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 4),
            Text(
              'Talla $_selectedSizeName · $_selectedColorName. Pagas una seña del 50 % y la prenda se aparta 48 h.',
              style: const TextStyle(fontSize: 12, color: _muted),
            ),
            const SizedBox(height: 12),
            if (options.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 12),
                child: Text('Ninguna sucursal tiene stock de esta talla y color. Prueba otra combinación.',
                    style: TextStyle(color: _muted)),
              )
            else
              ...options.map((b) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.storefront_outlined, color: _brand),
                    title: Text('${b['name']}'),
                    subtitle: Text('${b['city']} · ${b['opening_time']} - ${b['closing_time']} · ${b['stock']} en stock'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      Navigator.pop(ctx);
                      _reserveAt(b);
                    },
                  )),
          ]),
        ),
      ),
    );
  }

  /// [CU12 / CU26] Disponibilidad por sucursal de la talla/color elegidos + reserva en probador.
  Widget _availabilitySection() {
    final list = _branchStock;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Disponible en tiendas', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: _ink)),
      const SizedBox(height: 4),
      Text(
        _selectedSizeName.isEmpty
            ? 'Elige color y talla para ver el stock en cada sucursal.'
            : 'Talla $_selectedSizeName · $_selectedColorName. Reserva y pruébatela en tienda (seña 50 %, se aparta 48 h).',
        style: const TextStyle(fontSize: 12, color: _muted),
      ),
      const SizedBox(height: 10),
      if (_availability == null)
        const Text('No se pudo consultar el stock por sucursal.', style: TextStyle(fontSize: 12, color: _muted))
      else if (list.isEmpty)
        const Text('Sin stock en sucursales para esta combinación.', style: TextStyle(fontSize: 12, color: _muted))
      else
        ...list.map((b) {
          final stock = b['stock'] as int;
          final closed = b['closed'] == true;
          final canReserve = stock > 0 && !closed && b['fitting_room'] != false;
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE5DFDC)),
            ),
            child: Row(children: [
              Icon(Icons.storefront_outlined, color: stock > 0 && !closed ? _brand : const Color(0xFFC9BCB7)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${b['name']}', style: const TextStyle(fontWeight: FontWeight.w600, color: _ink)),
                  Text(
                    closed
                        ? 'Cerrada temporalmente${b['closure_reason'] != null ? ' (${b['closure_reason']})' : ''}'
                        : '${b['city']} · ${b['opening_time']} - ${b['closing_time']}',
                    style: TextStyle(fontSize: 11, color: closed ? Colors.red.shade700 : _muted),
                  ),
                  Text(
                    stock > 0 ? '$stock ${stock == 1 ? 'unidad' : 'unidades'}' : 'Agotado',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: stock > 0 ? Colors.green.shade700 : Colors.red.shade700),
                  ),
                ]),
              ),
              if (canReserve)
                TextButton(
                  onPressed: () => _reserveAt(b),
                  child: const Text('Reservar', style: TextStyle(color: _brand, fontWeight: FontWeight.bold)),
                ),
            ]),
          );
        }),
    ]);
  }

  Widget _reviewsSection() {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Reseñas', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: _ink)),
      const SizedBox(height: 8),
      Row(children: [
        Text(_ratingAvg.toStringAsFixed(1), style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
        const SizedBox(width: 8),
        _stars(_ratingAvg),
        const SizedBox(width: 8),
        Text('· $_ratingCount ${_ratingCount == 1 ? 'reseña' : 'reseñas'}', style: const TextStyle(color: _muted, fontSize: 12)),
      ]),
      const SizedBox(height: 12),
      Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 4)),
        ]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(_myRating > 0 ? 'Actualiza tu reseña' : 'Deja tu opinión',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink)),
          const SizedBox(height: 6),
          Row(children: List.generate(5, (i) => IconButton(
            padding: EdgeInsets.zero, constraints: const BoxConstraints(),
            icon: Icon(i < _myRating ? Icons.star : Icons.star_border, color: const Color(0xFFE8B04B), size: 28),
            onPressed: () => setState(() => _myRating = i + 1),
          ))),
          const SizedBox(height: 6),
          TextField(
            controller: _commentCtrl,
            maxLines: 2,
            decoration: InputDecoration(
              hintText: 'Cuéntanos qué te pareció…',
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              isDense: true,
            ),
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: _savingReview ? null : _submitReview,
            style: ElevatedButton.styleFrom(backgroundColor: _brand, foregroundColor: Colors.white),
            child: Text(_savingReview ? 'Guardando…' : (_myRating > 0 ? 'Actualizar mi reseña' : 'Publicar reseña')),
          ),
        ]),
      ),
      const SizedBox(height: 12),
      if (_reviews.isEmpty)
        const Text('Sé la primera en opinar sobre esta prenda.', style: TextStyle(color: _muted, fontSize: 13)),
      ..._reviews.map((r) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('${r['author_name']}${r['is_mine'] == true ? ' (tú)' : ''}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                Text((r['created_at'] as String).substring(0, 10), style: const TextStyle(fontSize: 11, color: _muted)),
              ]),
              _stars((r['rating'] as int).toDouble(), size: 14),
              if ((r['comment'] ?? '').toString().isNotEmpty)
                Text(r['comment'] as String, style: const TextStyle(color: _muted, fontSize: 13)),
            ]),
          )),
    ]);
  }

  Widget _stars(double v, {double size = 16}) => Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(5, (i) => Icon(
          i < (v + 0.5).floor() ? Icons.star : Icons.star_border,
          color: const Color(0xFFE8B04B), size: size,
        )),
      );

  Widget _pill(String text, Color bg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(999)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
      );

  Color _hex(String? h) {
    if (h == null || h.length < 7) return const Color(0xFFCCCCCC);
    return Color(int.parse('FF${h.substring(1)}', radix: 16));
  }
}
