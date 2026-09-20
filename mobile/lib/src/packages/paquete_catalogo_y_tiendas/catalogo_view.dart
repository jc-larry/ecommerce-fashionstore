import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:speech_to_text/speech_to_text.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import '../paquete_paquete_inteligente_y_analitica/virtual_tryon_view.dart';
import 'catalog_api.dart';
import 'product_detail_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU11] Catálogo de la tienda (móvil): categorías, grilla lookbook con
/// foto/precio/oferta/★/♥. [CU14] toggle de favorito. [CU34] búsqueda por voz (NLP).
class CatalogoView extends StatefulWidget {
  /// Si se incrementa desde fuera (botón de voz del Inicio), se abre el micrófono.
  final ValueListenable<int>? voiceTrigger;
  const CatalogoView({super.key, this.voiceTrigger});

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

  // [CU34] Búsqueda por voz: transcripción en el teléfono + extracción de entidades en el backend.
  final SpeechToText _speech = SpeechToText();
  final _searchCtrl = TextEditingController();
  bool _listening = false;
  String? _voiceQuery; // frase dictada que originó el filtro por voz
  Set<int>? _voiceIds; // productos que el backend reconoció para esa frase

  @override
  void initState() {
    super.initState();
    _load();
    widget.voiceTrigger?.addListener(_onVoiceTrigger);
  }

  void _onVoiceTrigger() {
    if (!_listening) _voiceSearch();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() => _loading = true);
    try {
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
    } catch (_) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  void dispose() {
    widget.voiceTrigger?.removeListener(_onVoiceTrigger);
    _speech.stop();
    _searchCtrl.dispose();
    super.dispose();
  }

  /// [CU34] Escucha al cliente, envía la transcripción a /analytics/search/voice-nlp y filtra
  /// el catálogo con las prendas que el backend reconoció (prenda, color, precio máximo).
  Future<void> _voiceSearch() async {
    if (_listening) {
      await _speech.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    final available = await _speech.initialize(
      onStatus: (st) {
        if ((st == 'done' || st == 'notListening') && mounted) setState(() => _listening = false);
      },
      onError: (_) {
        if (mounted) setState(() => _listening = false);
      },
    );
    if (!available) {
      messenger.showSnackBar(const SnackBar(
        content: Text('El reconocimiento de voz no está disponible o falta el permiso del micrófono.'),
      ));
      return;
    }
    // Preferir un idioma español instalado en el teléfono.
    String? localeId;
    try {
      final locales = await _speech.locales();
      final es = locales.where((l) => l.localeId.toLowerCase().startsWith('es')).toList();
      if (es.isNotEmpty) localeId = es.first.localeId;
    } catch (_) {}

    if (!mounted) return;
    setState(() => _listening = true);
    await _speech.listen(
      listenOptions: SpeechListenOptions(
        localeId: localeId,
        listenFor: const Duration(seconds: 12),
        pauseFor: const Duration(seconds: 3),
        listenMode: ListenMode.search,
      ),
      onResult: (r) {
        if (!mounted) return;
        setState(() => _searchCtrl.text = r.recognizedWords);
        if (r.finalResult && r.recognizedWords.trim().isNotEmpty) {
          _applyVoiceQuery(r.recognizedWords.trim());
        }
      },
    );
  }

  Future<void> _applyVoiceQuery(String text) async {
    setState(() {
      _listening = false;
      _voiceQuery = text;
      _voiceIds = null;
      _search = '';
    });
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/analytics/search/voice-nlp'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'query_text': text}),
          )
          .timeout(const Duration(seconds: 12));
      if (!mounted) return;
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        final entities = (data['extracted_entities'] as Map?) ?? const {};
        final understood = entities['garment'] != null || entities['max_price'] != null;
        if (understood) {
          setState(() => _voiceIds = ((data['products'] as List?) ?? const []).map<int>((p) => p['id'] as int).toSet());
          return;
        }
      }
    } catch (_) {}
    // Sin entidades reconocidas: se usa la frase como búsqueda de texto normal.
    if (mounted) setState(() => _search = text);
  }

  void _clearVoice() {
    setState(() {
      _voiceQuery = null;
      _voiceIds = null;
      _search = '';
      _searchCtrl.clear();
    });
  }

  List<dynamic> get _filtered {
    final t = _search.trim().toLowerCase();
    return _products.where((p) {
      if (_voiceIds != null && !_voiceIds!.contains(p['id'])) return false;
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

  void _showServerConfigDialog() {
    final controller = TextEditingController(text: AuthService.apiBaseUrl);
    bool testing = false;
    String? testStatus;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.wifi, color: _brand),
              SizedBox(width: 8),
              Text('Servidor Backend', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Ingresa la IP de tu PC donde corre el backend FastAPI (puerto 8000):',
                style: TextStyle(fontSize: 13, color: Colors.black87),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: InputDecoration(
                  labelText: 'URL de la API',
                  hintText: 'http://192.168.0.11:8000/api/v1',
                  prefixIcon: const Icon(Icons.link),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
                style: const TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: testing
                        ? null
                        : () async {
                            setDialogState(() {
                              testing = true;
                              testStatus = null;
                            });
                            final ok = await AuthService.testConnection(controller.text);
                            setDialogState(() {
                              testing = false;
                              testStatus = ok ? 'Conectado exitosamente ✅' : 'No responde el backend ❌';
                            });
                          },
                    icon: testing
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.bolt, size: 16),
                    label: const Text('Probar Conexión', style: TextStyle(fontSize: 12)),
                  ),
                ],
              ),
              if (testStatus != null) ...[
                const SizedBox(height: 6),
                Text(
                  testStatus!,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: testStatus!.contains('✅') ? Colors.green : Colors.red,
                  ),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancelar'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: _brand,
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                final nav = Navigator.of(ctx);
                await AuthService.setCustomBaseUrl(controller.text);
                nav.pop();
                _load();
              },
              child: const Text('Guardar y Recargar'),
            ),
          ],
        ),
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
        title: const Text('FashionStore', style: TextStyle(color: _ink, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.wifi, color: _brand),
            tooltip: 'Configurar Servidor / IP',
            onPressed: _showServerConfigDialog,
          ),
        ],
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
                    controller: _searchCtrl,
                    onChanged: (v) => setState(() {
                      _search = v;
                      _voiceQuery = null;
                      _voiceIds = null;
                    }),
                    decoration: InputDecoration(
                      hintText: _listening ? 'Escuchando… di p. ej. "vestido rojo hasta 200"' : 'Buscar colecciones…',
                      prefixIcon: const Icon(Icons.search, color: _muted),
                      suffixIcon: IconButton(
                        tooltip: 'Buscar por voz',
                        icon: Icon(_listening ? Icons.mic : Icons.mic_none, color: _listening ? Colors.red : _brand),
                        onPressed: _voiceSearch,
                      ),
                      filled: true, fillColor: Colors.white, isDense: true,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                    ),
                  ),
                  if (_voiceQuery != null) ...[
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: InputChip(
                        avatar: const Icon(Icons.record_voice_over, size: 16, color: _brand),
                        label: Text(
                          _voiceIds != null
                              ? 'Voz: "$_voiceQuery" · ${_voiceIds!.length} resultados'
                              : 'Voz: "$_voiceQuery"',
                          overflow: TextOverflow.ellipsis,
                        ),
                        onDeleted: _clearVoice,
                      ),
                    ),
                  ],
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
                    Container(
                      margin: const EdgeInsets.symmetric(vertical: 24),
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: const Color(0xFFEFE7E3)),
                      ),
                      child: Column(
                        children: [
                          Icon(_products.isEmpty ? Icons.cloud_off : Icons.search_off, size: 48, color: _brand.withValues(alpha: 0.6)),
                          const SizedBox(height: 12),
                          Text(
                            _products.isEmpty ? 'No se pudo conectar al catálogo' : 'No se encontraron prendas',
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _products.isEmpty
                                ? 'Verifica que tu celular esté en el mismo Wi-Fi que tu PC y que la IP del servidor sea la correcta.\n\nServidor actual: ${AuthService.apiBaseUrl}'
                                : 'Prueba cambiando los filtros o el texto de búsqueda.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 12, color: _muted),
                          ),
                          const SizedBox(height: 16),
                          if (_products.isEmpty)
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                ElevatedButton.icon(
                                  style: ElevatedButton.styleFrom(backgroundColor: _brand, foregroundColor: Colors.white),
                                  onPressed: _showServerConfigDialog,
                                  icon: const Icon(Icons.wifi, size: 16),
                                  label: const Text('Configurar IP / Servidor', style: TextStyle(fontSize: 12)),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton.icon(
                                  onPressed: _load,
                                  icon: const Icon(Icons.refresh, size: 16),
                                  label: const Text('Reintentar', style: TextStyle(fontSize: 12)),
                                ),
                              ],
                            ),
                        ],
                      ),
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
              Positioned(bottom: 6, right: 6, child: GestureDetector(
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => VirtualTryonView(
                      initialProductId: p['id'] as int,
                      initialProductName: p['name'] as String,
                      initialProduct: p,
                    ),
                  ),
                ),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.78),
                    borderRadius: BorderRadius.circular(8),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.15), blurRadius: 4),
                    ],
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.auto_awesome, size: 11, color: Color(0xFFF6C28B)),
                      SizedBox(width: 3),
                      Text('Probar', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                    ],
                  ),
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
