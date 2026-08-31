import 'package:flutter/material.dart';
import 'src/packages/seguridad_y_usuarios/login_view.dart';

void main() {
  runApp(const FashionStoreApp());
}

class FashionStoreApp extends StatelessWidget {
  const FashionStoreApp({super.key});

  // Paleta de marca (terracota)
  static const Color _brand = Color(0xFFC66F5C);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FashionStore Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: _brand,
          primary: _brand,
        ),
        scaffoldBackgroundColor: const Color(0xFFFCFBFA),
        fontFamily: 'Roboto',
      ),
      home: const LoginView(),
    );
  }
}
