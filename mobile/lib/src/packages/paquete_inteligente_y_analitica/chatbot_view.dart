import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../paquete_seguridad_usuarios/auth_service.dart';

const _brand = Color(0xFFC66F5C);
const _ink = Color(0xFF2B1F1D);
const _muted = Color(0xFF706361);

/// [CU33] Asistente Virtual Inteligente y Consejero de Estilo (App Móvil).
/// Permite al cliente conversar en lenguaje natural con el bot de IA,
/// solicitar recomendaciones de outfits, consejos de combinación y productos sugeridos.
class ChatbotView extends StatefulWidget {
  const ChatbotView({super.key});

  @override
  State<ChatbotView> createState() => _ChatbotViewState();
}

class _ChatMessage {
  final String text;
  final bool isUser;
  final List<dynamic>? suggestedProducts;
  final List<String>? suggestedActions;
  final DateTime timestamp;

  _ChatMessage({
    required this.text,
    required this.isUser,
    this.suggestedProducts,
    this.suggestedActions,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

class _ChatbotViewState extends State<ChatbotView> {
  final TextEditingController _msgCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _isSending = false;
  String? _sessionToken;

  final List<String> _quickPrompts = [
    '¿Qué prendas de lino tienen para clima cálido?',
    'Recomiéndame un outfit elegante para la noche',
    '¿Cómo combinar una blusa blanca?',
    '¿Dónde puedo recoger mis reservas?',
  ];

  @override
  void initState() {
    super.initState();
    _messages.add(
      _ChatMessage(
        text: '¡Hola! Soy tu asistente de moda y estilo de FashionStore 👗✨. ¿En qué ocasión o prenda estás pensando hoy?',
        isUser: false,
        suggestedActions: [
          'Ver vestidos de fiesta',
          'Rastrear un paquete',
          'Consultar horarios de sucursales',
        ],
      ),
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage(String text) async {
    final query = text.trim();
    if (query.isEmpty) return;

    _msgCtrl.clear();
    setState(() {
      _messages.add(_ChatMessage(text: query, isUser: true));
      _isSending = true;
    });
    _scrollToBottom();

    try {
      final token = await AuthService.getToken();
      final url = Uri.parse('${AuthService.apiBaseUrl}/analytics/chatbot/message');
      final res = await http.post(
        url,
        headers: {
          if (token != null) 'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'message': query,
          'session_token': _sessionToken,
        }),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        _sessionToken = data['session_token'];
        final reply = data['reply'] ?? 'He recibido tu consulta.';
        final products = data['suggested_products'] as List?;
        final actions = (data['suggested_actions'] as List?)?.map((e) => e.toString()).toList();

        setState(() {
          _messages.add(_ChatMessage(
            text: reply,
            isUser: false,
            suggestedProducts: products,
            suggestedActions: actions,
          ));
          _isSending = false;
        });
      } else {
        setState(() {
          _messages.add(_ChatMessage(
            text: 'Disculpa, ocurrió un inconveniente al procesar tu consulta. Intenta de nuevo en unos momentos.',
            isUser: false,
          ));
          _isSending = false;
        });
      }
    } catch (e) {
      setState(() {
        _messages.add(_ChatMessage(
          text: 'No fue posible conectar con el asistente de IA. Revisa tu conexión a internet.',
          isUser: false,
        ));
        _isSending = false;
      });
    }

    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F6F4),
      appBar: AppBar(
        title: const Row(
          children: [
            CircleAvatar(
              radius: 16,
              backgroundColor: Color(0xFFF6E3DD),
              child: Icon(Icons.auto_awesome, size: 18, color: _brand),
            ),
            SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Asistente FashionStore', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: _ink)),
                Text('Consejero IA en tiempo real', style: TextStyle(fontSize: 11, color: Colors.green, fontWeight: FontWeight.w500)),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // Chips de preguntas sugeridas
          if (_messages.length <= 2)
            SizedBox(
              height: 48,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                scrollDirection: Axis.horizontal,
                itemCount: _quickPrompts.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  return ActionChip(
                    label: Text(_quickPrompts[i], style: const TextStyle(fontSize: 12, color: _ink)),
                    backgroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFFECE6E2)),
                    onPressed: () => _sendMessage(_quickPrompts[i]),
                  );
                },
              ),
            ),

          // Lista de mensajes de chat
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final m = _messages[index];
                return _buildMessageBubble(m);
              },
            ),
          ),

          if (_isSending)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              alignment: Alignment.centerLeft,
              child: const Row(
                children: [
                  SizedBox(width: 14, height: 14, child: CircularProgressIndicator(color: _brand, strokeWidth: 2)),
                  SizedBox(width: 8),
                  Text('FashionStore IA está escribiendo...', style: TextStyle(fontSize: 12, color: _muted, fontStyle: FontStyle.italic)),
                ],
              ),
            ),

          // Input de envío
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(top: BorderSide(color: Color(0xFFECE6E2))),
            ),
            child: SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _msgCtrl,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: const InputDecoration(
                        hintText: 'Pregúntame sobre tallas, vestidos o estilos...',
                        hintStyle: TextStyle(fontSize: 13, color: _muted),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                      ),
                      onSubmitted: _sendMessage,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send_rounded, color: _brand),
                    onPressed: () => _sendMessage(_msgCtrl.text),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(_ChatMessage m) {
    return Align(
      alignment: m.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        child: Column(
          crossAxisAlignment: m.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: m.isUser ? _brand : Colors.white,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(m.isUser ? 16 : 4),
                  bottomRight: Radius.circular(m.isUser ? 4 : 16),
                ),
                border: m.isUser ? null : Border.all(color: const Color(0xFFECE6E2)),
                boxShadow: [
                  BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 6, offset: const Offset(0, 2)),
                ],
              ),
              child: Text(
                m.text,
                style: TextStyle(
                  color: m.isUser ? Colors.white : _ink,
                  fontSize: 13.5,
                  height: 1.35,
                ),
              ),
            ),

            // Acciones sugeridas
            if (m.suggestedActions != null && m.suggestedActions!.isNotEmpty) ...[
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: m.suggestedActions!.map((act) {
                  return InkWell(
                    onTap: () => _sendMessage(act),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6E3DD),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(act, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: _brand)),
                    ),
                  );
                }).toList(),
              ),
            ],

            // Prendas sugeridas por la IA
            if (m.suggestedProducts != null && m.suggestedProducts!.isNotEmpty) ...[
              const SizedBox(height: 8),
              SizedBox(
                height: 110,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: m.suggestedProducts!.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, i) {
                    final p = m.suggestedProducts![i];
                    return Container(
                      width: 140,
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFECE6E2)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(p['name'] ?? 'Prenda', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _ink)),
                          const SizedBox(height: 2),
                          Text('Bs. ${p['base_price'] ?? '0'}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _brand)),
                          const Spacer(),
                          Text(p['category_name'] ?? 'Moda', style: const TextStyle(fontSize: 10, color: _muted)),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
