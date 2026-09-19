import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../catalogo_y_tiendas/catalog_api.dart';
import '../seguridad_y_usuarios/auth_service.dart';
import '../catalogo_y_tiendas/product_detail_view.dart';
import '../ventas_y_pagos/ventas_api.dart';
import '../ventas_y_pagos/cart_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);
const _bg = Color(0xFFF8F6F4);

/// [CU32] Probador Virtual RA y Asesor Biométrico de Tallas (App Móvil).
/// Permite al cliente seleccionar visualmente cualquier prenda del catálogo con su fotografía,
/// simular cómo le queda en el vestidor virtual (maniquí, modelo o foto real),
/// calcular su talla biométrica ideal (S/M/L/XL) y proceder a compra o reserva en tienda.
class VirtualTryonView extends StatefulWidget {
  final int? initialProductId;
  final String? initialProductName;
  final Map<String, dynamic>? initialProduct;

  const VirtualTryonView({
    super.key,
    this.initialProductId,
    this.initialProductName,
    this.initialProduct,
  });

  @override
  State<VirtualTryonView> createState() => _VirtualTryonViewState();
}

class _VirtualTryonViewState extends State<VirtualTryonView> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Controladores de Medidas Biométricas
  final TextEditingController _heightCtrl = TextEditingController(text: '170');
  final TextEditingController _weightCtrl = TextEditingController(text: '65');
  final TextEditingController _chestCtrl = TextEditingController(text: '94');
  final TextEditingController _waistCtrl = TextEditingController(text: '78');

  String _gender = 'female';
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _result;

  // Catálogo de Prendas
  List<dynamic> _products = [];
  List<dynamic> _categories = [];
  int? _selectedProductId;
  Map<String, dynamic>? _selectedProduct;

  // Controles del Probador Visual (Espejo Inteligente / RA)
  String _visualMode = 'mannequin'; // 'mannequin', 'model', 'photo'
  String? _userCustomPhotoUrl;
  double _overlayScale = 1.0;
  double _overlayOffsetY = 0.0;
  double _overlayOpacity = 0.95;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _selectedProductId = widget.initialProductId;
    _selectedProduct = widget.initialProduct;
    _loadCatalogAndCategories();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _heightCtrl.dispose();
    _weightCtrl.dispose();
    _chestCtrl.dispose();
    _waistCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadCatalogAndCategories() async {
    setState(() => _loading = true);
    try {
      final prods = await CatalogApi.fetchProducts();
      final cats = await CatalogApi.fetchCategories();

      if (mounted) {
        setState(() {
          _products = prods;
          _categories = cats;
          _loading = false;

          // Seleccionar prenda inicial si no está seleccionada
          if (_products.isNotEmpty) {
            if (_selectedProductId != null) {
              final match = _products.firstWhere(
                (p) => p['id'] == _selectedProductId,
                orElse: () => _products.first,
              );
              _selectedProduct = match as Map<String, dynamic>?;
              _selectedProductId = _selectedProduct?['id'] as int?;
            } else {
              _selectedProduct = _products.first as Map<String, dynamic>?;
              _selectedProductId = _selectedProduct?['id'] as int?;
            }
          }
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _getGarmentImage(Map<String, dynamic>? p) {
    if (p == null) return null;
    final imgs = p['images'] as List?;
    if (imgs != null && imgs.isNotEmpty) {
      final prim = imgs.firstWhere((i) => i['is_primary'] == true, orElse: () => imgs.first);
      final raw = prim['image_url'] ?? prim['url'];
      if (raw != null && raw.toString().isNotEmpty) {
        return CatalogApi.resolveImage(raw.toString());
      }
    }
    if (p['primary_image_url'] != null && p['primary_image_url'].toString().isNotEmpty) {
      return CatalogApi.resolveImage(p['primary_image_url'].toString());
    }
    if (p['image_url'] != null && p['image_url'].toString().isNotEmpty) {
      return CatalogApi.resolveImage(p['image_url'].toString());
    }
    return null;
  }

  void _selectProduct(Map<String, dynamic> p) {
    setState(() {
      _selectedProduct = p;
      _selectedProductId = p['id'] as int;
      _result = null; // Reiniciar simulación para la nueva prenda
    });
  }

  /// Abrir modal visual completo para explorar y seleccionar cualquier prenda con fotos y filtros
  void _openVisualCatalogPicker() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        String searchQuery = '';
        int? categoryFilter;

        return StatefulBuilder(
          builder: (context, setModalState) {
            final filtered = _products.where((p) {
              final nameMatch = (p['name'] ?? '').toString().toLowerCase().contains(searchQuery.toLowerCase()) ||
                  (p['category']?['name'] ?? '').toString().toLowerCase().contains(searchQuery.toLowerCase());
              final catMatch = categoryFilter == null || p['category_id'] == categoryFilter;
              return nameMatch && catMatch;
            }).toList();

            return Container(
              height: MediaQuery.of(context).size.height * 0.85,
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
              ),
              child: Column(
                children: [
                  // Handle bar
                  Container(
                    margin: const EdgeInsets.only(top: 12, bottom: 8),
                    width: 44,
                    height: 5,
                    decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(10)),
                  ),
                  // Header
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Elige una Prenda', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink)),
                            Text('Toca la foto para probarla en el vestidor', style: TextStyle(fontSize: 12, color: _muted)),
                          ],
                        ),
                        IconButton(
                          onPressed: () => Navigator.pop(ctx),
                          icon: const Icon(Icons.close),
                        ),
                      ],
                    ),
                  ),
                  // Barra de búsqueda
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    child: TextField(
                      decoration: InputDecoration(
                        hintText: 'Buscar vestido, blusa, top, conjunto...',
                        prefixIcon: const Icon(Icons.search, color: _brand),
                        filled: true,
                        fillColor: const Color(0xFFF6F3F1),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14),
                          borderSide: BorderSide.none,
                        ),
                        contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
                      ),
                      onChanged: (val) => setModalState(() => searchQuery = val),
                    ),
                  ),
                  // Filtro de categorías
                  if (_categories.isNotEmpty)
                    SizedBox(
                      height: 44,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: FilterChip(
                              label: const Text('Todas', style: TextStyle(fontSize: 12)),
                              selected: categoryFilter == null,
                              selectedColor: _brand.withValues(alpha: 0.18),
                              checkmarkColor: _brand,
                              onSelected: (_) => setModalState(() => categoryFilter = null),
                            ),
                          ),
                          ..._categories.map((c) => Padding(
                                padding: const EdgeInsets.only(right: 6),
                                child: FilterChip(
                                  label: Text(c['name'] ?? '', style: const TextStyle(fontSize: 12)),
                                  selected: categoryFilter == c['id'],
                                  selectedColor: _brand.withValues(alpha: 0.18),
                                  checkmarkColor: _brand,
                                  onSelected: (_) => setModalState(() => categoryFilter = c['id']),
                                ),
                              )),
                        ],
                      ),
                    ),
                  const Divider(height: 1),
                  // Grilla de fotos de prendas
                  Expanded(
                    child: filtered.isEmpty
                        ? const Center(
                            child: Text('No hay prendas con ese criterio', style: TextStyle(color: _muted)),
                          )
                        : GridView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: filtered.length,
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              crossAxisSpacing: 12,
                              mainAxisSpacing: 12,
                              childAspectRatio: 0.68,
                            ),
                            itemBuilder: (_, i) {
                              final item = filtered[i] as Map<String, dynamic>;
                              final isSelected = item['id'] == _selectedProductId;
                              final img = _getGarmentImage(item);
                              final price = (item['base_price'] as num?)?.toDouble() ?? 0;

                              return GestureDetector(
                                onTap: () {
                                  _selectProduct(item);
                                  Navigator.pop(ctx);
                                },
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                      color: isSelected ? _brand : const Color(0xFFEFE7E3),
                                      width: isSelected ? 2.5 : 1,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: isSelected ? _brand.withValues(alpha: 0.2) : Colors.black.withValues(alpha: 0.04),
                                        blurRadius: isSelected ? 8 : 4,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                  ),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                        child: Stack(
                                          children: [
                                            ClipRRect(
                                              borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
                                              child: Container(
                                                width: double.infinity,
                                                color: const Color(0xFFFAFAFA),
                                                child: img != null
                                                    ? Image.network(
                                                        img,
                                                        fit: BoxFit.contain,
                                                        errorBuilder: (_, __, ___) =>
                                                            const Icon(Icons.broken_image, color: Colors.grey),
                                                      )
                                                    : const Icon(Icons.checkroom, color: Colors.grey, size: 40),
                                              ),
                                            ),
                                            if (isSelected)
                                              Positioned(
                                                top: 6,
                                                right: 6,
                                                child: Container(
                                                  padding: const EdgeInsets.all(4),
                                                  decoration: const BoxDecoration(shape: BoxShape.circle, color: _brand),
                                                  child: const Icon(Icons.check, size: 14, color: Colors.white),
                                                ),
                                              ),
                                          ],
                                        ),
                                      ),
                                      Padding(
                                        padding: const EdgeInsets.all(8),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              item['category']?['name'] ?? 'Prenda',
                                              style: const TextStyle(fontSize: 10, color: _muted),
                                              maxLines: 1,
                                            ),
                                            Text(
                                              item['name'] ?? '',
                                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _ink),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                            const SizedBox(height: 2),
                                            Text(
                                              'Bs. ${price.toStringAsFixed(0)}',
                                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _pickCustomPhoto() async {
    final picker = ImagePicker();
    final photo = await picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
    if (photo != null) {
      final bytes = await photo.readAsBytes();
      setState(() {
        _userCustomPhotoUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
        _visualMode = 'photo';
      });
    }
  }

  Future<void> _takeCameraPhoto() async {
    final picker = ImagePicker();
    final photo = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
    if (photo != null) {
      final bytes = await photo.readAsBytes();
      setState(() {
        _userCustomPhotoUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
        _visualMode = 'photo';
      });
    }
  }

  Future<void> _calculateFitAndTryon() async {
    final h = double.tryParse(_heightCtrl.text) ?? 170;
    final w = double.tryParse(_weightCtrl.text) ?? 65;
    final ch = double.tryParse(_chestCtrl.text) ?? 94;
    final wa = double.tryParse(_waistCtrl.text) ?? 78;

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/analytics/tryon/simulate');
      final res = await http.post(
        url,
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'product_id': _selectedProductId ?? 1,
          'height_cm': h,
          'weight_kg': w,
          'chest_cm': ch,
          'waist_cm': wa,
          'gender': _gender,
        }),
      ).timeout(const Duration(seconds: 15));

      if (!mounted) return;

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _result = data is Map<String, dynamic> ? data : null;
          _loading = false;
        });
      } else {
        setState(() {
          _loading = false;
          _error = 'No se pudo realizar la simulación biométrica (código ${res.statusCode}).';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Error de conexión con el motor de IA biométrica: $e';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentGarmentImg = _getGarmentImage(_selectedProduct);

    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        title: const Text('Vestidor Virtual & Probador', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: Colors.white,
        foregroundColor: _ink,
        elevation: 0.5,
        actions: [
          IconButton(
            icon: const Icon(Icons.grid_view_rounded, color: _brand),
            tooltip: 'Ver Catálogo Completo',
            onPressed: _openVisualCatalogPicker,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.only(bottom: 30),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ==========================================
            // 1. FICHA VISUAL DE LA PRENDA SELECCIONADA
            // ==========================================
            Container(
              margin: const EdgeInsets.all(16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFFEFE7E3)),
                boxShadow: [
                  BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 4)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: _brand.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              _selectedProduct?['category']?['name']?.toString().toUpperCase() ?? 'PRENDA',
                              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: _brand, letterSpacing: 0.8),
                            ),
                          ),
                          const SizedBox(width: 8),
                          if (_selectedProduct?['code'] != null)
                            Text(
                              'Ref: ${_selectedProduct?['code']}',
                              style: const TextStyle(fontSize: 11, color: _muted),
                            ),
                        ],
                      ),
                      TextButton.icon(
                        onPressed: _openVisualCatalogPicker,
                        icon: const Icon(Icons.swap_horiz, size: 16, color: _brand),
                        label: const Text('Cambiar Prenda', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand)),
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          backgroundColor: const Color(0xFFFBF4F2),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Fotografía grande en fondo blanco de estudio
                      Container(
                        width: 105,
                        height: 130,
                        decoration: BoxDecoration(
                          color: const Color(0xFFFAFAFA),
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFFECE6E2)),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: currentGarmentImg != null
                              ? Image.network(
                                  currentGarmentImg,
                                  fit: BoxFit.contain,
                                  errorBuilder: (_, __, ___) => const Icon(Icons.broken_image, color: Colors.grey, size: 36),
                                )
                              : const Icon(Icons.checkroom, color: Colors.grey, size: 44),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _selectedProduct?['name'] ?? 'Prenda seleccionada',
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: _ink),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                Text(
                                  'Bs. ${((_selectedProduct?['base_price'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}',
                                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _brand),
                                ),
                                if (_selectedProduct?['compare_at_price'] != null) ...[
                                  const SizedBox(width: 8),
                                  Text(
                                    'Bs. ${((_selectedProduct?['compare_at_price'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}',
                                    style: const TextStyle(
                                      fontSize: 13,
                                      color: Colors.grey,
                                      decoration: TextDecoration.lineThrough,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.green.shade200),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.check_circle, size: 13, color: Colors.green),
                                  SizedBox(width: 4),
                                  Text('Lista para probarse en vivo', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.green)),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // ========================================================
            // 2. CARRUSEL HORIZONTAL DE PRENDAS CON FOTOS (RACK VIVO)
            // ========================================================
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Prendas de Colección', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _ink)),
                  GestureDetector(
                    onTap: _openVisualCatalogPicker,
                    child: const Text('Ver todas las fotos ›', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: _brand)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: 120,
              child: _products.isEmpty
                  ? const Center(child: CircularProgressIndicator(color: _brand))
                  : ListView.builder(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemCount: _products.length,
                      itemBuilder: (_, idx) {
                        final p = _products[idx] as Map<String, dynamic>;
                        final isSel = p['id'] == _selectedProductId;
                        final img = _getGarmentImage(p);

                        return GestureDetector(
                          onTap: () => _selectProduct(p),
                          child: Container(
                            width: 82,
                            margin: const EdgeInsets.only(right: 10),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: isSel ? _brand : const Color(0xFFE8DFDB),
                                width: isSel ? 2.5 : 1,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: isSel ? _brand.withValues(alpha: 0.2) : Colors.black.withValues(alpha: 0.03),
                                  blurRadius: isSel ? 6 : 2,
                                  offset: const Offset(0, 2),
                                ),
                              ],
                            ),
                            child: Column(
                              children: [
                                Expanded(
                                  child: Stack(
                                    children: [
                                      ClipRRect(
                                        borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                                        child: Container(
                                          width: double.infinity,
                                          color: const Color(0xFFFAFAFA),
                                          child: img != null
                                              ? Image.network(
                                                  img,
                                                  fit: BoxFit.contain,
                                                  errorBuilder: (_, __, ___) => const Icon(Icons.broken_image, size: 20, color: Colors.grey),
                                                )
                                              : const Icon(Icons.checkroom, size: 24, color: Colors.grey),
                                        ),
                                      ),
                                      if (isSel)
                                        Positioned(
                                          top: 3,
                                          right: 3,
                                          child: Container(
                                            padding: const EdgeInsets.all(2),
                                            decoration: const BoxDecoration(shape: BoxShape.circle, color: _brand),
                                            child: const Icon(Icons.check, size: 10, color: Colors.white),
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                                  child: Column(
                                    children: [
                                      Text(
                                        p['name'] ?? '',
                                        style: TextStyle(
                                          fontSize: 9,
                                          fontWeight: isSel ? FontWeight.bold : FontWeight.normal,
                                          color: isSel ? _brand : _ink,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      Text(
                                        'Bs. ${((p['base_price'] as num?)?.toDouble() ?? 0).toStringAsFixed(0)}',
                                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: _brand),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            const SizedBox(height: 16),

            // ==========================================
            // 3. PESTAÑAS: PROBADOR VISUAL & ASESOR BIOMÉTRICO
            // ==========================================
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFECE6E2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    color: _brand,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  labelColor: Colors.white,
                  unselectedLabelColor: _ink,
                  labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  tabs: const [
                    Tab(icon: Icon(Icons.auto_awesome, size: 18), text: 'Asesor Biométrico'),
                    Tab(icon: Icon(Icons.checkroom, size: 18), text: 'Probador Visual RA'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),

            // CONTENIDO DE LAS PESTAÑAS
            AnimatedBuilder(
              animation: _tabController,
              builder: (context, _) {
                if (_tabController.index == 0) {
                  return _buildBiometricAdvisorTab();
                } else {
                  return _buildVisualMirrorTab(currentGarmentImg);
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // TAB 1: ASESOR BIOMÉTRICO Y TALLAS
  // ==========================================
  Widget _buildBiometricAdvisorTab() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFECE6E2)),
              boxShadow: [
                BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 8, offset: const Offset(0, 3)),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Tus Medidas Corporales', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: _ink)),
                    Row(
                      children: [
                        ChoiceChip(
                          label: const Text('Mujer', style: TextStyle(fontSize: 11)),
                          selected: _gender == 'female',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (_) => setState(() => _gender = 'female'),
                        ),
                        const SizedBox(width: 6),
                        ChoiceChip(
                          label: const Text('Varón', style: TextStyle(fontSize: 11)),
                          selected: _gender == 'male',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (_) => setState(() => _gender = 'male'),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _heightCtrl,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Estatura (cm)',
                          prefixIcon: const Icon(Icons.height, size: 18),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _weightCtrl,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Peso (kg)',
                          prefixIcon: const Icon(Icons.monitor_weight_outlined, size: 18),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _chestCtrl,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Busto / Pecho (cm)',
                          prefixIcon: const Icon(Icons.straighten, size: 18),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _waistCtrl,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: 'Cintura (cm)',
                          prefixIcon: const Icon(Icons.straighten, size: 18),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: _loading ? null : _calculateFitAndTryon,
                  icon: _loading
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Icon(Icons.auto_awesome, color: Colors.white),
                  label: Text(
                    _loading ? 'Simulando vestidor con IA...' : 'Simular Vestidor y Recomendar Talla',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _brand,
                    minimumSize: const Size.fromHeight(48),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          if (_error != null)
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
            ),

          if (_result != null) _buildTryonResultCard(),
        ],
      ),
    );
  }

  // ==========================================
  // TAB 2: PROBADOR VISUAL (ESPEJO INTELIGENTE)
  // ==========================================
  Widget _buildVisualMirrorTab(String? currentGarmentImg) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          // Selector de Silueta / Maniquí / Cámara
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFECE6E2)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ChoiceChip(
                  avatar: const Icon(Icons.person, size: 16),
                  label: const Text('Maniquí', style: TextStyle(fontSize: 12)),
                  selected: _visualMode == 'mannequin',
                  selectedColor: _brand.withValues(alpha: 0.15),
                  onSelected: (_) => setState(() => _visualMode = 'mannequin'),
                ),
                ChoiceChip(
                  avatar: const Icon(Icons.camera_alt, size: 16),
                  label: const Text('Cámara', style: TextStyle(fontSize: 12)),
                  selected: _visualMode == 'photo',
                  selectedColor: _brand.withValues(alpha: 0.15),
                  onSelected: (_) => _takeCameraPhoto(),
                ),
                ChoiceChip(
                  avatar: const Icon(Icons.photo_library, size: 16),
                  label: const Text('Mi Foto', style: TextStyle(fontSize: 12)),
                  selected: _visualMode == 'photo' && _userCustomPhotoUrl != null,
                  selectedColor: _brand.withValues(alpha: 0.15),
                  onSelected: (_) => _pickCustomPhoto(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Escenario del Vestidor (Espejo 9:16)
          Container(
            height: 380,
            width: double.infinity,
            decoration: BoxDecoration(
              color: const Color(0xFFEFEFEF),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFD6CDC8), width: 1.5),
              boxShadow: [
                BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 12, offset: const Offset(0, 4)),
              ],
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                // 1. Fondo de silueta / foto
                if (_visualMode == 'mannequin' || _userCustomPhotoUrl == null)
                  Center(
                    child: Opacity(
                      opacity: 0.35,
                      child: Icon(
                        _gender == 'female' ? Icons.woman : Icons.man,
                        size: 280,
                        color: Colors.grey.shade600,
                      ),
                    ),
                  )
                else if (_userCustomPhotoUrl != null)
                  Positioned.fill(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: Image.memory(
                        base64Decode(_userCustomPhotoUrl!.split(',').last),
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),

                // 2. Prenda superpuesta con controles de posición
                if (currentGarmentImg != null)
                  Transform.translate(
                    offset: Offset(0, _overlayOffsetY),
                    child: Transform.scale(
                      scale: _overlayScale,
                      child: Opacity(
                        opacity: _overlayOpacity,
                        child: Image.network(
                          currentGarmentImg,
                          height: 220,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => const Icon(Icons.checkroom, size: 80, color: _brand),
                        ),
                      ),
                    ),
                  ),

                // Badge de prenda y talla
                Positioned(
                  top: 12,
                  right: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          _selectedProduct?['name'] ?? '',
                          style: const TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.bold),
                          maxLines: 1,
                        ),
                        Text(
                          'Talla: ${_result?['recommended_size'] ?? 'M'}',
                          style: const TextStyle(fontSize: 11, color: Color(0xFFF6C28B), fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Ajustes finos de la prenda en el vestidor
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFFECE6E2)),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(Icons.aspect_ratio, size: 18, color: _muted),
                    const SizedBox(width: 8),
                    const Text('Escala:', style: TextStyle(fontSize: 12, color: _muted)),
                    Expanded(
                      child: Slider(
                        value: _overlayScale,
                        min: 0.7,
                        max: 1.4,
                        activeColor: _brand,
                        onChanged: (v) => setState(() => _overlayScale = v),
                      ),
                    ),
                  ],
                ),
                Row(
                  children: [
                    const Icon(Icons.vertical_align_center, size: 18, color: _muted),
                    const SizedBox(width: 8),
                    const Text('Altura:', style: TextStyle(fontSize: 12, color: _muted)),
                    Expanded(
                      child: Slider(
                        value: _overlayOffsetY,
                        min: -50,
                        max: 50,
                        activeColor: _brand,
                        onChanged: (v) => setState(() => _overlayOffsetY = v),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ==========================================
  // TARJETA DE RESULTADO DE LA SIMULACIÓN
  // ==========================================
  Widget _buildTryonResultCard() {
    final r = _result!;
    final size = r['recommended_size'] ?? 'M';
    final fit = r['fit_assessment'] ?? 'Ajuste Regular Óptimo';
    final advice = r['style_advice'] ?? 'Excelente caída de hombros y talle.';
    final confidence = (r['confidence_score'] ?? 95).toString();
    final currentGarmentImg = _getGarmentImage(_selectedProduct);

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _brand, width: 2),
        boxShadow: [
          BoxShadow(color: _brand.withValues(alpha: 0.12), blurRadius: 14, offset: const Offset(0, 4)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.verified, color: Colors.green, size: 22),
                  SizedBox(width: 8),
                  Text('Talla y Calce Recomendado', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: _ink)),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.green.shade300),
                ),
                child: Text('$confidence% precisión IA', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.green.shade800)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              if (currentGarmentImg != null)
                Container(
                  width: 75,
                  height: 90,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFAFAFA),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFECE6E2)),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(currentGarmentImg, fit: BoxFit.contain),
                  ),
                ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Tu talla calculada para esta prenda es:', style: TextStyle(fontSize: 12, color: _muted)),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 6),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6E3DD),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: _brand, width: 1.5),
                      ),
                      child: Text(
                        'TALLA $size',
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _brand),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(fit, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: _ink)),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          const Text('Consejo de Estilista & Caída Textil:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _muted)),
          const SizedBox(height: 4),
          Text(advice, style: const TextStyle(fontSize: 13, color: _ink, fontStyle: FontStyle.italic)),
          const SizedBox(height: 20),

          // Botones de acción directa
          const Text('¿Cómo deseas obtener esta prenda?', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: _ink)),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _showReserveDialog(size),
                  icon: const Icon(Icons.storefront, size: 18, color: _brand),
                  label: const Text(
                    'Reservar Cita\n(50% Seña)',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand),
                  ),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    side: const BorderSide(color: _brand, width: 1.5),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _showDeliveryDialog(size),
                  icon: const Icon(Icons.shopping_bag, size: 18, color: Colors.white),
                  label: const Text(
                    'Añadir al\nCarrito',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _brand,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showReserveDialog(String recommendedSize) {
    final productId = _selectedProductId;
    if (productId == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Selecciona una prenda primero.')));
      return;
    }
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => ProductDetailView(productId: productId, initialSizeName: recommendedSize)),
    );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Talla $recommendedSize seleccionada. Elige una sucursal con stock para agendar tu cita.')),
    );
  }

  Future<int?> _variantForSize(String sizeName) async {
    try {
      final res = await http.get(Uri.parse('${AuthService.apiBaseUrl}/catalog/products/$_selectedProductId'));
      if (res.statusCode != 200) return null;
      final data = jsonDecode(utf8.decode(res.bodyBytes));
      final wanted = sizeName.trim().toUpperCase();
      for (final v in (data['variants'] as List? ?? [])) {
        if (v['is_active'] == true && (v['size']?['name'] ?? '').toString().toUpperCase() == wanted) {
          return v['id'] as int;
        }
      }
    } catch (_) {}
    return null;
  }

  Future<void> _showDeliveryDialog(String recommendedSize) async {
    if (!await AuthService.isLoggedIn()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Inicia sesión para comprar esta prenda.')));
      return;
    }
    final variantId = await _variantForSize(recommendedSize);
    if (!mounted) return;
    if (variantId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${_selectedProduct?['name'] ?? 'Prenda'} no está disponible en talla $recommendedSize.')),
      );
      return;
    }
    final res = await VentasApi.addToCart(variantId, 1);
    if (!mounted) return;
    if (res['ok'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${_selectedProduct?['name'] ?? 'Prenda'} (talla $recommendedSize) se agregó al carrito.')),
      );
      Navigator.push(context, MaterialPageRoute(builder: (_) => const CartView()));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['detail']?.toString() ?? 'No se pudo agregar la prenda al carrito.')),
      );
    }
  }
}
