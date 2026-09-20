import 'package:flutter/material.dart';
import 'ventas_api.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU24] Historial y detalle de compras del cliente + [CU22] sus devoluciones y cambios.
class CustomerOrdersView extends StatefulWidget {
  const CustomerOrdersView({super.key});

  @override
  State<CustomerOrdersView> createState() => _CustomerOrdersViewState();
}

class _CustomerOrdersViewState extends State<CustomerOrdersView> {
  bool _loading = true;
  List<dynamic> _orders = [];
  List<dynamic> _returns = [];

  @override
  void initState() {
    super.initState();
    _loadOrders();
  }

  Future<void> _loadOrders() async {
    setState(() {
      _loading = true;
    });

    final results = await Future.wait([VentasApi.fetchMyOrders(), VentasApi.fetchMyReturns()]);
    if (mounted) {
      setState(() {
        _orders = results[0];
        _returns = results[1];
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: const Color(0xFFFCFBFA),
        appBar: AppBar(
          title: const Text('Mis compras', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
          backgroundColor: Colors.white,
          elevation: 0,
          foregroundColor: _ink,
          bottom: TabBar(
            labelColor: _brand,
            indicatorColor: _brand,
            unselectedLabelColor: _muted,
            tabs: [
              Tab(text: 'Pedidos (${_orders.length})'),
              Tab(text: 'Devoluciones (${_returns.length})'),
            ],
          ),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator(color: _brand))
            : TabBarView(children: [
                _orders.isEmpty
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
                _returnsList(),
              ]),
      ),
    );
  }

  /// [CU22] Devoluciones de dinero y cambios de prenda procesados en sucursal.
  Widget _returnsList() {
    if (_returns.isEmpty) {
      return RefreshIndicator(
        color: _brand,
        onRefresh: _loadOrders,
        child: ListView(children: const [
          SizedBox(height: 120),
          Icon(Icons.assignment_return_outlined, size: 56, color: _brand),
          SizedBox(height: 12),
          Center(child: Text('No tienes devoluciones ni cambios', style: TextStyle(fontWeight: FontWeight.bold, color: _ink))),
          SizedBox(height: 6),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              'Si necesitas cambiar o devolver una prenda, acércate a la sucursal con tu número de pedido.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 13),
            ),
          ),
        ]),
      );
    }
    return RefreshIndicator(
      color: _brand,
      onRefresh: _loadOrders,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _returns.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (ctx, i) {
          final r = _returns[i] as Map<String, dynamic>;
          final isRefund = r['return_type'] == 'DEVOLUCION_DINERO';
          final items = (r['items'] as List?) ?? const [];
          final date = (r['created_at'] ?? '').toString().split('T').first;
          final refund = (r['refund_amount'] as num?)?.toDouble() ?? 0;
          return Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFFECE6E2)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('${r['return_number']}', style: const TextStyle(fontWeight: FontWeight.bold, color: _ink)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                  decoration: BoxDecoration(color: Colors.green.shade50, borderRadius: BorderRadius.circular(12)),
                  child: Text('${r['status']}',
                      style: TextStyle(color: Colors.green.shade700, fontWeight: FontWeight.bold, fontSize: 11)),
                ),
              ]),
              const SizedBox(height: 4),
              Text('Pedido ${r['order_number']} · $date', style: const TextStyle(fontSize: 12, color: _muted)),
              const SizedBox(height: 6),
              Text(isRefund ? 'Devolución de dinero' : 'Cambio de prenda',
                  style: const TextStyle(fontWeight: FontWeight.w600, color: _brand)),
              Text('Motivo: ${r['reason']}', style: const TextStyle(fontSize: 12, color: _ink)),
              const Divider(height: 18),
              ...items.map((it) {
                final replacement = it['replacement_product_name'] != null
                    ? '  →  ${it['replacement_product_name']} (${it['replacement_size']}/${it['replacement_color']})'
                    : '';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(
                    '${it['quantity']}x ${it['product_name']} (${it['size']}/${it['color']})$replacement',
                    style: const TextStyle(fontSize: 12, color: _ink),
                  ),
                );
              }),
              if (isRefund) ...[
                const SizedBox(height: 8),
                Text('Reembolso: Bs. ${refund.toStringAsFixed(2)}',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: _ink)),
              ],
            ]),
          );
        },
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
    if (st == 'CANCELADA' || st == 'CANCELADO') {
      bg = Colors.red.shade50;
      fg = Colors.red.shade700;
    } else if (st == 'PENDIENTE' || st == 'PREPARANDO') {
      bg = Colors.amber.shade50;
      fg = Colors.amber.shade800;
    } else if (st == 'LISTO_PARA_ENTREGA') {
      bg = Colors.blue.shade50;
      fg = Colors.blue.shade700;
    }
    // Estados de alistado del pedido online en la sucursal (bandeja del cajero).
    const labels = {
      'PAGADA': 'Pagada',
      'PREPARANDO': 'En preparación',
      'LISTO_PARA_ENTREGA': 'Listo para entrega',
      'ENTREGADO': 'Entregado',
      'CANCELADO': 'Cancelado',
      'CANCELADA': 'Cancelada',
      'PENDIENTE': 'Pendiente',
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(labels[st] ?? st.replaceAll('_', ' '), style: TextStyle(color: fg, fontWeight: FontWeight.bold, fontSize: 11)),
    );
  }
}
