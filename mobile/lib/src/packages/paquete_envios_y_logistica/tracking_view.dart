import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU30] Vista de Rastreo de Envíos en Tiempo Real (App Móvil).
/// Permite al cliente consultar el estado de su despacho a domicilio,
/// visualizando la línea de tiempo completa de hitos logísticos.
class TrackingView extends StatefulWidget {
  final String? initialTrackingCode;
  const TrackingView({super.key, this.initialTrackingCode});

  @override
  State<TrackingView> createState() => _TrackingViewState();
}

class _TrackingViewState extends State<TrackingView> {
  final TextEditingController _codeCtrl = TextEditingController();
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _trackingData;

  @override
  void initState() {
    super.initState();
    if (widget.initialTrackingCode != null && widget.initialTrackingCode!.isNotEmpty) {
      _codeCtrl.text = widget.initialTrackingCode!;
      _searchTracking(widget.initialTrackingCode!);
    }
  }

  Future<void> _searchTracking(String code) async {
    final query = code.trim().toUpperCase();
    if (query.isEmpty) return;

    setState(() {
      _loading = true;
      _error = null;
      _trackingData = null;
    });

    try {
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/track/${Uri.encodeComponent(query)}');
      final res = await http.get(url).timeout(const Duration(seconds: 12));

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _trackingData = data is Map<String, dynamic> ? data : null;
          _loading = false;
        });
      } else {
        String msg = 'No se encontró ningún envío con el código "$query". Revisa el número e intenta nuevamente.';
        try {
          final detail = jsonDecode(utf8.decode(res.bodyBytes))['detail'];
          if (detail is String && detail.isNotEmpty) msg = detail;
        } catch (_) {}
        setState(() {
          _loading = false;
          _error = msg;
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'No se pudo conectar con el servidor. Revisa tu conexión e intenta nuevamente.';
      });
    }
  }

  Color _statusColor(String status) {
    switch (status.toUpperCase()) {
      case 'DELIVERED':
        return Colors.green.shade700;
      case 'IN_TRANSIT':
      case 'OUT_FOR_DELIVERY':
        return Colors.blue.shade700;
      case 'PENDING_DISPATCH':
      case 'DISPATCHED':
      case 'ASSIGNED':
      case 'PICKED_UP':
      case 'RESCHEDULED':
        return Colors.orange.shade700;
      case 'FAILED_ATTEMPT':
      case 'RETURNED_TO_STORE':
        return Colors.red.shade700;
      default:
        return _brand;
    }
  }

  /// Mismos textos que la vista web de rastreo (CU30).
  String _statusText(String status) {
    switch (status.toUpperCase()) {
      case 'PENDING_DISPATCH':
        return 'En preparación en almacén';
      case 'DISPATCHED':
        return 'Despachado con el transportista';
      case 'ASSIGNED':
        return 'Repartidor asignado';
      case 'PICKED_UP':
        return 'Recogido en la sucursal';
      case 'IN_TRANSIT':
        return 'En tránsito';
      case 'OUT_FOR_DELIVERY':
        return '¡En reparto hoy hacia tu domicilio!';
      case 'DELIVERED':
        return 'Entregado con éxito';
      case 'FAILED_ATTEMPT':
        return 'Intento de entrega fallido';
      case 'RESCHEDULED':
        return 'Entrega reprogramada';
      case 'RETURNED_TO_STORE':
        return 'Devuelto a la sucursal';
      default:
        return status.replaceAll('_', ' ');
    }
  }

  String _fmtDateTime(dynamic raw) {
    final d = DateTime.tryParse((raw ?? '').toString())?.toLocal();
    if (d == null) return '';
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(d.day)}/${two(d.month)}/${d.year} ${two(d.hour)}:${two(d.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        title: const Text('Rastreo de Envíos en Vivo', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Buscador de código
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFECE6E2)),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 8, offset: const Offset(0, 3)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Ingresa tu número de guía o código de rastreo:', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: _ink)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _codeCtrl,
                          textCapitalization: TextCapitalization.characters,
                          decoration: InputDecoration(
                            hintText: 'Ej. TRK-2026-A1B2C3',
                            prefixIcon: const Icon(Icons.qr_code_scanner, color: _brand),
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                          ),
                          onSubmitted: _searchTracking,
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () => _searchTracking(_codeCtrl.text),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        child: const Icon(Icons.search),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            if (_loading)
              const Center(child: Padding(padding: EdgeInsets.all(32), child: CircularProgressIndicator(color: _brand))),

            if (_error != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.orange.shade200)),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange),
                    const SizedBox(width: 12),
                    Expanded(child: Text(_error!, style: const TextStyle(fontSize: 13, color: Colors.black87))),
                  ],
                ),
              ),

            if (_trackingData != null) _buildTrackingResult(),
          ],
        ),
      ),
    );
  }

  Widget _buildTrackingResult() {
    final d = _trackingData!;
    final status = (d['status'] ?? 'PENDING_DISPATCH').toString();
    final events = (d['events'] as List?) ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Tarjeta resumen del envío
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFECE6E2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    d['tracking_number'] ?? 'TRK-SN',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17, color: _brand),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: _statusColor(status).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _statusText(status),
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _statusColor(status)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  const Icon(Icons.local_shipping_outlined, size: 16, color: _muted),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Repartidor: ${d['delivery_person_name'] ?? d['carrier_name'] ?? 'Por asignar'}',
                      style: const TextStyle(fontSize: 13, color: _ink),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.pin_drop_outlined, size: 16, color: _muted),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text('Destino: ${d['delivery_address'] ?? 'Dirección registrada'}', style: const TextStyle(fontSize: 13, color: _ink)),
                  ),
                ],
              ),
              if (d['origin_branch_name'] != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(Icons.storefront_outlined, size: 16, color: _muted),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text('Sale de: ${d['origin_branch_name']}', style: const TextStyle(fontSize: 13, color: _ink)),
                    ),
                  ],
                ),
              ],
              if (d['delivered_at'] != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(Icons.check_circle_outline, size: 16, color: Colors.green),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Entregado el ${_fmtDateTime(d['delivered_at'])}'
                        '${d['received_by_name'] != null ? ' · recibió ${d['received_by_name']}' : ''}',
                        style: const TextStyle(fontSize: 13, color: _ink),
                      ),
                    ),
                  ],
                ),
              ],
              if (d['recipient_name'] != null) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(Icons.person_outline, size: 16, color: _muted),
                    const SizedBox(width: 6),
                    Text('Recibe: ${d['recipient_name']}', style: const TextStyle(fontSize: 13, color: _ink)),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Timeline de Hitos Logísticos
        Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFECE6E2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Línea de Tiempo de Entrega', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: _ink)),
              const SizedBox(height: 16),
              if (events.isEmpty)
                const Text('Aún no se registran hitos para este envío.', style: TextStyle(color: _muted, fontSize: 13))
              else
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: events.length,
                  itemBuilder: (context, i) {
                    final ev = events[i];
                    final isLast = i == events.length - 1;
                    return Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Column(
                          children: [
                            Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: isLast ? _brand : Colors.green,
                                border: Border.all(color: Colors.white, width: 2),
                                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 4)],
                              ),
                            ),
                            if (i < events.length - 1)
                              Container(
                                width: 2,
                                height: 44,
                                color: const Color(0xFFECE6E2),
                              ),
                          ],
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Expanded(
                                      child: Text(
                                        _statusText((ev['status'] ?? '').toString()),
                                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink),
                                      ),
                                    ),
                                    Text(
                                      _fmtDateTime(ev['created_at']),
                                      style: const TextStyle(fontSize: 11, color: _muted),
                                    ),
                                  ],
                                ),
                                if (ev['location'] != null)
                                  Text('📍 ${ev['location']}', style: const TextStyle(fontSize: 12, color: _muted)),
                                if (ev['description'] != null && ev['description'].toString().isNotEmpty)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 2),
                                    child: Text(ev['description'].toString(), style: const TextStyle(fontSize: 12, color: Colors.black87)),
                                  ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
            ],
          ),
        ),
      ],
    );
  }
}
