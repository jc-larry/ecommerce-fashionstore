import 'package:flutter/material.dart';
import 'ventas_api.dart';
import '../catalogo_y_tiendas/catalog_api.dart';
import 'customer_orders_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU17 / CU18 / CU20] Pantalla completa de Carrito Digital y Checkout Omnicanal Móvil.
class CartView extends StatefulWidget {
  const CartView({super.key});

  @override
  State<CartView> createState() => _CartViewState();
}

class _CartViewState extends State<CartView> {
  bool _loading = true;
  Map<String, dynamic>? _cart;

  @override
  void initState() {
    super.initState();
    _loadCart();
  }

  Future<void> _loadCart() async {
    setState(() {
      _loading = true;
    });
    final c = await VentasApi.fetchCart();
    if (mounted) {
      setState(() {
        _cart = c;
        _loading = false;
      });
    }
  }

  Future<void> _updateQty(int itemId, int currentQty, int delta, int maxStock) async {
    final nextQty = currentQty + delta;
    if (nextQty > maxStock) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Stock máximo alcanzado ($maxStock unidades).')),
      );
      return;
    }
    if (nextQty <= 0) {
      await _removeItem(itemId);
      return;
    }

    final res = await VentasApi.updateCartItem(itemId, nextQty);
    if (!res['ok']) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['detail'] ?? 'Error al actualizar.')),
        );
      }
    } else {
      if (mounted) {
        setState(() => _cart = res['data']);
      }
    }
  }

  Future<void> _removeItem(int itemId) async {
    final ok = await VentasApi.removeCartItem(itemId);
    if (ok && mounted) {
      _loadCart();
    }
  }

  Future<void> _clearCart() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Vaciar carrito'),
        content: const Text('¿Deseas quitar todas las prendas de tu carrito?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Vaciar', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (ok == true) {
      await VentasApi.clearCart();
      if (mounted) _loadCart();
    }
  }

  void _startCheckout() {
    if (_cart == null || (_cart!['items'] as List).isEmpty) return;
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CheckoutSheet(
          cart: _cart!,
          onOrderCompleted: () {
            _loadCart();
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = _cart != null ? (_cart!['items'] as List) : [];
    final subtotal = _cart != null ? (_cart!['subtotal'] as num).toDouble() : 0.0;
    final count = _cart != null ? (_cart!['items_count'] as int? ?? 0) : 0;

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('Mi Carrito', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        elevation: 0,
        actions: [
          if (items.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_sweep_outlined, color: Colors.redAccent),
              tooltip: 'Vaciar carrito',
              onPressed: _clearCart,
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : items.isEmpty
              ? _emptyState()
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('$count ${count == 1 ? "prenda" : "prendas"} en total',
                              style: const TextStyle(color: _muted, fontSize: 13, fontWeight: FontWeight.w500)),
                          const Text('Envío a todo el país', style: TextStyle(color: Colors.green, fontSize: 12, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 12),
                        itemBuilder: (ctx, i) => _cartItemTile(items[i]),
                      ),
                    ),
                    _checkoutSummaryBar(subtotal),
                  ],
                ),
    );
  }

  Widget _emptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: _brand.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.shopping_bag_outlined, size: 64, color: _brand),
            ),
            const SizedBox(height: 20),
            const Text(
              'Tu carrito está vacío',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink),
            ),
            const SizedBox(height: 8),
            const Text(
              'Explora las últimas colecciones y añade las prendas que te encanten.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }

  Widget _cartItemTile(dynamic it) {
    final itemId = it['id'] as int;
    final name = it['product_name'] as String;
    final size = it['size'] as String;
    final color = it['color'] as String;
    final sku = it['sku'] as String;
    final price = (it['unit_price'] as num).toDouble();
    final itemSubtotal = (it['subtotal'] as num).toDouble();
    final qty = it['quantity'] as int;
    final maxStock = it['stock_available'] as int;
    final img = it['image_url'] as String?;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Imagen miniatura
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              width: 70,
              height: 70,
              child: img != null && img.isNotEmpty
                  ? Image.network(
                      CatalogApi.resolveImage(img),
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(
                        color: const Color(0xFFEFE7E3),
                        child: const Icon(Icons.broken_image_outlined, color: _muted),
                      ),
                    )
                  : Container(
                      color: const Color(0xFFEFE7E3),
                      child: const Icon(Icons.image_outlined, color: _muted),
                    ),
            ),
          ),
          const SizedBox(width: 12),
          // Info de prenda
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _ink),
                ),
                const SizedBox(height: 2),
                Text(
                  '$size · $color · $sku',
                  style: const TextStyle(color: _muted, fontSize: 11),
                ),
                const SizedBox(height: 6),
                Text(
                  'Bs. ${price.toStringAsFixed(2)}',
                  style: const TextStyle(color: _brand, fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
          ),
          // Controles de cantidad
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _circleBtn(Icons.remove, () => _updateQty(itemId, qty, -1, maxStock)),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Text('$qty', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  ),
                  _circleBtn(Icons.add, () => _updateQty(itemId, qty, 1, maxStock)),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'Bs. ${itemSubtotal.toStringAsFixed(2)}',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _circleBtn(IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 28,
        height: 28,
        decoration: const BoxDecoration(
          color: Color(0xFFF6E3DD),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: 16, color: _brand),
      ),
    );
  }

  Widget _checkoutSummaryBar(double subtotal) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 16,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Total a Pagar', style: TextStyle(fontSize: 15, color: _muted, fontWeight: FontWeight.w600)),
                Text(
                  'Bs. ${subtotal.toStringAsFixed(2)}',
                  style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _brand),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: _startCheckout,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Continuar al Checkout', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// [CU18 / CU20] Pantalla de Checkout Polimórfico y Emisión de Factura Fiscal en Móvil.
class CheckoutSheet extends StatefulWidget {
  final Map<String, dynamic> cart;
  final VoidCallback onOrderCompleted;

  const CheckoutSheet({
    super.key,
    required this.cart,
    required this.onOrderCompleted,
  });

  @override
  State<CheckoutSheet> createState() => _CheckoutSheetState();
}

class _CheckoutSheetState extends State<CheckoutSheet> {
  bool _loading = false;
  List<dynamic> _branches = [];
  int? _selectedBranchId;

  // Cupón (CU13)
  final _couponCtrl = TextEditingController();
  double _discountAmount = 0.0;

  Future<void> _applyCoupon() async {
    final code = _couponCtrl.text.trim().toUpperCase();
    if (code.isEmpty) return;
    final res = await CatalogApi.validateCoupon(code, _subtotal);
    if (!mounted) return;
    if (res['is_valid'] == true) {
      setState(() {
        _discountAmount = (res['discount_amount'] as num).toDouble();
        _error = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('¡Cupón $code aplicado: -Bs. ${_discountAmount.toStringAsFixed(2)}!')),
      );
    } else {
      setState(() {
        _discountAmount = 0.0;
        _error = res['message'] ?? 'Cupón inválido o expirado.';
      });
    }
  }

  // Medio de pago (STI)
  String _paymentType = 'TARJETA'; // TARJETA, QR, EFECTIVO
  String _cardBrand = 'VISA';
  final _cardLast4Ctrl = TextEditingController(text: '4242');

  // Facturación fiscal IVA 13%
  String _docType = 'FACTURA'; // FACTURA, NOTA_ENTREGA
  final _nitCtrl = TextEditingController(text: '0');
  final _nameCtrl = TextEditingController();

  String? _error;
  Map<String, dynamic>? _successOrder;

  @override
  void initState() {
    super.initState();
    _loadBranches();
  }

  Future<void> _loadBranches() async {
    final b = await VentasApi.fetchBranches();
    if (mounted) {
      setState(() {
        _branches = b;
        if (b.isNotEmpty) {
          _selectedBranchId = b[0]['id'] as int;
        }
      });
    }
  }

  double get _subtotal => (widget.cart['subtotal'] as num).toDouble();
  double get _total => (_subtotal - _discountAmount).clamp(0.0, double.infinity);
  double get _iva13 => _total * 0.13;

  Future<void> _processCheckout() async {
    if (_selectedBranchId == null) {
      setState(() => _error = 'Selecciona una sucursal de retiro o despacho.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    final payload = <String, dynamic>{
      'channel': 'ONLINE',
      'branch_id': _selectedBranchId,
      'payment_type': _paymentType,
      'doc_type': _docType,
      'customer_nit': _nitCtrl.text.trim().isEmpty ? '0' : _nitCtrl.text.trim(),
      'customer_name': _nameCtrl.text.trim(),
      if (_couponCtrl.text.trim().isNotEmpty) 'coupon_code': _couponCtrl.text.trim().toUpperCase(),
    };

    if (_paymentType == 'TARJETA') {
      payload['card_payment'] = {
        'card_brand': _cardBrand,
        'card_last4': _cardLast4Ctrl.text.length >= 4 ? _cardLast4Ctrl.text.substring(_cardLast4Ctrl.text.length - 4) : '4242',
      };
    } else if (_paymentType == 'QR') {
      payload['qr_payment'] = {
        'qr_reference': 'QR-MOB-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}',
      };
    } else if (_paymentType == 'EFECTIVO') {
      payload['cash_payment'] = {
        'cash_received': _total,
      };
    }

    final res = await VentasApi.checkout(payload);
    if (!mounted) return;

    if (res['ok']) {
      setState(() {
        _loading = false;
        _successOrder = res['data'];
      });
      widget.onOrderCompleted();
    } else {
      setState(() {
        _loading = false;
        _error = res['detail'] ?? 'Error al procesar el pago.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_successOrder != null) {
      return _buildSuccessView();
    }

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('Checkout & Pago', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: _ink,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_error != null)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.red.shade200)),
                child: Text(_error!, style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
              ),

            // 1. Sucursal de despacho
            _sectionHeader('1. Sucursal de Despacho', Icons.store_outlined),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFE5DFDC))),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<int>(
                  isExpanded: true,
                  value: _selectedBranchId,
                  items: _branches.map((b) {
                    return DropdownMenuItem<int>(
                      value: b['id'] as int,
                      child: Text('${b['name']} (${b['city'] ?? "Santa Cruz"})'),
                    );
                  }).toList(),
                  onChanged: (v) => setState(() => _selectedBranchId = v),
                ),
              ),
            ),
            const SizedBox(height: 20),

            // 2. Método de Pago Polimórfico (CU18)
            _sectionHeader('2. Medio de Pago', Icons.payment_outlined),
            Row(
              children: [
                _paymentTile('TARJETA', 'Tarjeta', Icons.credit_card),
                const SizedBox(width: 8),
                _paymentTile('QR', 'QR Simple', Icons.qr_code),
                const SizedBox(width: 8),
                _paymentTile('EFECTIVO', 'Efectivo', Icons.money),
              ],
            ),
            const SizedBox(height: 12),
            _paymentFields(),
            const SizedBox(height: 20),

            // 3. Comprobante Fiscal (CU20)
            _sectionHeader('3. Comprobante Fiscal', Icons.receipt_long_outlined),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE5DFDC))),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: ChoiceChip(
                          label: const Text('Factura (IVA 13%)'),
                          selected: _docType == 'FACTURA',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (s) => setState(() => _docType = 'FACTURA'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: ChoiceChip(
                          label: const Text('Nota de Entrega'),
                          selected: _docType == 'NOTA_ENTREGA',
                          selectedColor: const Color(0xFFF6E3DD),
                          onSelected: (s) => setState(() => _docType = 'NOTA_ENTREGA'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _nitCtrl,
                    decoration: const InputDecoration(
                      labelText: 'NIT o C.I.',
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Razón Social / Nombre',
                      isDense: true,
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // 4. Cupón de Descuento (CU13)
            _sectionHeader('4. Cupón de Descuento', Icons.percent_outlined),
            TextField(
              controller: _couponCtrl,
              textCapitalization: TextCapitalization.characters,
              onSubmitted: (_) => _applyCoupon(),
              decoration: InputDecoration(
                hintText: 'Ej: BIENVENIDA10',
                filled: true,
                fillColor: Colors.white,
                suffixIcon: IconButton(
                  icon: const Icon(Icons.check_circle, color: _brand),
                  onPressed: _applyCoupon,
                  tooltip: 'Aplicar cupón',
                ),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFE5DFDC))),
              ),
            ),
            const SizedBox(height: 24),

            // 5. Resumen Financiero
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE5DFDC))),
              child: Column(
                children: [
                  _summaryRow('Subtotal de prendas', 'Bs. ${_subtotal.toStringAsFixed(2)}'),
                  if (_discountAmount > 0) _summaryRow('Descuento cupón', '- Bs. ${_discountAmount.toStringAsFixed(2)}', color: Colors.green),
                  if (_docType == 'FACTURA') _summaryRow('IVA Débito Fiscal (13%)', 'Bs. ${_iva13.toStringAsFixed(2)}', isMuted: true),
                  const Divider(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('TOTAL GENERAL', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink)),
                      Text('Bs. ${_total.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 20, color: _brand)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Botón Confirmar Compra
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _loading ? null : _processCheckout,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _brand,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                icon: _loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Icon(Icons.check_circle_outline),
                label: Text(
                  _loading ? 'Procesando...' : 'Confirmar y Pagar (Bs. ${_total.toStringAsFixed(2)})',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: _brand),
          const SizedBox(width: 8),
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _ink)),
        ],
      ),
    );
  }

  Widget _paymentTile(String type, String label, IconData icon) {
    final sel = _paymentType == type;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _paymentType = type),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: sel ? const Color(0xFFF6E3DD) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: sel ? _brand : const Color(0xFFE5DFDC), width: sel ? 2 : 1),
          ),
          child: Column(
            children: [
              Icon(icon, color: sel ? _brand : _muted),
              const SizedBox(height: 4),
              Text(label, style: TextStyle(fontWeight: sel ? FontWeight.bold : FontWeight.normal, fontSize: 12, color: sel ? _brand : _ink)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _paymentFields() {
    if (_paymentType == 'TARJETA') {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFE5DFDC))),
        child: Row(
          children: [
            Expanded(
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: _cardBrand,
                  items: const [
                    DropdownMenuItem(value: 'VISA', child: Text('VISA')),
                    DropdownMenuItem(value: 'MASTERCARD', child: Text('Mastercard')),
                  ],
                  onChanged: (v) => setState(() => _cardBrand = v ?? 'VISA'),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextField(
                controller: _cardLast4Ctrl,
                maxLength: 4,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Últimos 4 dígitos',
                  counterText: '',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ),
          ],
        ),
      );
    }
    if (_paymentType == 'QR') {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.teal.shade50, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.teal.shade200)),
        child: const Row(
          children: [
            Icon(Icons.qr_code_scanner, color: Colors.teal, size: 28),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Se generará un código QR interoperable avalado por la red bancaria boliviana.',
                style: TextStyle(color: Colors.teal, fontSize: 12),
              ),
            ),
          ],
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.amber.shade50, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.amber.shade200)),
      child: const Row(
        children: [
          Icon(Icons.local_shipping_outlined, color: Colors.amber, size: 28),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Pagarás en efectivo al momento de recibir o retirar tu pedido.',
              style: TextStyle(color: Colors.brown, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(String label, String value, {Color? color, bool isMuted = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: isMuted ? _muted : _ink, fontSize: 13)),
          Text(value, style: TextStyle(fontWeight: FontWeight.w600, color: color ?? _ink, fontSize: 13)),
        ],
      ),
    );
  }

  Widget _buildSuccessView() {
    final ord = _successOrder!;
    final numOrder = ord['order_number'] as String? ?? 'ORD-${ord['id']}';
    final inv = ord['invoice'] as Map<String, dynamic>?;

    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: const BoxDecoration(color: Colors.green, shape: BoxShape.circle),
                  child: const Icon(Icons.check, size: 54, color: Colors.white),
                ),
                const SizedBox(height: 20),
                const Text('¡Compra Exitosa!', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _ink)),
                const SizedBox(height: 6),
                Text('Orden $numOrder confirmada.', style: const TextStyle(color: _muted, fontSize: 14)),
                const SizedBox(height: 20),

                // Tarjeta de recibo
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFFE5DFDC))),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Comprobante', style: TextStyle(color: _muted, fontSize: 13)),
                          Text(inv != null ? (inv['doc_type'] ?? 'FACTURA') : 'RECIBO', style: const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      if (inv != null && inv['control_code'] != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text('Código Control', style: TextStyle(color: _muted, fontSize: 13)),
                            Text(inv['control_code'], style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 12)),
                          ],
                        ),
                      ],
                      const Divider(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('TOTAL PAGADO', style: TextStyle(fontWeight: FontWeight.bold)),
                          Text('Bs. ${(ord['total_amount'] as num).toDouble().toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, color: _brand, fontSize: 16)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      Navigator.push(context, MaterialPageRoute(builder: (_) => const CustomerOrdersView()));
                    },
                    style: ElevatedButton.styleFrom(backgroundColor: _brand, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                    child: const Text('Ver Mis Compras (CU24)'),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Volver a la Tienda', style: TextStyle(color: _muted)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
