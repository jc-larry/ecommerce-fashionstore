import 'package:flutter/material.dart';
import '../seguridad_y_usuarios/auth_service.dart';
import '../seguridad_y_usuarios/login_view.dart';
import 'catalogo_view.dart';
import 'wishlist_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// Shell del cliente: barra inferior Inicio · Catálogo · Carrito · Favoritos · Perfil.
class StoreShell extends StatefulWidget {
  const StoreShell({super.key});

  @override
  State<StoreShell> createState() => _StoreShellState();
}

class _StoreShellState extends State<StoreShell> {
  int _index = 1; // arranca en Catálogo

  @override
  Widget build(BuildContext context) {
    final pages = <Widget>[
      const CatalogoView(),          // Inicio (mismo catálogo)
      const CatalogoView(),          // Catálogo
      const _ComingSoon(icon: Icons.shopping_bag_outlined, label: 'El carrito llega en la próxima versión'),
      const WishlistView(),          // Favoritos
      const _ProfileTab(),           // Perfil
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) {
          if (i == 2) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('El carrito llega en la próxima versión.')),
            );
          }
          setState(() => _index = i);
        },
        indicatorColor: const Color(0xFFF6E3DD),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home, color: _brand), label: 'Inicio'),
          NavigationDestination(icon: Icon(Icons.grid_view_outlined), selectedIcon: Icon(Icons.grid_view, color: _brand), label: 'Catálogo'),
          NavigationDestination(icon: Icon(Icons.shopping_bag_outlined), label: 'Carrito'),
          NavigationDestination(icon: Icon(Icons.favorite_border), selectedIcon: Icon(Icons.favorite, color: _brand), label: 'Favoritos'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person, color: _brand), label: 'Perfil'),
        ],
      ),
    );
  }
}

class _ComingSoon extends StatelessWidget {
  final IconData icon;
  final String label;
  const _ComingSoon({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: const Color(0xFFFCFBFA),
        appBar: AppBar(backgroundColor: Colors.white, elevation: 0),
        body: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 48, color: const Color(0xFFD4CECB)),
            const SizedBox(height: 12),
            Text(label, style: const TextStyle(color: _muted)),
          ]),
        ),
      );
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab();

  Future<void> _logout(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cerrar sesión'),
        content: const Text('¿Seguro que quieres cerrar tu sesión?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Cerrar sesión', style: TextStyle(color: _brand))),
        ],
      ),
    );
    if (ok != true) return;
    await AuthService.logout();
    if (!context.mounted) return;
    Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const LoginView()), (r) => false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.white, elevation: 0,
        title: const Text('Mi perfil', style: TextStyle(color: _ink, fontWeight: FontWeight.bold)),
      ),
      body: ListView(children: [
        const SizedBox(height: 12),
        const ListTile(
          leading: CircleAvatar(backgroundColor: _brand, child: Icon(Icons.person, color: Colors.white)),
          title: Text('Cliente FashionStore'),
          subtitle: Text('Explora el catálogo y guarda tus favoritas'),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.favorite_border, color: _muted),
          title: const Text('Mis favoritos'),
          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WishlistView())),
        ),
        ListTile(
          leading: const Icon(Icons.logout, color: _brand),
          title: const Text('Cerrar sesión', style: TextStyle(color: _brand)),
          onTap: () => _logout(context),
        ),
      ]),
    );
  }
}
