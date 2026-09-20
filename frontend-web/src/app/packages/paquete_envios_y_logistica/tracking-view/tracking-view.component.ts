import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { LogisticaService, Shipment } from '../logistica.service';

@Component({
  selector: 'app-tracking-view',
  templateUrl: './tracking-view.component.html',
  styleUrls: ['./tracking-view.component.css']
})
export class TrackingViewComponent implements OnInit {
  trackingCode: string = '';
  shipment: Shipment | null = null;
  loading: boolean = false;
  errorMsg: string = '';

  constructor(
    private route: ActivatedRoute,
    private logisticaService: LogisticaService
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe(params => {
      if (params['code']) {
        this.trackingCode = params['code'];
        this.searchTracking();
      }
    });
  }

  searchTracking(): void {
    if (!this.trackingCode.trim()) return;
    this.loading = true;
    this.errorMsg = '';
    this.shipment = null;

    this.logisticaService.trackByCode(this.trackingCode.trim()).subscribe({
      next: (res) => {
        this.shipment = res;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err.error?.detail || `No se encontró ningún paquete con el código "${this.trackingCode}".`;
      }
    });
  }

  getStatusBadge(status: string): string {
    switch (status) {
      case 'PENDING_DISPATCH': return 'bg-warning text-dark';
      case 'DISPATCHED': return 'bg-info text-dark';
      case 'IN_TRANSIT': return 'bg-primary';
      case 'OUT_FOR_DELIVERY': return 'bg-purple text-white';
      case 'DELIVERED': return 'bg-success';
      default: return 'bg-secondary';
    }
  }

  getStatusText(status: string): string {
    switch (status) {
      case 'PENDING_DISPATCH': return 'En preparación en almacén';
      case 'DISPATCHED': return 'Despachado con el transportista';
      case 'IN_TRANSIT': return 'En tránsito';
      case 'OUT_FOR_DELIVERY': return '¡En reparto hoy hacia tu domicilio!';
      case 'DELIVERED': return 'Entregado con éxito';
      default: return status;
    }
  }
}
