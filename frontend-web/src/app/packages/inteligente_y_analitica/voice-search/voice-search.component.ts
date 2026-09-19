import { Component, EventEmitter, Output } from '@angular/core';
import { AnaliticaService, VoiceNLPResult } from '../analitica.service';

@Component({
  selector: 'app-voice-search',
  templateUrl: './voice-search.component.html',
  styleUrls: ['./voice-search.component.css']
})
export class VoiceSearchComponent {
  @Output() searchResult = new EventEmitter<VoiceNLPResult>();

  isListening: boolean = false;
  recognizedText: string = '';
  speechSupported: boolean = false;
  private recognition: any = null;

  constructor(private analiticaService: AnaliticaService) {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.speechSupported = true;
      this.recognition = new SpeechRecognition();
      this.recognition.lang = 'es-ES';
      this.recognition.interimResults = false;
      this.recognition.maxAlternatives = 1;

      this.recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        this.recognizedText = transcript;
        this.isListening = false;
        this.processWithNLP(transcript);
      };

      this.recognition.onerror = () => {
        this.isListening = false;
      };

      this.recognition.onend = () => {
        this.isListening = false;
      };
    }
  }

  toggleListening(): void {
    if (!this.speechSupported) {
      // Fallback para navegadores sin Speech API: solicitar texto interactivo
      const promptText = prompt('Ingresa tu consulta en lenguaje natural (ej. "Vestido rojo de menos de 200 bolivianos"):');
      if (promptText) this.processWithNLP(promptText);
      return;
    }

    if (this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    } else {
      this.recognizedText = 'Escuchando...';
      this.isListening = true;
      try {
        this.recognition.start();
      } catch (e) {
        this.isListening = false;
      }
    }
  }

  processWithNLP(text: string): void {
    this.analiticaService.searchByVoiceNLP(text).subscribe({
      next: (res) => {
        this.searchResult.emit(res);
      },
      error: () => {}
    });
  }
}
