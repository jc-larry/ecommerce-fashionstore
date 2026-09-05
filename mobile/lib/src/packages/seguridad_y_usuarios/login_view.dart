import 'package:flutter/material.dart';
import 'auth_service.dart';
import 'register_view.dart';
import 'recover_view.dart';
import '../catalogo_y_tiendas/store_shell.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
}

class _LoginViewState extends State<LoginView> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _loading = false;

  void _onLogin() async {
    // [CU01] Inicio de sesión conectado a la API REST.
    // El correo va en minúsculas y sin espacios; la contraseña se recorta de espacios
    // al inicio/fin (el teclado de Android suele añadir uno).
    final email = _emailController.text.trim().toLowerCase();
    final password = _passwordController.text.trim();

    if (email.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, completa todos los campos')),
      );
      return;
    }

    final emailRegex = RegExp(r'^[\w.\-]+@[\w\-]+\.[\w\-.]+$');
    if (!emailRegex.hasMatch(email)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingresa un correo electrónico válido')),
      );
      return;
    }

    setState(() => _loading = true);

    Map<String, dynamic> result;
    try {
      result = await AuthService.login(email, password);
    } catch (e) {
      result = {'success': false, 'message': 'Error inesperado: $e'};
    } finally {
      if (mounted) setState(() => _loading = false);
    }

    if (!mounted) return;

    if (result['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('¡Sesión iniciada con éxito!'),
          backgroundColor: Color(0xFF4CAF50),
        ),
      );
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const StoreShell()),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message']?.toString() ?? 'No se pudo iniciar sesión'),
          backgroundColor: const Color(0xFFE53935),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Banner superior premium (estilo editorial de moda)
            Stack(
              children: [
                SizedBox(
                  height: 280,
                  width: double.infinity,
                  child: Image.network(
                    'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=80&w=1000',
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Container(color: const Color(0xFFC66F5C)),
                    loadingBuilder: (context, child, progress) =>
                        progress == null ? child : Container(color: const Color(0xFFE9D7D1)),
                  ),
                ),
                Container(
                  height: 280,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.black.withOpacity(0.3), Colors.black.withOpacity(0.75)],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ),
                  ),
                ),
                Positioned(
                  bottom: 24,
                  left: 24,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text(
                        'FashionStore',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          letterSpacing: -0.5,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'AR VIRTUAL DRESSING ROOM',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            // Formulario de login
            Padding(
              padding: const EdgeInsets.all(24.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Te damos la bienvenida',
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF2B1F1D),
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Inicia sesión para explorar colecciones exclusivas y probarlas en realidad aumentada.',
                    style: TextStyle(
                      fontSize: 14,
                      color: Color(0xFF706361),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Input Email
                  const Text(
                    'Correo electrónico',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    decoration: InputDecoration(
                      hintText: 'ejemplo@correo.com',
                      prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF8C7E7B)),
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding: const EdgeInsets.symmetric(vertical: 14),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFC66F5C)),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Input Password
                  const Text(
                    'Contraseña',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    autocorrect: false,
                    enableSuggestions: false,
                    textCapitalization: TextCapitalization.none,
                    decoration: InputDecoration(
                      hintText: '••••••••',
                      prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF8C7E7B)),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                          color: const Color(0xFF8C7E7B),
                        ),
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                      ),
                      filled: true,
                      fillColor: Colors.white,
                      contentPadding: const EdgeInsets.symmetric(vertical: 14),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFFC66F5C)),
                      ),
                    ),
                  ),

                  // [CU03] Olvidé mi contraseña
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const RecoverView()),
                        );
                      },
                      child: const Text(
                        '¿Olvidé mi contraseña?',
                        style: TextStyle(
                          color: Color(0xFFC66F5C),
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // [CU01] Botón Iniciar Sesión
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFC66F5C),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                      onPressed: _loading ? null : _onLogin,
                      child: _loading
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : const Text(
                              'Iniciar Sesión',
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Divisor O INICIA CON
                  Row(
                    children: const [
                      Expanded(child: Divider(color: Color(0xFFD4CECB))),
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 16.0),
                        child: Text(
                          'O INICIA CON',
                          style: TextStyle(color: Color(0xFF8C7E7B), fontSize: 12),
                        ),
                      ),
                      Expanded(child: Divider(color: Color(0xFFD4CECB))),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Botón Google
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFF2B1F1D),
                        side: const BorderSide(color: Color(0xFFD4CECB)),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      icon: const Icon(Icons.g_mobiledata, size: 28, color: Colors.red),
                      label: const Text(
                        'Continuar con Google',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                      ),
                      onPressed: () {},
                    ),
                  ),
                  const SizedBox(height: 32),

                  // [CU04] Crear Cuenta Link
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        '¿No tienes una cuenta? ',
                        style: TextStyle(color: Color(0xFF706361), fontSize: 14),
                      ),
                      GestureDetector(
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (context) => const RegisterView()),
                          );
                        },
                        child: const Text(
                          'Crear cuenta',
                          style: TextStyle(
                            color: Color(0xFFC66F5C),
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
