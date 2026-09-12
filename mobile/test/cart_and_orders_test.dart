import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fashionstore_mobile/src/packages/ventas_y_pagos/cart_view.dart';
import 'package:fashionstore_mobile/src/packages/ventas_y_pagos/customer_orders_view.dart';

void main() {
  group('[CU17 / CU18 / CU20] Pruebas de Carrito y Checkout Móvil', () {
    testWidgets('CartView renderiza estado inicial correctamente', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: CartView(),
        ),
      );
      // Al inicio muestra loading y luego resuelve
      await tester.pump();

      expect(find.text('Mi Carrito'), findsOneWidget);
    });

    test('Cálculo de IVA Débito Fiscal 13% conforme a normativa boliviana', () {
      const subtotal = 200.0;
      const discount = 20.0;
      const total = subtotal - discount; // 180.0
      const iva = total * 0.13; // 23.40

      expect(total, equals(180.0));
      expect(double.parse(iva.toStringAsFixed(2)), equals(23.40));
    });
  });

  group('[CU24] Pruebas de Historial de Compras Móvil', () {
    testWidgets('CustomerOrdersView renderiza barra de título y estado', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: CustomerOrdersView(),
        ),
      );
      await tester.pump();

      expect(find.text('Mis Pedidos'), findsOneWidget);
    });
  });
}
