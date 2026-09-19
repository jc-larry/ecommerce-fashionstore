import { Component, OnInit } from '@angular/core';
import { AnaliticaService, KardexItem, TopSellingItem } from '../analitica.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

@Component({
  selector: 'app-manager-reports',
  templateUrl: './manager-reports.component.html',
  styleUrls: ['./manager-reports.component.css']
})
export class ManagerReportsComponent implements OnInit {
  activeTab: 'kardex' | 'top' | 'voice' = 'kardex';

  // Kardex
  kardexRecords: KardexItem[] = [];
  branches: any[] = [];
  selectedBranchId?: number;
  loadingKardex: boolean = false;

  // Top Vendidos
  topProducts: TopSellingItem[] = [];
  loadingTop: boolean = false;

  // Resumen Ejecutivo / Voz
  voiceSummary: string = '';
  voiceRevenue: number = 0;
  voiceOrders: number = 0;
  voiceReservations: number = 0;
  voiceShipments: number = 0;
  isSpeaking: boolean = false;
  loadingVoice: boolean = false;

  constructor(
    private analiticaService: AnaliticaService,
    private catalogoService: CatalogoService
  ) {}

  ngOnInit(): void {
    this.loadBranches();
    this.loadKardex();
    this.loadTopSelling();
    this.loadVoiceSummary();
  }

  loadBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (b: any[]) => (this.branches = b),
      error: () => {}
    });
  }

  loadKardex(): void {
    this.loadingKardex = true;
    this.analiticaService.getKardex(this.selectedBranchId).subscribe({
      next: (data) => {
        this.kardexRecords = data;
        this.loadingKardex = false;
      },
      error: () => {
        this.loadingKardex = false;
      }
    });
  }

  downloadKardexCsv(): void {
    const url = this.analiticaService.exportKardexCsvUrl(this.selectedBranchId);
    window.open(url, '_blank');
  }

  loadTopSelling(): void {
    this.loadingTop = true;
    this.analiticaService.getTopSelling(10).subscribe({
      next: (data) => {
        this.topProducts = data;
        this.loadingTop = false;
      },
      error: () => {
        this.loadingTop = false;
      }
    });
  }

  loadVoiceSummary(): void {
    this.loadingVoice = true;
    this.analiticaService.getExecutiveSummaryVoice().subscribe({
      next: (res) => {
        this.voiceSummary = res.summary_text;
        this.voiceRevenue = res.total_revenue;
        this.voiceOrders = res.total_orders;
        this.voiceReservations = res.active_reservations;
        this.voiceShipments = res.pending_shipments;
        this.loadingVoice = false;
      },
      error: () => {
        this.loadingVoice = false;
      }
    });
  }

  speakSummary(): void {
    if (!('speechSynthesis' in window)) {
      alert('Tu navegador no soporta síntesis de voz en tiempo real.');
      return;
    }

    if (this.isSpeaking) {
      window.speechSynthesis.cancel();
      this.isSpeaking = false;
      return;
    }

    const utterance = new SpeechSynthesisUtterance(this.voiceSummary);
    utterance.lang = 'es-ES';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onend = () => {
      this.isSpeaking = false;
    };
    utterance.onerror = () => {
      this.isSpeaking = false;
    };

    this.isSpeaking = true;
    window.speechSynthesis.speak(utterance);
  }

  getMovementBadge(type: string): string {
    switch (type) {
      case 'INGRESO': return 'bg-success';
      case 'VENTA': return 'bg-primary';
      case 'RESERVA': return 'bg-warning text-dark';
      case 'RESERVA_LIBERACION': return 'bg-info text-dark';
      case 'AJUSTE': return 'bg-secondary';
      default: return 'bg-light text-dark';
    }
  }
}
