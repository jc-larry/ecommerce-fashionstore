import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AnaliticaService, ChatbotResponse } from '../analitica.service';

interface ChatMessage {
  sender: 'USER' | 'BOT';
  text: string;
  time: string;
  suggested_products?: any[];
  suggested_actions?: string[];
}

@Component({
  selector: 'app-chatbot-widget',
  templateUrl: './chatbot-widget.component.html',
  styleUrls: ['./chatbot-widget.component.css']
})
export class ChatbotWidgetComponent implements OnInit {
  isOpen: boolean = false;
  inputMessage: string = '';
  sessionToken: string = '';
  messages: ChatMessage[] = [];
  sending: boolean = false;

  constructor(
    private analiticaService: AnaliticaService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.sessionToken = 'fs_' + Math.random().toString(36).substring(2, 11);
    // Mensaje de bienvenida inicial
    this.messages.push({
      sender: 'BOT',
      text: '¡Hola! 👋 Soy tu Asistente Virtual y Estilista de FashionStore. ¿En qué te puedo asesorar hoy?',
      time: this.getCurrentTime(),
      suggested_actions: ['¿Dónde están las sucursales?', 'Rastrear mi pedido', 'Prendas elegantes', 'Reservar probador']
    });
  }

  toggleChat(): void {
    this.isOpen = !this.isOpen;
  }

  getCurrentTime(): string {
    const now = new Date();
    return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
  }

  sendMessage(textToSend?: string): void {
    const text = textToSend || this.inputMessage.trim();
    if (!text || this.sending) return;

    this.messages.push({
      sender: 'USER',
      text: text,
      time: this.getCurrentTime()
    });
    this.inputMessage = '';
    this.sending = true;

    this.analiticaService.sendChatMessage(text, this.sessionToken).subscribe({
      next: (res: ChatbotResponse) => {
        this.sending = false;
        this.messages.push({
          sender: 'BOT',
          text: res.reply,
          time: this.getCurrentTime(),
          suggested_products: res.suggested_products,
          suggested_actions: res.suggested_actions
        });
      },
      error: () => {
        this.sending = false;
        this.messages.push({
          sender: 'BOT',
          text: 'Disculpa, tuve una breve interrupción de conexión. Por favor intenta de nuevo.',
          time: this.getCurrentTime()
        });
      }
    });
  }

  handleActionClick(action: string): void {
    if (action === 'Rastrear mi pedido' || action === 'Consultar Envíos') {
      this.router.navigate(['/tienda/rastreo']);
      this.isOpen = false;
    } else if (action === 'Reservar probador' || action === 'Ir a Reservas') {
      this.router.navigate(['/tienda/reservas']);
      this.isOpen = false;
    } else if (action === 'Vestidor Virtual') {
      this.router.navigate(['/tienda/vestidor']);
      this.isOpen = false;
    } else {
      this.sendMessage(action);
    }
  }

  viewProduct(prodId: number): void {
    this.router.navigate(['/tienda/producto', prodId]);
    this.isOpen = false;
  }
}
