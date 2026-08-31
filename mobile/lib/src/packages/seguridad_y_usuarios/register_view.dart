import 'package:flutter/material.dart';
import 'auth_service.dart';
import 'password_strength_indicator.dart';

class RegisterView extends StatefulWidget {
  const RegisterView({super.key});

  @override
  State<RegisterView> createState() => _RegisterViewState();
}

class _RegisterViewState extends State<RegisterView> {
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _acceptTerms = false;
  bool _loading = false;
  String _currentPassword = '';

  @override
  void initState() {
    super.initState();
    _passwordController.addListener(() {
      setState(() {
        _currentPassword = _passwordController.text;
      });
    });
  }

  bool _isPasswordStrong(String password) {
    return password.length >= 8 &&
        RegExp(r'[A-Z]').hasMatch(password) &&
        RegExp(r'[a-z]').hasMatch(password) &&
        RegExp(r'[0-9]').hasMatch(password) &&
        RegExp(r'[@$!%*?&]').hasMatch(password);
  }

  void _onRegister() async {
    // [CU04] Auto-registro del propio cliente conectado a la API real
    final firstName = _firstNameController.text.trim();
    final lastName = _lastNameController.text.trim();
    final email = _emailController.text.trim();
    final phone = _phoneController.text.trim();
    // Se recorta el espacio que algunos teclados de Android agregan al final.
    final password = _passwordController.text.trim();
    final confirm = _confirmPasswordController.text.trim();

    if (firstName.isEmpty || lastName.isEmpty || email.isEmpty || phone.isEmpty || password.isEmpty || confirm.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, completa todos los campos')),
      );
      return;
    }

    if (!_isPasswordStrong(password)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('La contraseña no cumple con los requisitos de seguridad'),
          backgroundColor: Color(0xFFE53935),
        ),
      );
      return;
    }

    if (password != confirm) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Las contraseñas no coinciden')),
      );
      return;
    }

    if (!_acceptTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Debes aceptar los términos y condiciones')),
      );
      return;
    }

    setState(() => _loading = true);

    Map<String, dynamic> result;
    try {
      result = await AuthService.register(
        firstName: firstName,
        lastName: lastName,
        email: email,
        phone: phone,
        password: password,
      );
    } catch (e) {
      result = {'success': false, 'message': 'Error inesperado: $e'};
    } finally {
      if (mounted) setState(() => _loading = false);
    }

    if (!mounted) return;

    if (result['success'] == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('¡Cuenta creada con éxito! Ya puedes iniciar sesión.'),
          backgroundColor: Color(0xFF4CAF50),
        ),
      );
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message']?.toString() ?? 'No se pudo registrar la cuenta'),
          backgroundColor: const Color(0xFFE53935),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Color(0xFF2B1F1D)),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 8.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Crear cuenta',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2B1F1D),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Únete a la nueva experiencia de moda digital en Bolivia.',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF706361),
                ),
              ),
              const SizedBox(height: 24),

              // Nombre
              const Text(
                'Nombre',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _firstNameController,
                decoration: InputDecoration(
                  hintText: 'Juan',
                  prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF8C7E7B)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Apellido
              const Text(
                'Apellido',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _lastNameController,
                decoration: InputDecoration(
                  hintText: 'Pérez',
                  prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF8C7E7B)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Correo electrónico
              const Text(
                'Correo electrónico',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  hintText: 'juan@correo.com',
                  prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF8C7E7B)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Teléfono
              const Text(
                'Teléfono',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                decoration: InputDecoration(
                  hintText: '+591 70000000',
                  prefixIcon: const Icon(Icons.phone_outlined, color: Color(0xFF8C7E7B)),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Contraseña
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
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),

              // ✅ Indicador visual de requisitos de contraseña en tiempo real
              PasswordStrengthIndicator(password: _currentPassword),
              const SizedBox(height: 16),

              // Confirmar contraseña
              const Text(
                'Confirmar contraseña',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _confirmPasswordController,
                obscureText: _obscureConfirmPassword,
                autocorrect: false,
                enableSuggestions: false,
                textCapitalization: TextCapitalization.none,
                decoration: InputDecoration(
                  hintText: '••••••••',
                  prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF8C7E7B)),
                  suffixIcon: IconButton(
                    icon: Icon(
                      _obscureConfirmPassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      color: const Color(0xFF8C7E7B),
                    ),
                    onPressed: () {
                      setState(() {
                        _obscureConfirmPassword = !_obscureConfirmPassword;
                      });
                    },
                  ),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFD4CECB)),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Checkbox Términos y condiciones
              Row(
                children: [
                  Checkbox(
                    value: _acceptTerms,
                    activeColor: const Color(0xFFC66F5C),
                    onChanged: (val) {
                      setState(() {
                        _acceptTerms = val ?? false;
                      });
                    },
                  ),
                  const Expanded(
                    child: Text(
                      'Acepto los Términos y condiciones y políticas de privacidad.',
                      style: TextStyle(color: Color(0xFF706361), fontSize: 13),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Botón crear cuenta
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
                  onPressed: _loading ? null : _onRegister,
                  child: _loading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Text(
                          'Crear mi cuenta',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
              const SizedBox(height: 24),

              // Volver a login link
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    '¿Ya tienes cuenta? ',
                    style: TextStyle(color: Color(0xFF706361), fontSize: 14),
                  ),
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: const Text(
                      'Inicia sesión',
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
      ),
    );
  }
}
