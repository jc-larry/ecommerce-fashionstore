import 'package:flutter/material.dart';
import 'ventas_api.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU24] Pantalla de Historial y Detalle de Compras del Cliente.
class CustomerOrdersView extends StatefulWidget {
  const CustomerOrdersView({super.key});

  @override
  State<CustomerOrdersView> createState() => _CustomerOrdersViewState();
}

class _CustomerOrdersViewState extends State<CustomerOrdersView> {
  bool _loading = true;
  List<dynamic> _orders = [];

  @override
  void initState() {
    super.initState();
    _loadOrders();
  }

  Future<void> _loadOrders() async {
    setState(() {
      _loading = true;
    });

    final data = await VentasApi.fetchMyOrders();
    if (mounted) {
      setState(() {
        _orders = data;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('Mis Pedidos', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: _ink,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : _orders.isEmpty
              ? _emptyState()
              : RefreshIndicator(
                  color: _brand,
                  onRefresh: _loadOrders,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _orders.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 14),
                    itemBuilder: (ctx, i) => _orderCard(_orders[i]),
                  ),
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
              decoration: BoxDecoration(color: _brand.withValues(alpha: 0.08), shape: BoxShape.circle),
              child: const Icon(Icons.receipt_long_outlined, size: 64, color: _brand),
            ),
            const SizedBox(height: 20),
            const Text('Aún no tienes pedidos', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 8),
            const Text(
              'Tus compras digitales y en tienda se registrarán aquí con tus comprobantes fiscales.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }

  Widget _orderCard(dynamic ord) {
    final numOrder = ord['order_number'] as String? ?? 'ORD-${ord['id']}';
    final status = ord['status'] as String? ?? 'PAGADA';
    final total = (ord['total_amount'] as num).toDouble();
    final items = ord['items'] as List? ?? [];
    final inv = ord['invoice'] as Map<String, dynamic>?;
    final payments = ord['payments'] as List? ?? [];
    final payType = payments.isNotEmpty ? payments[0]['payment_type'] : 'ONLINE';
    final dateStr = (ord['created_at'] as String?)?.substring(0, 10) ?? '';

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5DFDC)),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 10, offset: const Offset(0, 3)),
        ],
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        shape: const RoundedRectangleBorder(side: BorderSide.none),
        collapsedShape: const RoundedRectangleBorder(side: BorderSide.none),
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(numOrder, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: _ink)),
            _statusBadge(status),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('$dateStr · $payType', style: const TextStyle(color: _muted, fontSize: 12)),
              Text('Bs. ${total.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _brand)),
            ],
          ),
        ),
        children: [
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Prendas adquiridas:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink)),
                const SizedBox(height: 8),
                ...items.map((it) {
                  final itSubtotal = (it['subtotal'] as num).toDouble();
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            '${it['quantity']}x ${it['product_name']} (${it['size']}/${it['color']})',
                            style: const TextStyle(fontSize: 13, color: _ink),
                          ),
                        ),
                        Text('Bs. ${itSubtotal.toStringAsFixed(2)}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 12),
                if (inv != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: const Color(0xFFF9F7F6), borderRadius: BorderRadius.circular(10)),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text('Comprobante: ${inv['doc_type']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: _ink)),
                            Text('NIT: ${inv['customer_nit'] ?? "0"}', style: const TextStyle(fontSize: 11, color: _muted)),
                          ],
                        ),
                        if (inv['control_code'] != null) ...[
                          const SizedBox(height: 4),
                          Text('Código Control: ${inv['control_code']}', style: const TextStyle(fontFamily: 'monospace', fontSize: 11, color: _muted)),
                        ],
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusBadge(String st) {
    Color bg = Colors.green.shade50;
    Color fg = Colors.green.shade700;
    if (st == 'CANCELADA') {
      bg = Colors.red.shade50;
      fg = Colors.red.shade700;
    } else if (st == 'PENDIENTE') {
      bg = Colors.amber.shade50;
      fg = Colors.amber.shade800;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(st, style: TextStyle(color: fg, fontWeight: FontWeight.bold, fontSize: 11)),
    );
  }
}
