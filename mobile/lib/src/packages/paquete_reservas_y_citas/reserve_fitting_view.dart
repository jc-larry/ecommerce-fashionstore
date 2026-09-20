import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';
import '../paquete_paquete_ventas_y_pagos/paypal_checkout.dart';
import 'reservations_view.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// Sucursal elegida para la cita, con su horario (viene de GET /branches).
class FittingBranch {
  final int id;
  final String name;
  final String city;
  final int stock;
  final String openingTime;
  final String closingTime;
  final String daysOpen;

  const FittingBranch({
    required this.id,
    required this.name,
    required this.city,
    required this.stock,
    this.openingTime = '09:00',
    this.closingTime = '21:00',
    this.daysOpen = 'Lunes a Sábado',
  });
}

/// [CU26] Agendar reserva de una prenda para probarla en la sucursal (bloqueo de stock 48 h).
///
/// Igual que la web: el cliente elige la sucursal con stock (CU12), fecha y hora dentro del
/// horario de atención y paga la seña del 50 % (Tarjeta, PayPal o QR). El backend aparta el
/// stock y, si la seña es por PayPal, verifica el cobro con la pasarela antes de reservar.
class ReserveFittingView extends StatefulWidget {
  final int variantId;
  final String productName;
  final String colorName;
  final String sizeName;
  final double unitPrice;
  final FittingBranch branch;

  const ReserveFittingView({
    super.key,
    required this.variantId,
    required this.productName,
    required this.colorName,
    required this.sizeName,
    required this.unitPrice,
    required this.branch,
  });

  @override
  State<ReserveFittingView> createState() => _ReserveFittingViewState();
}

class _ReserveFittingViewState extends State<ReserveFittingView> {
  late DateTime _date;
  late TimeOfDay _time;
  final _phoneCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  String _paymentMethod = 'TARJETA'; // TARJETA, PAYPAL, QR
  String _cardBrand = 'VISA';
  final _cardNumberCtrl = TextEditingController();
  final _cardCvvCtrl = TextEditingController();

  PayPalPaymentResult? _paypalResult;
  bool _saving = false;
  String? _error;

  /// La seña la calcula el backend como 50 % del precio base; aquí solo se muestra y se cobra.
  double get _deposit => (widget.unitPrice * 0.5 * 100).roundToDouble() / 100;
  double get _balance => widget.unitPrice - _deposit;

  @override
  void initState() {
    super.initState();
    _date = DateTime.now().add(const Duration(days: 1));
    _time = _parseTime(widget.branch.openingTime) ?? const TimeOfDay(hour: 15, minute: 0);
    AuthService.getUser().then((u) {
      final phone = u?['phone']?.toString();
      if (mounted && phone != null && phone.isNotEmpty) _phoneCtrl.text = phone;
    });
  }

  @override
  void dispose() {
    _phoneCtrl.dispose();
    _notesCtrl.dispose();
    _cardNumberCtrl.dispose();
    _cardCvvCtrl.dispose();
    super.dispose();
  }

  TimeOfDay? _parseTime(String hhmm) {
    final parts = hhmm.split(':');
    if (parts.length < 2) return null;
    final h = int.tryParse(parts[0]);
    final m = int.tryParse(parts[1]);
    if (h == null || m == null) return null;
    return TimeOfDay(hour: h, minute: m);
  }

  String _two(int v) => v.toString().padLeft(2, '0');
  String get _dateIso => '${_date.year}-${_two(_date.month)}-${_two(_date.day)}';
  String get _timeHhmm => '${_two(_time.hour)}:${_two(_time.minute)}';

  bool _withinOpeningHours(TimeOfDay t) {
    final open = _parseTime(widget.branch.openingTime);
    final close = _parseTime(widget.branch.closingTime);
    if (open == null || close == null) return true;
    final v = t.hour * 60 + t.minute;
    return v >= open.hour * 60 + open.minute && v <= close.hour * 60 + close.minute;
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(now.year, now.month, now.day).add(const Duration(days: 1)),
      lastDate: now.add(const Duration(days: 30)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: _time);
    if (picked == null) return;
    if (!_withinOpeningHours(picked)) {
      setState(() => _error =
          'Elige una hora dentro del horario de la sucursal (${widget.branch.openingTime} - ${widget.branch.closingTime}).');
      return;
    }
    setState(() {
      _time = picked;
      _error = null;
    });
  }

  Future<void> _confirm() async {
    if (!await AuthService.isLoggedIn()) {
      setState(() => _error = 'Inicia sesión con tu cuenta para reservar prendas.');
      return;
    }
    if (!_withinOpeningHours(_time)) {
      setState(() => _error = 'La hora está fuera del horario de atención de la sucursal.');
      return;
    }

    String paymentRef;
    final cleanCard = _cardNumberCtrl.text.replaceAll(RegExp(r'\D'), '');
    if (_paymentMethod == 'TARJETA') {
      if (cleanCard.length < 13) {
        setState(() => _error = 'Ingresa un número de tarjeta válido (mínimo 13 dígitos).');
        return;
      }
      if (_cardCvvCtrl.text.trim().length < 3) {
        setState(() => _error = 'Ingresa el código CVV (3 o 4 dígitos).');
        return;
      }
      paymentRef = 'TARJETA-$_cardBrand-****${cleanCard.substring(cleanCard.length - 4)}';
    } else if (_paymentMethod == 'QR') {
      paymentRef = 'QR-MOB-${DateTime.now().millisecondsSinceEpoch.toRadixString(36).toUpperCase()}';
    } else {
      paymentRef = '';
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    // Seña por PayPal: se cobra primero; el backend la verifica antes de apartar el stock.
    if (_paymentMethod == 'PAYPAL') {
      if (_paypalResult == null) {
        if (!mounted) return;
        try {
          final result = await PayPalCheckout.pay(
            context,
            amountBob: _deposit,
            description: 'Seña 50% Reserva Probador FashionStore (1 prenda)',
          );
          if (!mounted) return;
          if (result == null) {
            setState(() {
              _saving = false;
              _error = 'Cancelaste el pago en PayPal. No se realizó ningún cobro.';
            });
            return;
          }
          _paypalResult = result;
        } on PayPalException catch (e) {
          if (!mounted) return;
          setState(() {
            _saving = false;
            _error = e.message;
          });
          return;
        }
      }
      paymentRef = 'PAYPAL:${_paypalResult!.orderId}';
    }

    final phone = _phoneCtrl.text.trim();
    final notes = _notesCtrl.text.trim();
    try {
      final token = await AuthService.getToken();
      final res = await http.post(
        Uri.parse('${AuthService.apiBaseUrl}/reservations'),
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
        body: jsonEncode({
          'branch_id': widget.branch.id,
          'items': [
            {'variant_id': widget.variantId, 'quantity': 1, if (notes.isNotEmpty) 'notes': notes},
          ],
          'appointment_date': _dateIso,
          'appointment_time': _timeHhmm,
          // Igual que la web: la cita define la fecha de reserva (regla de cancelación de 24 h).
          'reserved_at': '${_dateIso}T$_timeHhmm:00',
          'notes': 'Reserva para probador (app móvil). Tel: ${phone.isEmpty ? 'S/N' : phone}. $notes'.trim(),
          'payment_method': _paymentMethod,
          'payment_reference': paymentRef,
        }),
      ).timeout(const Duration(seconds: 20));

      if (!mounted) return;
      if (res.statusCode == 200 || res.statusCode == 201) {
        final data = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
        await _showSuccess(data);
        return;
      }
      String msg = 'No se pudo crear la reserva en esta sucursal.';
      try {
        final d = jsonDecode(utf8.decode(res.bodyBytes))['detail'];
        if (d is String && d.isNotEmpty) msg = d;
      } catch (_) {}
      setState(() {
        _saving = false;
        _error = msg;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'No se pudo conectar con el servidor. Intenta nuevamente.';
      });
    }
  }

  Future<void> _showSuccess(Map<String, dynamic> data) async {
    final nav = Navigator.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Row(children: [
          Icon(Icons.check_circle, color: Colors.green),
          SizedBox(width: 8),
          Text('¡Reserva confirmada!'),
        ]),
        content: Text(
          'Código: ${data['reservation_code']}\n'
          'Sucursal: ${widget.branch.name}\n'
          'Cita: $_dateIso a las $_timeHhmm\n'
          'Seña pagada: Bs. ${_deposit.toStringAsFixed(2)}\n\n'
          'Presenta este código en la sucursal. La prenda queda apartada por 48 horas.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Entendido')),
        ],
      ),
    );
    nav.pushReplacement(MaterialPageRoute(builder: (_) => const ReservationsView()));
  }

  @override
  Widget build(BuildContext context) {
    final b = widget.branch;
    return Scaffold(
      backgroundColor: const Color(0xFFFCFBFA),
      appBar: AppBar(title: const Text('Reservar para probar', style: TextStyle(fontWeight: FontWeight.bold))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_error != null)
            Container(
              margin: const EdgeInsets.only(bottom: 14),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.red.shade200),
              ),
              child: Text(_error!, style: TextStyle(color: Colors.red.shade800, fontSize: 13)),
            ),
          _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(widget.productName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink)),
            const SizedBox(height: 4),
            Text('Color: ${widget.colorName} · Talla: ${widget.sizeName}', style: const TextStyle(color: _muted)),
            const Divider(height: 20),
            Row(children: [
              const Icon(Icons.storefront_outlined, size: 18, color: _brand),
              const SizedBox(width: 6),
              Expanded(child: Text('${b.name} (${b.city})', style: const TextStyle(fontWeight: FontWeight.w600))),
              Text('${b.stock} en stock', style: TextStyle(fontSize: 12, color: Colors.green.shade700)),
            ]),
            const SizedBox(height: 4),
            Text('Horario: ${b.daysOpen}, ${b.openingTime} - ${b.closingTime}', style: const TextStyle(fontSize: 12, color: _muted)),
          ])),
          const SizedBox(height: 14),
          _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Fecha y hora de la cita', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _pickDate,
                  icon: const Icon(Icons.event, size: 18),
                  label: Text('${_two(_date.day)}/${_two(_date.month)}/${_date.year}'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _pickTime,
                  icon: const Icon(Icons.schedule, size: 18),
                  label: Text(_timeHhmm),
                ),
              ),
            ]),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Teléfono de contacto', isDense: true),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _notesCtrl,
              decoration: const InputDecoration(labelText: 'Notas para la tienda (opcional)', isDense: true),
            ),
          ])),
          const SizedBox(height: 14),
          _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Seña del 50 %', style: TextStyle(fontWeight: FontWeight.bold, color: _ink)),
            const SizedBox(height: 6),
            _row('Precio de la prenda', 'Bs. ${widget.unitPrice.toStringAsFixed(2)}'),
            _row('Seña a pagar ahora', 'Bs. ${_deposit.toStringAsFixed(2)}', bold: true),
            _row('Saldo a pagar en tienda', 'Bs. ${_balance.toStringAsFixed(2)}'),
            const SizedBox(height: 12),
            Wrap(spacing: 8, children: [
              _methodChip('TARJETA', 'Tarjeta'),
              _methodChip('PAYPAL', 'PayPal'),
              _methodChip('QR', 'QR'),
            ]),
            const SizedBox(height: 12),
            if (_paymentMethod == 'TARJETA') ...[
              DropdownButtonFormField<String>(
                initialValue: _cardBrand,
                decoration: const InputDecoration(isDense: true, labelText: 'Marca'),
                items: const [
                  DropdownMenuItem(value: 'VISA', child: Text('VISA')),
                  DropdownMenuItem(value: 'MASTERCARD', child: Text('Mastercard')),
                ],
                onChanged: (v) => setState(() => _cardBrand = v ?? 'VISA'),
              ),
              const SizedBox(height: 10),
              Row(children: [
                Expanded(
                  flex: 3,
                  child: TextField(
                    controller: _cardNumberCtrl,
                    keyboardType: TextInputType.number,
                    maxLength: 19,
                    decoration: const InputDecoration(labelText: 'Número de tarjeta', counterText: '', isDense: true),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _cardCvvCtrl,
                    keyboardType: TextInputType.number,
                    obscureText: true,
                    maxLength: 4,
                    decoration: const InputDecoration(labelText: 'CVV', counterText: '', isDense: true),
                  ),
                ),
              ]),
            ],
            if (_paymentMethod == 'PAYPAL')
              Text(
                _paypalResult != null
                    ? 'Seña autorizada por PayPal. Ref: ${_paypalResult!.gatewayReference}'
                    : 'Al confirmar se abrirá PayPal para que apruebes la seña.',
                style: TextStyle(fontSize: 12, color: _paypalResult != null ? Colors.green.shade800 : Colors.blue.shade900),
              ),
            if (_paymentMethod == 'QR')
              const Text(
                'Paga la seña escaneando el QR interoperable con tu app bancaria.',
                style: TextStyle(fontSize: 12, color: Colors.teal),
              ),
          ])),
          const SizedBox(height: 20),
          SizedBox(
            height: 50,
            child: ElevatedButton.icon(
              onPressed: _saving ? null : _confirm,
              icon: _saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.lock_outline),
              label: Text(_saving ? 'Procesando…' : 'Pagar seña y reservar (Bs. ${_deposit.toStringAsFixed(2)})'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _card(Widget child) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE5DFDC)),
        ),
        child: child,
      );

  Widget _row(String label, String value, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(label, style: const TextStyle(fontSize: 13, color: _muted)),
          Text(value, style: TextStyle(fontSize: 13, fontWeight: bold ? FontWeight.bold : FontWeight.w500, color: bold ? _brand : _ink)),
        ]),
      );

  Widget _methodChip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _paymentMethod == value,
        selectedColor: const Color(0xFFF6E3DD),
        onSelected: (_) {
          // Una seña ya cobrada por PayPal no se pierde al cambiar de medio.
          if (_paypalResult != null && value != 'PAYPAL') return;
          setState(() => _paymentMethod = value);
        },
      );
}
