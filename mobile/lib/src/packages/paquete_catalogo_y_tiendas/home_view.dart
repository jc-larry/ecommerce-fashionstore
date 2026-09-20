import 'package:flutter/material.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';
import '../paquete_seguridad_usuarios/login_view.dart';
import '../paquete_paquete_ventas_y_pagos/customer_orders_view.dart';
import '../paquete_paquete_reservas_y_citas/reservations_view.dart';
import '../paquete_paquete_envios_y_logistica/tracking_view.dart';
import '../paquete_paquete_inteligente_y_analitica/virtual_tryon_view.dart';
import '../paquete_paquete_inteligente_y_analitica/chatbot_view.dart';
import '../paquete_paquete_notificaciones/notifications_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// Inicio del cliente: accesos directos a todas las funciones de la app, visibles desde el
/// primer momento (antes estaban escondidas en "Perfil" y solo tras iniciar sesión).
class HomeView extends StatefulWidget {
  /// Abre la pestaña Catálogo; si [voice] es true, arranca la búsqueda por voz (CU34).
  final void Function({bool voice}) onOpenCatalog;
  const HomeView({super.key, required this.onOpenCatalog});

  @override
  State<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<HomeView> {
  String? _userName;

  @override
  void initState() {
    super.initState();
    _loadUser();
  }

  Future<void> _loadUser() async {
    if (!await AuthService.isLoggedIn()) return;
    final u = await AuthService.getUser();
    if (mounted && u != null) setState(() => _userName = (u['first_name'] ?? '').toString());
  }

  /// Abre [page]; si la función necesita cuenta y no hay sesión, primero pide iniciar sesión.
  Future<void> _open(Widget page, {bool needsLogin = true}) async {
    if (needsLogin && !await AuthService.isLoggedIn()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Inicia sesión para usar esta función.')),
      );
      await Navigator.push(context, MaterialPageRoute(builder: (_) => const LoginView()));
      return;
    }
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final tiles = <_HomeTile>[
      _HomeTile(Icons.checkroom, 'Vestidor virtual', 'Pruébate prendas y calcula tu talla (CU32)',
          () => _open(const VirtualTryonView(), needsLogin: false)),
      _HomeTile(Icons.storefront_outlined, 'Reservar en tienda', 'Elige una prenda y apártala 48 h (CU26)',
          () => widget.onOpenCatalog()),
      _HomeTile(Icons.event_available_outlined, 'Mis reservas', 'Consulta o cancela tus citas (CU26/CU28)',
          () => _open(const ReservationsView())),
      _HomeTile(Icons.receipt_long_outlined, 'Mis compras y devoluciones', 'Pedidos, facturas y cambios (CU24/CU22)',
          () => _open(const CustomerOrdersView())),
      _HomeTile(Icons.local_shipping_outlined, 'Rastrear envío', 'Sigue tu pedido en tiempo real (CU30)',
          () => _open(const TrackingView(), needsLogin: false)),
      _HomeTile(Icons.notifications_none, 'Notificaciones', 'Avisos de pedidos y reservas (CU40)',
          () => _open(const NotificationsView())),
      _HomeTile(Icons.auto_awesome, 'Asistente IA', 'Recomendaciones de prendas y tallas (CU33)',
          () => _open(const ChatbotView(), needsLogin: false)),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        title: Text(
          _userName != null && _userName!.isNotEmpty ? 'Hola, $_userName' : 'FashionStore',
          style: const TextStyle(fontWeight: FontWeight.bold, color: _ink),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadUser,
        color: _brand,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Búsqueda (texto o voz) → catálogo
            Row(children: [
              Expanded(
                child: InkWell(
                  borderRadius: BorderRadius.circular(24),
                  onTap: () => widget.onOpenCatalog(),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24)),
                    child: const Row(children: [
                      Icon(Icons.search, color: _muted),
                      SizedBox(width: 8),
                      Text('Buscar prendas…', style: TextStyle(color: _muted)),
                    ]),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Material(
                color: _brand,
                shape: const CircleBorder(),
                child: IconButton(
                  tooltip: 'Buscar por voz (CU34)',
                  icon: const Icon(Icons.mic, color: Colors.white),
                  onPressed: () => widget.onOpenCatalog(voice: true),
                ),
              ),
            ]),
            const SizedBox(height: 6),
            const Padding(
              padding: EdgeInsets.only(left: 6),
              child: Text('Toca el micrófono y di, por ejemplo: "vestido rojo hasta 200"',
                  style: TextStyle(fontSize: 11, color: _muted)),
            ),
            const SizedBox(height: 18),

            // Pagos disponibles
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF6E3DD),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Row(children: [
                Icon(Icons.verified_user_outlined, color: _brand),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Paga tus compras y señas con Tarjeta, PayPal o QR. '
                    'Consulta el stock de cada sucursal en el detalle de la prenda.',
                    style: TextStyle(fontSize: 12, color: _ink),
                  ),
                ),
              ]),
            ),
            const SizedBox(height: 18),

            const Text('¿Qué quieres hacer?', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 10),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 1.15,
              children: tiles.map(_tile).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _tile(_HomeTile t) => InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: t.onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFECE6E2)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: const BoxDecoration(color: Color(0xFFF6E3DD), shape: BoxShape.circle),
              child: Icon(t.icon, color: _brand, size: 22),
            ),
            const Spacer(),
            Text(t.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: _ink)),
            const SizedBox(height: 2),
            Text(t.subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, color: _muted)),
          ]),
        ),
      );
}

class _HomeTile {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _HomeTile(this.icon, this.title, this.subtitle, this.onTap);
}
