import 'package:flutter/material.dart';
import 'auth_service.dart';

/// [CU03] Recuperación de credenciales — un solo paso en la app.
/// El usuario pide el enlace; la pantalla de "nueva contraseña" se abre
/// únicamente al tocar el enlace del correo (página web), nunca dentro de la app,
/// y jamás se pide un token a mano (es más seguro: un enlace solo funciona desde
/// el buzón del propio usuario).
class RecoverView extends StatefulWidget {
  const RecoverView({super.key});

  @override
  State<RecoverView> createState() => _RecoverViewState();
}

class _RecoverViewState extends State<RecoverView> {
  final _emailController = TextEditingController();
  bool _loading = false;
  bool _sent = false;
  String? _devResetLink; // solo en modo desarrollo (backend sin SMTP)

  void _onRequestLink() async {
    final email = _emailController.text.trim();

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
      result = await AuthService.recover(email);
    } catch (e) {
      result = {'success': false, 'message': 'Error inesperado: $e'};
    }

    if (!mounted) return;
    setState(() {
      _loading = false;
      // Mensaje neutro por seguridad: no se revela si el correo existe.
      _sent = result['success'] == true;
      _devResetLink = result['devResetLink'] as String?;
    });

    if (result['success'] != true) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message']?.toString() ?? 'No se pudo procesar la solicitud'),
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
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 64,
                height: 64,
                decoration: const BoxDecoration(
                  color: Color(0x1AC66F5C),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _sent ? Icons.mark_email_read_outlined : Icons.key,
                  color: const Color(0xFFC66F5C),
                  size: 32,
                ),
              ),
              const SizedBox(height: 24),

              Text(
                _sent ? 'Revisa tu correo' : 'Recuperar contraseña',
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2B1F1D),
                ),
              ),
              const SizedBox(height: 8),

              if (_sent) ...[
                Text(
                  'Si ${_emailController.text.trim()} está registrado, te enviamos un enlace '
                  'para crear tu nueva contraseña. Ábrelo desde tu bandeja de entrada '
                  '(revisa también spam).',
                  style: const TextStyle(fontSize: 14, color: Color(0xFF706361), height: 1.5),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF3E0),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFFF9800)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.timer, color: Color(0xFFFF9800), size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'El enlace vence en 5 minutos.',
                          style: TextStyle(fontSize: 12, color: Color(0xFFE65100), fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
                if (_devResetLink != null && _devResetLink!.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF8E1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFFFB300)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Modo desarrollo (sin SMTP)',
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFFE65100))),
                        const SizedBox(height: 4),
                        SelectableText(_devResetLink!,
                            style: const TextStyle(fontSize: 11, color: Color(0xFF5D4037))),
                        const Text('Ábrelo en el navegador para definir la nueva contraseña.',
                            style: TextStyle(fontSize: 11, color: Color(0xFF8C7E7B))),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFC66F5C),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      elevation: 0,
                    ),
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Volver al inicio de sesión',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  ),
                ),
              ] else ...[
                const Text(
                  'Ingresa tu correo registrado y te enviaremos un enlace para crear una '
                  'nueva contraseña.',
                  style: TextStyle(fontSize: 14, color: Color(0xFF706361), height: 1.5),
                ),
                const SizedBox(height: 32),
                const Text(
                  'Correo electrónico',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF2B1F1D)),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: InputDecoration(
                    hintText: 'ejemplo@correo.com',
                    prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF8C7E7B)),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFC66F5C),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      elevation: 0,
                    ),
                    icon: const Icon(Icons.send_outlined, size: 18),
                    label: _loading
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('Enviar enlace de recuperación', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                    onPressed: _loading ? null : _onRequestLink,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
