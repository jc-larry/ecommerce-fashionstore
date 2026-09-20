import 'package:flutter/material.dart';

/// Widget reutilizable que muestra el indicador visual en tiempo real
/// de los requisitos de seguridad de la contraseña.
/// Se usa en register_view.dart y en la pantalla de reset de contraseña.
class PasswordStrengthIndicator extends StatelessWidget {
  final String password;

  const PasswordStrengthIndicator({super.key, required this.password});

  bool get _hasMinLength => password.length >= 8;
  bool get _hasUppercase => RegExp(r'[A-Z]').hasMatch(password);
  bool get _hasLowercase => RegExp(r'[a-z]').hasMatch(password);
  bool get _hasNumber => RegExp(r'[0-9]').hasMatch(password);
  bool get _hasSpecial => RegExp(r'[@$!%*?&]').hasMatch(password);

  bool get isValid => _hasMinLength && _hasUppercase && _hasLowercase && _hasNumber && _hasSpecial;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        const Text(
          'Requisitos de seguridad:',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Color(0xFF706361),
          ),
        ),
        const SizedBox(height: 6),
        _buildRule('Mínimo 8 caracteres', _hasMinLength),
        _buildRule('Al menos una mayúscula (A-Z)', _hasUppercase),
        _buildRule('Al menos una minúscula (a-z)', _hasLowercase),
        _buildRule('Al menos un número (0-9)', _hasNumber),
        _buildRule('Al menos un carácter especial (@\$!%*?&)', _hasSpecial),
      ],
    );
  }

  Widget _buildRule(String text, bool met) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2.0),
      child: Row(
        children: [
          Icon(
            met ? Icons.check_circle : Icons.cancel,
            color: met ? const Color(0xFF4CAF50) : const Color(0xFFE53935),
            size: 16,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 12,
                color: met ? const Color(0xFF4CAF50) : const Color(0xFFE53935),
                fontWeight: met ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
