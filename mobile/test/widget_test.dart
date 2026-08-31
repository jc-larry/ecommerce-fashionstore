// Smoke test básico: la app arranca en la pantalla de inicio de sesión.

import 'package:flutter_test/flutter_test.dart';
import 'package:fashionstore_mobile/main.dart';

void main() {
  testWidgets('La app muestra la pantalla de inicio de sesión', (WidgetTester tester) async {
    await tester.pumpWidget(const FashionStoreApp());
    await tester.pump();

    expect(find.text('FashionStore'), findsWidgets);
    expect(find.text('Iniciar Sesión'), findsOneWidget);
  });
}
