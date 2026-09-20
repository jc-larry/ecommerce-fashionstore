import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU40] Centro de Notificaciones In-App y Push (App Móvil).
/// Permite al usuario revisar avisos de cambios de estado en sus pedidos,
/// actualizaciones de despacho y rastreo, y confirmaciones de reservas.
class NotificationsView extends StatefulWidget {
  const NotificationsView({super.key});

  @override
  State<NotificationsView> createState() => _NotificationsViewState();
}

class _NotificationsViewState extends State<NotificationsView> {
  bool _loading = true;
  String? _error;
  List<dynamic> _notifications = [];
  int _unreadCount = 0;

  @override
  void initState() {
    super.initState();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await AuthService.getToken();
      if (token == null) {
        setState(() {
          _loading = false;
          _error = 'Inicia sesión para consultar tus paquete_notificaciones.';
        });
        return;
      }

      final url = Uri.parse('${AuthService.apiBaseUrl}/notifications/my?limit=50');
      final res = await http.get(url, headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      }).timeout(const Duration(seconds: 10));

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _notifications = data is Map ? List<dynamic>.from(data['notifications'] ?? const []) : [];
          _unreadCount = data is Map ? (data['unread_count'] as num? ?? 0).toInt() : 0;
          _loading = false;
        });
      } else {
        setState(() {
          _loading = false;
          _error = 'No se pudieron cargar las paquete_notificaciones.';
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'No se pudo conectar con el servidor. Intenta nuevamente.';
      });
    }
  }

  Future<void> _markAsRead(int id) async {
    final index = _notifications.indexWhere((n) => n['id'] == id);
    if (index == -1 || _notifications[index]['is_read'] == true) return;
    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/notifications/$id/read');
      final res = await http.patch(url, headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      });
      if (res.statusCode == 200 && mounted) {
        setState(() {
          _notifications[index]['is_read'] = true;
          if (_unreadCount > 0) _unreadCount--;
        });
      }
    } catch (_) {}
  }

  Future<void> _markAllAsRead() async {
    try {
      final token = await AuthService.getToken();
      final res = await http.post(
        Uri.parse('${AuthService.apiBaseUrl}/notifications/mark-all-read'),
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
      );
      if (res.statusCode == 200 && mounted) {
        setState(() {
          for (final n in _notifications) {
            n['is_read'] = true;
          }
          _unreadCount = 0;
        });
      }
    } catch (_) {}
  }

  IconData _getTypeIcon(String type) {
    switch (type.toUpperCase()) {
      case 'ENVIO':
      case 'SHIPMENT':
        return Icons.local_shipping_outlined;
      case 'RESERVA':
      case 'RESERVATION':
        return Icons.calendar_today_outlined;
      case 'PEDIDO':
      case 'ORDER':
        return Icons.receipt_long_outlined;
      case 'PROMO':
      case 'PROMOTION':
        return Icons.local_offer_outlined;
      default:
        return Icons.notifications_none;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        title: Text(
          _unreadCount > 0 ? 'Notificaciones ($_unreadCount)' : 'Notificaciones',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        actions: [
          if (_unreadCount > 0)
            IconButton(
              icon: const Icon(Icons.done_all),
              onPressed: _markAllAsRead,
              tooltip: 'Marcar todas como leídas',
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadNotifications,
            tooltip: 'Actualizar',
          ),
        ],
      ),
      body: _buildContent(),
    );
  }

  Widget _buildContent() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: _brand));
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.notifications_off_outlined, size: 48, color: _muted),
              const SizedBox(height: 12),
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: _muted)),
              const SizedBox(height: 16),
              ElevatedButton(onPressed: _loadNotifications, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    if (_notifications.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: const BoxDecoration(shape: BoxShape.circle, color: Color(0xFFF6E3DD)),
                child: const Icon(Icons.notifications_none, size: 48, color: _brand),
              ),
              const SizedBox(height: 16),
              const Text('Sin paquete_notificaciones recientes', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: _ink)),
              const SizedBox(height: 6),
              const Text('Te avisaremos cuando tu reserva esté lista o tu envío se encuentre en camino.', textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: _muted)),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadNotifications,
      color: _brand,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _notifications.length,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          final n = _notifications[index];
          final isRead = n['is_read'] == true;
          final type = (n['notification_type'] ?? 'GENERAL').toString();
          final title = n['title'] ?? 'Notificación';
          final message = n['message'] ?? '';
          final date = (n['created_at'] ?? '').toString().split('T').first;

          return InkWell(
            onTap: () => _markAsRead(n['id']),
            borderRadius: BorderRadius.circular(14),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: isRead ? Colors.white : const Color(0xFFFFF9F8),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: isRead ? const Color(0xFFECE6E2) : const Color(0xFFF3C7BE)),
                boxShadow: isRead ? null : [BoxShadow(color: _brand.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 2))],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 20,
                    backgroundColor: isRead ? const Color(0xFFF8F6F4) : const Color(0xFFF6E3DD),
                    child: Icon(_getTypeIcon(type), size: 20, color: isRead ? _muted : _brand),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(
                              child: Text(
                                title,
                                style: TextStyle(
                                  fontSize: 13.5,
                                  fontWeight: isRead ? FontWeight.w600 : FontWeight.bold,
                                  color: _ink,
                                ),
                              ),
                            ),
                            if (!isRead)
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(shape: BoxShape.circle, color: _brand),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(message, style: const TextStyle(fontSize: 12.5, color: _muted, height: 1.3)),
                        const SizedBox(height: 6),
                        Text(date, style: const TextStyle(fontSize: 11, color: Color(0xFFA89C9A))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
