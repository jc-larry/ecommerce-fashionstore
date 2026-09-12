import 'package:flutter/material.dart';
import '../seguridad_y_usuarios/auth_service.dart';
import '../seguridad_y_usuarios/login_view.dart';
import '../seguridad_y_usuarios/register_view.dart';
import 'catalogo_view.dart';
import 'wishlist_view.dart';
import '../ventas_y_pagos/cart_view.dart';
import '../ventas_y_pagos/customer_orders_view.dart';

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
      const CartView(),              // Carrito Digital (CU17)
      const WishlistView(),          // Favoritos
      const _ProfileTab(),           // Perfil
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) {
          setState(() => _index = i);
        },
        indicatorColor: const Color(0xFFF6E3DD),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home, color: _brand), label: 'Inicio'),
          NavigationDestination(icon: Icon(Icons.grid_view_outlined), selectedIcon: Icon(Icons.grid_view, color: _brand), label: 'Catálogo'),
          NavigationDestination(icon: Icon(Icons.shopping_bag_outlined), selectedIcon: Icon(Icons.shopping_bag, color: _brand), label: 'Carrito'),
          NavigationDestination(icon: Icon(Icons.favorite_border), selectedIcon: Icon(Icons.favorite, color: _brand), label: 'Favoritos'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person, color: _brand), label: 'Perfil'),
        ],
      ),
    );
  }
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
    Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => const StoreShell()), (r) => false);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: AuthService.isLoggedIn(),
      builder: (context, snapshot) {
        final isLoggedIn = snapshot.data == true;

        return Scaffold(
          backgroundColor: const Color(0xFFFCFBFA),
          appBar: AppBar(
            backgroundColor: Colors.white,
            elevation: 0,
            title: Text(
              isLoggedIn ? 'Mi perfil' : 'Cuenta de usuario',
              style: const TextStyle(color: _ink, fontWeight: FontWeight.bold),
            ),
          ),
          body: isLoggedIn
              ? ListView(children: [
                  const SizedBox(height: 12),
                  const ListTile(
                    leading: CircleAvatar(backgroundColor: _brand, child: Icon(Icons.person, color: Colors.white)),
                    title: Text('Cliente FashionStore'),
                    subtitle: Text('Sesión activa en tu dispositivo'),
                  ),
                  const Divider(),
                  ListTile(
                    leading: const Icon(Icons.favorite_border, color: _muted),
                    title: const Text('Mis favoritos'),
                    onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WishlistView())),
                  ),
                  ListTile(
                    leading: const Icon(Icons.receipt_long_outlined, color: _muted),
                    title: const Text('Mis pedidos y compras (CU24)'),
                    onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CustomerOrdersView())),
                  ),
                  ListTile(
                    leading: const Icon(Icons.logout, color: _brand),
                    title: const Text('Cerrar sesión', style: TextStyle(color: _brand)),
                    onTap: () => _logout(context),
                  ),
                ])
              : Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: const BoxDecoration(
                          color: Color(0x1AC66F5C),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.person_outline, size: 40, color: _brand),
                      ),
                      const SizedBox(height: 20),
                      const Text(
                        '¡Te damos la bienvenida!',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: _ink),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Inicia sesión o crea tu cuenta para guardar prendas favoritas, revisar tus pedidos y coordinar tus compras.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 14, color: _muted, height: 1.4),
                      ),
                      const SizedBox(height: 32),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.push(context, MaterialPageRoute(builder: (_) => const LoginView()));
                          },
                          child: const Text('Iniciar Sesión', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: OutlinedButton(
                          onPressed: () {
                            Navigator.push(context, MaterialPageRoute(builder: (_) => const RegisterView()));
                          },
                          child: const Text('Crear Cuenta Nueva', style: TextStyle(fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
        );
      },
    );
  }
}
