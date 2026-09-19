// Smoke test básico: la app del cliente arranca en la tienda (catálogo + barra inferior).

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fashionstore_mobile/main.dart';

void main() {
  testWidgets('La app arranca en el Inicio con accesos a todas las funciones del cliente', (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const FashionStoreApp());
    await tester.pump();

    expect(find.text('Catálogo'), findsWidgets);
    expect(find.text('Carrito'), findsOneWidget);
    expect(find.text('Perfil'), findsOneWidget);
    // El Inicio muestra accesos directos a las funciones del cliente.
    expect(find.text('Vestidor virtual'), findsOneWidget);
    expect(find.text('Reservar en tienda'), findsOneWidget);
    expect(find.text('Mis compras y devoluciones'), findsOneWidget);
  });
}
