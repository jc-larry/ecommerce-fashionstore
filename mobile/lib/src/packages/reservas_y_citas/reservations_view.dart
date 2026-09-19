import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../seguridad_y_usuarios/auth_service.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU26 / CU28] Vista de Reservas en Tienda Física (App Móvil).
/// Permite al cliente consultar sus reservas con bloqueo de stock 48h,
/// verificar su código de retiro (QR/Alfanumérico) y cancelar si no puede asistir.
class ReservationsView extends StatefulWidget {
  const ReservationsView({super.key});

  @override
  State<ReservationsView> createState() => _ReservationsViewState();
}

class _ReservationsViewState extends State<ReservationsView> {
  bool _loading = true;
  String? _error;
  List<dynamic> _reservations = [];

  @override
  void initState() {
    super.initState();
    _loadReservations();
  }

  Future<void> _loadReservations() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await AuthService.getToken();
      if (token == null) {
        setState(() {
          _loading = false;
          _error = 'Debes iniciar sesión para consultar tus reservas.';
        });
        return;
      }

      final url = Uri.parse('${AuthService.apiBaseUrl}/reservations/my');
      final res = await http.get(url, headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      }).timeout(const Duration(seconds: 12));

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _reservations = data is List ? data : [];
          _loading = false;
        });
      } else {
        setState(() {
          _loading = false;
          _error = 'No se pudieron obtener las reservas (código ${res.statusCode}).';
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'No se pudo conectar con el servidor. Intenta nuevamente.';
      });
    }
  }

  Future<void> _cancelReservation(int id, String code) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('¿Cancelar reserva?'),
        content: Text('Se liberará el stock bloqueado de la reserva $code para que otros clientes puedan adquirirlo.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No, mantener')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sí, cancelar', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/reservations/$id/cancel');
      final res = await http.post(url, headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      });

      if (res.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Reserva $code cancelada. Las prendas volvieron al stock de la sucursal.'),
            backgroundColor: Colors.black87,
          ),
        );
        _loadReservations();
      } else {
        final err = jsonDecode(utf8.decode(res.bodyBytes));
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(err['detail'] ?? 'No se pudo cancelar la reserva.'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo conectar con el servidor.'), backgroundColor: Colors.red),
      );
    }
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING':
      case 'LATE':
        return Colors.orange.shade700;
      case 'PREPARING':
        return Colors.blue.shade700;
      case 'READY':
      case 'COMPLETED':
        return Colors.green.shade700;
      case 'CANCELLED':
      case 'EXPIRED':
      case 'NO_SHOW':
        return Colors.red.shade700;
      default:
        return Colors.grey.shade600;
    }
  }

  Color _statusBg(String status) => _statusColor(status).withValues(alpha: 0.08);

  /// Mismos textos que "Mis reservas" en la web.
  String _statusLabel(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING':
        return 'Pendiente de preparación';
      case 'PREPARING':
        return 'Prendas en perchero';
      case 'READY':
        return 'Listo en vestidor';
      case 'LATE':
        return 'Con retraso';
      case 'COMPLETED':
        return 'Venta concretada';
      case 'CANCELLED':
        return 'Cancelada';
      case 'EXPIRED':
        return 'Expirada';
      case 'NO_SHOW':
        return 'No asistió';
      default:
        return status;
    }
  }

  double _num(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        title: const Text('Mis Reservas en Tienda', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadReservations,
            tooltip: 'Actualizar',
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: _brand));
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.info_outline, size: 48, color: Colors.orange),
              const SizedBox(height: 12),
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: _muted)),
              const SizedBox(height: 16),
              ElevatedButton(onPressed: _loadReservations, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    if (_reservations.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xFFF6E3DD)),
                child: const Icon(Icons.calendar_today_outlined, size: 48, color: _brand),
              ),
              const SizedBox(height: 18),
              const Text('No tienes reservas activas', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink)),
              const SizedBox(height: 8),
              const Text(
                'Aparta tus prendas favoritas por 48 horas desde el catálogo para probártelas en tu sucursal más cercana.',
                textAlign: TextAlign.center,
                style: TextStyle(color: _muted, fontSize: 13),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadReservations,
      color: _brand,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _reservations.length,
        separatorBuilder: (_, __) => const SizedBox(height: 14),
        itemBuilder: (context, index) {
          final res = _reservations[index];
          final items = (res['items'] as List?) ?? [];
          final status = (res['status'] ?? 'PENDING').toString();
          // El backend permite cancelar mientras la reserva no esté concretada, cancelada o vencida.
          final canCancel = const ['PENDING', 'PREPARING', 'READY', 'LATE'].contains(status);
          final code = res['reservation_code'] ?? 'RES-${res['id']}';
          final branch = res['branch_name'] ?? 'Sucursal Principal';

          return Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFECE6E2)),
              boxShadow: [
                BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 10, offset: const Offset(0, 4)),
              ],
            ),
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.qr_code, color: _brand, size: 20),
                        const SizedBox(width: 6),
                        Text(code, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: _ink)),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: _statusBg(status),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: _statusColor(status).withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        _statusLabel(status),
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: _statusColor(status)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.storefront, size: 15, color: _muted),
                    const SizedBox(width: 4),
                    Text(branch, style: const TextStyle(fontSize: 13, color: _ink, fontWeight: FontWeight.w500)),
                  ],
                ),
                if (res['appointment_date'] != null) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.event_available_outlined, size: 15, color: _muted),
                      const SizedBox(width: 4),
                      Text(
                        'Cita: ${res['appointment_date']}${res['appointment_time'] != null ? ' a las ${res['appointment_time']}' : ''}',
                        style: const TextStyle(fontSize: 12, color: _ink),
                      ),
                    ],
                  ),
                ],
                if (res['expires_at'] != null && canCancel) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.timer_outlined, size: 15, color: Colors.orange),
                      const SizedBox(width: 4),
                      Text(
                        'Vence: ${res['expires_at'].toString().split('T').first}',
                        style: const TextStyle(fontSize: 12, color: Colors.deepOrange, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ],
                const Divider(height: 20),
                const Text('Prendas reservadas:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _muted)),
                const SizedBox(height: 6),
                ...items.map((it) => Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              '• ${it['product_name'] ?? 'Prenda'} (Talla: ${it['size_name'] ?? '-'}, Color: ${it['color_name'] ?? '-'}) x${it['quantity']}',
                              style: const TextStyle(fontSize: 12, color: _ink),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text('Bs. ${_num(it['unit_price']).toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    )),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Seña pagada (${res['payment_method'] ?? 'TARJETA'}): Bs. ${_num(res['deposit_amount']).toStringAsFixed(2)}',
                            style: const TextStyle(fontSize: 11, color: _muted),
                          ),
                          const Text('Saldo a pagar en tienda:', style: TextStyle(fontSize: 11, color: _muted)),
                          Text('Bs. ${_num(res['balance_due']).toStringAsFixed(2)}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: _brand)),
                        ],
                      ),
                    ),
                    if (canCancel)
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.red,
                          side: const BorderSide(color: Colors.red),
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          textStyle: const TextStyle(fontSize: 12),
                        ),
                        onPressed: () => _cancelReservation(res['id'], code),
                        icon: const Icon(Icons.close, size: 14),
                        label: const Text('Cancelar'),
                      ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
