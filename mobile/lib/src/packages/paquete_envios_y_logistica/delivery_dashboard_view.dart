import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import '../paquete_paquete_catalogo_y_tiendas/store_shell.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU29, CU30] Dashboard móvil para Repartidores de Logística y Última Milla.
/// Permite auto-seleccionar pedidos disponibles de la bolsa, avanzar estados en ruta
/// reportar entregas fallidas, confirmar la entrega con foto de evidencia y consultar su historial.
class DeliveryDashboardView extends StatefulWidget {
  const DeliveryDashboardView({super.key});

  @override
  State<DeliveryDashboardView> createState() => _DeliveryDashboardViewState();
}

class _DeliveryDashboardViewState extends State<DeliveryDashboardView> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isAvailable = true;
  bool _loading = false;
  List<dynamic> _availableShipments = [];
  List<dynamic> _myShipments = [];
  List<dynamic> _history = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadAll();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadAll() async {
    setState(() => _loading = true);
    await Future.wait([_loadProfile(), _loadAvailable(), _loadMyActive(), _loadHistory()]);
    if (mounted) setState(() => _loading = false);
  }

  /// Disponibilidad real del repartidor (no se asume "Disponible").
  Future<void> _loadProfile() async {
    try {
      final token = await AuthService.getToken();
      final res = await http.get(
        Uri.parse('${AuthService.apiBaseUrl}/logistics/delivery-persons/my'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (res.statusCode == 200 && mounted) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() => _isAvailable = data['is_available'] == true);
      }
    } catch (_) {}
  }

  /// Historial de envíos entregados/fallidos con sus tiempos.
  Future<void> _loadHistory() async {
    try {
      final token = await AuthService.getToken();
      final res = await http.get(
        Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/my-history'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (res.statusCode == 200 && mounted) {
        setState(() => _history = jsonDecode(utf8.decode(res.bodyBytes)));
      }
    } catch (_) {}
  }

  Future<void> _logout() async {
    await AuthService.logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const StoreShell()),
      (r) => false,
    );
  }

  Future<void> _loadAvailable() async {
    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/available');
      final res = await http.get(url, headers: {'Authorization': 'Bearer $token'});
      if (res.statusCode == 200) {
        setState(() {
          _availableShipments = jsonDecode(utf8.decode(res.bodyBytes));
        });
      }
    } catch (_) {}
  }

  Future<void> _loadMyActive() async {
    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/my-active');
      final res = await http.get(url, headers: {'Authorization': 'Bearer $token'});
      if (res.statusCode == 200) {
        setState(() {
          _myShipments = jsonDecode(utf8.decode(res.bodyBytes));
        });
      }
    } catch (_) {}
  }

  Future<void> _claimShipment(int shipmentId) async {
    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/$shipmentId/claim');
      final res = await http.post(url, headers: {'Authorization': 'Bearer $token'});
      if (!mounted) return;
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(backgroundColor: Colors.green, content: Text('¡Has tomado el pedido! Ya está en tus entregas activas.')),
        );
        _loadAll();
      } else {
        final err = jsonDecode(utf8.decode(res.bodyBytes));
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: ${err['detail'] ?? 'No se pudo tomar'}')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _updateRouteStatus(int shipmentId, String newStatus) async {
    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/$shipmentId/route-status');
      final res = await http.patch(
        url,
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
        body: jsonEncode({'status': newStatus}),
      );
      if (!mounted) return;
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Estado actualizado a $newStatus')));
        _loadMyActive();
      } else {
        _showApiError(res);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  void _showApiError(http.Response res) {
    String msg = 'No se pudo completar la acción';
    try {
      msg = jsonDecode(utf8.decode(res.bodyBytes))['detail']?.toString() ?? msg;
    } catch (_) {}
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: Colors.red, content: Text(msg)));
  }

  /// Toma la foto de evidencia con la cámara, pide quién recibió y confirma la entrega.
  Future<void> _confirmDeliveryWithPhoto(Map<String, dynamic> shipment) async {
    final photo = await ImagePicker().pickImage(
      source: ImageSource.camera,
      maxWidth: 1024,
      maxHeight: 1024,
      imageQuality: 60,
    );
    if (photo == null || !mounted) return;
    final bytes = await photo.readAsBytes();
    final dataUrl = 'data:image/jpeg;base64,${base64Encode(bytes)}';
    final receivedCtrl = TextEditingController(text: shipment['recipient_name']?.toString() ?? '');

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirmar entrega', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.memory(bytes, height: 180, fit: BoxFit.cover),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: receivedCtrl,
              decoration: InputDecoration(
                labelText: '¿Quién recibió el pedido?',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirmar', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    if (receivedCtrl.text.trim().length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Indica quién recibió el pedido.')));
      return;
    }

    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/${shipment['id']}/confirm-delivery');
      final res = await http.post(
        url,
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
        body: jsonEncode({'photo_data_url': dataUrl, 'received_by_name': receivedCtrl.text.trim()}),
      );
      if (!mounted) return;
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(backgroundColor: Colors.green, content: Text('Entrega confirmada con evidencia fotográfica.')),
        );
        _loadMyActive();
        _loadHistory();
      } else {
        _showApiError(res);
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  void _showFailedReportDialog(int shipmentId) {
    final reasonCtrl = TextEditingController(text: 'Cliente ausente');
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Reportar Intento Fallido', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Indica el motivo por el cual no se pudo entregar:', style: TextStyle(fontSize: 12, color: _muted)),
              const SizedBox(height: 10),
              TextField(
                controller: reasonCtrl,
                decoration: InputDecoration(
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  hintText: 'Ej: Cliente ausente / Teléfono apagado',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                Navigator.pop(ctx);
                final token = await AuthService.getToken();
                final url = Uri.parse('${AuthService.apiBaseUrl}/logistics/shipments/$shipmentId/failed-delivery');
                final res = await http.post(
                  url,
                  headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
                  body: jsonEncode({'reason': reasonCtrl.text.trim()}),
                );
                if (res.statusCode == 200) {
                  messenger.showSnackBar(const SnackBar(content: Text('Intento fallido registrado.')));
                  _loadMyActive();
                }
              },
              child: const Text('Confirmar Fallo', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Panel del Repartidor', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        backgroundColor: _brand,
        foregroundColor: Colors.white,
        actions: [
          Row(
            children: [
              Text(_isAvailable ? 'Disponible' : 'Pausado', style: const TextStyle(fontSize: 12)),
              Switch(
                value: _isAvailable,
                activeThumbColor: Colors.white,
                activeTrackColor: Colors.green,
                onChanged: (val) async {
                  final previous = _isAvailable;
                  setState(() => _isAvailable = val);
                  try {
                    final token = await AuthService.getToken();
                    final res = await http.patch(
                      Uri.parse('${AuthService.apiBaseUrl}/logistics/delivery-persons/availability?is_available=$val'),
                      headers: {'Authorization': 'Bearer $token'},
                    );
                    if (res.statusCode != 200) {
                      if (mounted) setState(() => _isAvailable = previous);
                      _showApiError(res);
                    }
                  } catch (_) {
                    if (mounted) setState(() => _isAvailable = previous);
                  }
                },
              ),
            ],
          ),
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          tabs: [
            Tab(text: 'Bolsa (${_availableShipments.length})'),
            Tab(text: 'Mis Entregas (${_myShipments.length})'),
            Tab(text: 'Historial (${_history.length})'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _brand))
          : TabBarView(
              controller: _tabController,
              children: [
                _buildAvailableList(),
                _buildMyList(),
                _buildHistoryList(),
              ],
            ),
    );
  }

  Widget _buildAvailableList() {
    if (_availableShipments.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadAll,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.inbox, size: 50, color: _muted),
              SizedBox(height: 10),
              Text('No hay pedidos pendientes en la bolsa de Santa Cruz', style: TextStyle(color: _muted)),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _availableShipments.length,
        itemBuilder: (ctx, i) {
          final s = _availableShipments[i];
          return Card(
            elevation: 2,
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Guía: ${s['tracking_number']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _ink)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(8)),
                        child: Text(s['status'] ?? 'DISPONIBLE', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.blue.shade800)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.location_on, size: 16, color: _brand),
                      const SizedBox(width: 6),
                      Expanded(child: Text(s['delivery_address'] ?? 'Santa Cruz', style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.person, size: 16, color: _muted),
                      const SizedBox(width: 6),
                      Text('Destinatario: ${s['recipient_name'] ?? 'Cliente'} (${s['recipient_phone'] ?? ''})', style: const TextStyle(fontSize: 12, color: _muted)),
                    ],
                  ),
                  const Divider(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Flete: Bs. ${s['shipping_cost'] ?? 15}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _brand)),
                      ElevatedButton.icon(
                        onPressed: () => _claimShipment(s['id']),
                        icon: const Icon(Icons.check, size: 16, color: Colors.white),
                        label: const Text('Tomar Pedido', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(backgroundColor: _brand, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildMyList() {
    if (_myShipments.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadAll,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.two_wheeler, size: 50, color: _muted),
              SizedBox(height: 10),
              Text('No tienes entregas activas en este momento', style: TextStyle(color: _muted)),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _myShipments.length,
        itemBuilder: (ctx, i) {
          final s = _myShipments[i];
          final status = s['status'] ?? 'ASSIGNED';
          return Card(
            elevation: 3,
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Guía: ${s['tracking_number']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(color: Colors.orange.shade50, borderRadius: BorderRadius.circular(8)),
                        child: Text(status, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.orange.shade800)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Dirección: ${s['delivery_address']}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                  Text('Cliente: ${s['recipient_name']} (Tel: ${s['recipient_phone']})', style: const TextStyle(fontSize: 12, color: _muted)),
                  const Divider(height: 16),
                  const Text('Actualizar estado de entrega:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _ink)),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      if (status == 'ASSIGNED')
                        ActionChip(
                          avatar: const Icon(Icons.store, size: 16),
                          label: const Text('1. Recoger en Tienda'),
                          onPressed: () => _updateRouteStatus(s['id'], 'PICKED_UP'),
                        ),
                      if (status == 'PICKED_UP' || status == 'FAILED_ATTEMPT' || status == 'RESCHEDULED')
                        ActionChip(
                          avatar: const Icon(Icons.two_wheeler, size: 16),
                          label: const Text('2. Salir en Camino'),
                          onPressed: () => _updateRouteStatus(s['id'], 'IN_TRANSIT'),
                        ),
                      if (status == 'IN_TRANSIT')
                        ActionChip(
                          avatar: const Icon(Icons.location_on, size: 16),
                          label: const Text('3. Llegué al Destino'),
                          onPressed: () => _updateRouteStatus(s['id'], 'OUT_FOR_DELIVERY'),
                        ),
                      if (['PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'FAILED_ATTEMPT'].contains(status))
                        ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                          icon: const Icon(Icons.photo_camera, size: 16, color: Colors.white),
                          label: const Text('4. Entregar (con foto)', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                          onPressed: () => _confirmDeliveryWithPhoto(Map<String, dynamic>.from(s)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                        icon: const Icon(Icons.report_problem, size: 16),
                        label: const Text('Cliente Ausente / Fallo'),
                        onPressed: () => _showFailedReportDialog(s['id']),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
  /// Minutos entre que el repartidor tomó el pedido y lo entregó (null si falta un dato).
  int? _durationMinutes(Map<String, dynamic> s) {
    final start = DateTime.tryParse((s['claimed_at'] ?? s['dispatched_at'] ?? '').toString());
    final end = DateTime.tryParse((s['delivered_at'] ?? '').toString());
    if (start == null || end == null) return null;
    return end.difference(start).inMinutes;
  }

  String _fmtDateTime(dynamic raw) {
    final d = DateTime.tryParse((raw ?? '').toString())?.toLocal();
    if (d == null) return '—';
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(d.day)}/${two(d.month)}/${d.year} ${two(d.hour)}:${two(d.minute)}';
  }

  /// Foto de evidencia: el backend la guarda como data URL (base64); se aceptan también URLs.
  Widget _evidenceImage(String photo) {
    const h = 120.0;
    Widget fallback(BuildContext _, Object __, StackTrace? ___) => const SizedBox.shrink();
    if (photo.startsWith('data:')) {
      try {
        final bytes = base64Decode(photo.substring(photo.indexOf(',') + 1));
        return Image.memory(bytes, height: h, width: double.infinity, fit: BoxFit.cover, errorBuilder: fallback);
      } catch (_) {
        return const SizedBox.shrink();
      }
    }
    final origin = AuthService.apiBaseUrl.replaceAll(RegExp(r'/api/v1/?$'), '');
    final url = photo.startsWith('http') ? photo : '$origin$photo';
    return Image.network(url, height: h, width: double.infinity, fit: BoxFit.cover, errorBuilder: fallback);
  }

  Widget _buildHistoryList() {
    if (_history.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadAll,
        child: ListView(
          children: const [
            SizedBox(height: 120),
            Icon(Icons.history, size: 50, color: _muted),
            SizedBox(height: 10),
            Center(child: Text('Aún no tienes entregas registradas', style: TextStyle(color: _muted))),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _history.length,
        itemBuilder: (ctx, i) {
          final s = Map<String, dynamic>.from(_history[i] as Map);
          final delivered = s['status'] == 'DELIVERED';
          final minutes = _durationMinutes(s);
          final photo = s['delivery_photo_url']?.toString() ?? '';
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Guía: ${s['tracking_number']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: _ink)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: delivered ? Colors.green.shade50 : Colors.red.shade50,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          delivered ? 'ENTREGADO' : (s['status'] ?? '').toString().replaceAll('_', ' '),
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: delivered ? Colors.green.shade800 : Colors.red.shade800,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(s['delivery_address']?.toString() ?? '', style: const TextStyle(fontSize: 13)),
                  const SizedBox(height: 6),
                  Text('Tomado: ${_fmtDateTime(s['claimed_at'])}', style: const TextStyle(fontSize: 12, color: _muted)),
                  Text('Entregado: ${_fmtDateTime(s['delivered_at'])}', style: const TextStyle(fontSize: 12, color: _muted)),
                  if (minutes != null)
                    Text('Tiempo de entrega: $minutes min',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand)),
                  if (s['received_by_name'] != null)
                    Text('Recibió: ${s['received_by_name']}', style: const TextStyle(fontSize: 12, color: _ink)),
                  if (s['failed_reason'] != null && !delivered)
                    Text('Motivo: ${s['failed_reason']}', style: const TextStyle(fontSize: 12, color: Colors.red)),
                  if (photo.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: _evidenceImage(photo),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
