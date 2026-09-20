import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:webview_flutter/webview_flutter.dart';
import '../paquete_seguridad_usuarios/auth_service.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);
const _paypalBlue = Color(0xFF003087);

/// Comprobante de un pago capturado por PayPal (real o simulado).
class PayPalPaymentResult {
  final String orderId;
  final String gatewayReference;
  final String? payerId;
  final String? payerEmail;
  final bool simulated;

  const PayPalPaymentResult({
    required this.orderId,
    required this.gatewayReference,
    this.payerId,
    this.payerEmail,
    required this.simulated,
  });
}

/// Error de la pasarela con un mensaje apto para mostrar al cliente.
class PayPalException implements Exception {
  final String message;
  const PayPalException(this.message);

  @override
  String toString() => message;
}

/// [CU18 / CU26] Pasarela PayPal en la app móvil (mismo backend que la web).
///
/// Flujo real (credenciales sandbox/live en el backend):
///   1. POST /payments/paypal/create-order → orden REST v2 + `approve_url`.
///   2. La ventana oficial de PayPal se abre dentro de la app; el cliente inicia sesión
///      con su cuenta (sandbox: cuenta "Personal" de pruebas) y aprueba.
///   3. PayPal redirige a `.../checkout/success` → la app lo detecta y pide al backend
///      POST /payments/paypal/capture-order. El Secret nunca llega al teléfono.
/// Sin credenciales en el backend, la orden es simulada y se avisa que no hay cobro.
class PayPalCheckout {
  static const Duration _timeout = Duration(seconds: 20);
  static const double defaultExchangeRate = 6.96;

  static Future<Map<String, String>> _headers() async {
    final token = await AuthService.getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  static String _detail(http.Response r, String fallback) {
    try {
      final body = jsonDecode(utf8.decode(r.bodyBytes));
      final d = body is Map ? body['detail'] : null;
      if (d is String && d.isNotEmpty) return d;
    } catch (_) {}
    return fallback;
  }

  /// Tipo de cambio Bs → USD que usa el backend (para mostrar el monto en dólares).
  static Future<double> exchangeRate() async {
    try {
      final r = await http
          .get(Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/config'))
          .timeout(_timeout);
      if (r.statusCode == 200) {
        final rate = (jsonDecode(r.body)['exchange_rate_bob_usd'] as num?)?.toDouble();
        if (rate != null && rate > 0) return rate;
      }
    } catch (_) {}
    return defaultExchangeRate;
  }

  /// Ejecuta el cobro completo por PayPal. Devuelve null si el cliente cancela.
  /// Lanza [PayPalException] si PayPal o el backend rechazan el pago.
  static Future<PayPalPaymentResult?> pay(
    BuildContext context, {
    required double amountBob,
    required String description,
  }) async {
    final navigator = Navigator.of(context);

    // 1. Crear la orden en el backend (que a su vez la crea en PayPal).
    final Map<String, dynamic> order;
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/create-order'),
            headers: await _headers(),
            body: jsonEncode({'amount_bob': double.parse(amountBob.toStringAsFixed(2)), 'description': description}),
          )
          .timeout(_timeout);
      if (r.statusCode != 200) {
        throw PayPalException(_detail(r, 'No se pudo iniciar el pago con PayPal.'));
      }
      order = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    } on PayPalException {
      rethrow;
    } catch (_) {
      throw const PayPalException('No se pudo conectar con el servidor para iniciar el pago.');
    }

    final orderId = order['id']?.toString() ?? '';
    final simulated = order['simulated'] == true;
    final approveUrl = order['approve_url']?.toString();
    final amountUsd = (order['amount_usd'] as num?)?.toDouble() ?? 0;

    // 2. Aprobación del comprador.
    bool? approved;
    if (simulated) {
      approved = await navigator.push<bool>(MaterialPageRoute(
        builder: (_) => _SimulatedApprovalPage(amountBob: amountBob, amountUsd: amountUsd),
      ));
    } else {
      if (approveUrl == null || approveUrl.isEmpty) {
        throw const PayPalException('PayPal no devolvió el enlace de aprobación.');
      }
      approved = await navigator.push<bool>(MaterialPageRoute(
        builder: (_) => PayPalApprovalPage(approveUrl: approveUrl, amountUsd: amountUsd),
      ));
    }
    if (approved != true) return null;

    // 3. Captura de los fondos (lado servidor).
    try {
      final r = await http
          .post(
            Uri.parse('${AuthService.apiBaseUrl}/payments/paypal/capture-order'),
            headers: await _headers(),
            body: jsonEncode({'paypal_order_id': orderId}),
          )
          .timeout(_timeout);
      if (r.statusCode != 200) {
        throw PayPalException(_detail(r, 'PayPal no confirmó el pago. No se realizó ningún cobro.'));
      }
      final cap = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
      final payer = (cap['payer'] as Map?) ?? const {};
      return PayPalPaymentResult(
        orderId: cap['id']?.toString() ?? orderId,
        gatewayReference: cap['gateway_reference']?.toString() ?? 'PAYPAL:$orderId',
        payerId: payer['payer_id']?.toString(),
        payerEmail: payer['email_address']?.toString(),
        simulated: cap['simulated'] == true,
      );
    } on PayPalException {
      rethrow;
    } catch (_) {
      throw const PayPalException('No se pudo confirmar el pago con el servidor.');
    }
  }
}

/// Ventana oficial de PayPal (sandbox o live) embebida en la app.
/// Devuelve true cuando PayPal redirige al return_url (pago aprobado) y false si se cancela.
class PayPalApprovalPage extends StatefulWidget {
  final String approveUrl;
  final double amountUsd;
  const PayPalApprovalPage({super.key, required this.approveUrl, required this.amountUsd});

  @override
  State<PayPalApprovalPage> createState() => _PayPalApprovalPageState();
}

class _PayPalApprovalPageState extends State<PayPalApprovalPage> {
  late final WebViewController _controller;
  int _progress = 0;
  bool _finished = false;

  /// El backend configura return_url = .../checkout/success y cancel_url = .../checkout/cancel.
  bool _handleUrl(String url) {
    if (_finished) return true;
    if (url.contains('/checkout/success')) {
      _finish(true);
      return true;
    }
    if (url.contains('/checkout/cancel')) {
      _finish(false);
      return true;
    }
    return false;
  }

  void _finish(bool approved) {
    _finished = true;
    if (mounted) Navigator.of(context).pop(approved);
  }

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onNavigationRequest: (req) =>
            _handleUrl(req.url) ? NavigationDecision.prevent : NavigationDecision.navigate,
        // Respaldo: algunas redirecciones del servidor no pasan por onNavigationRequest.
        onPageStarted: _handleUrl,
        onProgress: (p) {
          if (mounted) setState(() => _progress = p);
        },
      ))
      ..loadRequest(Uri.parse(widget.approveUrl));
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop && !_finished) _finish(false);
      },
      child: Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.white,
          foregroundColor: _paypalBlue,
          leading: IconButton(icon: const Icon(Icons.close), onPressed: () => _finish(false)),
          title: Text(
            'PayPal · \$${widget.amountUsd.toStringAsFixed(2)} USD',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          bottom: _progress < 100
              ? PreferredSize(
                  preferredSize: const Size.fromHeight(3),
                  child: LinearProgressIndicator(value: _progress / 100, minHeight: 3, color: _paypalBlue),
                )
              : null,
        ),
        body: WebViewWidget(controller: _controller),
      ),
    );
  }
}

/// Aprobación simulada: solo cuando el backend no tiene credenciales de PayPal.
/// Lo dice explícitamente para no confundirla con un cobro real.
class _SimulatedApprovalPage extends StatelessWidget {
  final double amountBob;
  final double amountUsd;
  const _SimulatedApprovalPage({required this.amountBob, required this.amountUsd});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(
        title: const Text('PayPal (simulación)', style: TextStyle(fontWeight: FontWeight.bold)),
        leading: IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(context, false)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: const Text(
                'Modo simulación: el servidor no tiene credenciales de PayPal configuradas. '
                'No se contacta a PayPal ni se realiza ningún cobro.',
                style: TextStyle(fontSize: 13, color: _ink),
              ),
            ),
            const SizedBox(height: 24),
            const Text('Pagar a', style: TextStyle(color: _muted, fontSize: 12)),
            const Text('FashionStore Bolivia', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink)),
            const SizedBox(height: 16),
            Text('\$${amountUsd.toStringAsFixed(2)} USD',
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: _paypalBlue)),
            Text('≈ Bs. ${amountBob.toStringAsFixed(2)}', style: const TextStyle(color: _muted)),
            const Spacer(),
            SizedBox(
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFFC439),
                  foregroundColor: _paypalBlue,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(25)),
                ),
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Aprobar pago simulado', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar', style: TextStyle(color: _brand)),
            ),
          ],
        ),
      ),
    );
  }
}
