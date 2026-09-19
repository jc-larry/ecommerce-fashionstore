import { Component, OnInit } from '@angular/core';
import { LogisticaService, Shipment, DeliveryZone } from '../logistica.service';

@Component({
  selector: 'app-shipments',
  templateUrl: './shipments.component.html',
  styleUrls: ['./shipments.component.css']
})
export class ShipmentsComponent implements OnInit {
  shipments: Shipment[] = [];
  zones: DeliveryZone[] = [];
  statusFilter: string = '';
  loading: boolean = false;
  successMsg: string = '';
  errorMsg: string = '';

  // Modal Nuevo Despacho (CU29)
  showCreateModal: boolean = false;
  newOrderId: number = 1;
  newZoneId?: number;
  newCarrierName: string = 'Moto Express Santa Cruz';
  newCarrierPhone: string = '70012345';
  newAddress: string = '';
  newRecipient: string = '';
  newPhone: string = '';
  newCost: number = 15;
  newNotes: string = '';
  createProcessing: boolean = false;

  // Modal Actualizar Hito
  selectedShipmentForEvent: Shipment | null = null;
  newEventStatus: string = 'IN_TRANSIT';
  newEventLocation: string = 'Centro de Distribución';
  newEventDescription: string = 'Paquete clasificado y listo para entrega.';
  eventProcessing: boolean = false;

  // Drawer Detalle
  viewingShipment: Shipment | null = null;

  constructor(private logisticaService: LogisticaService) {}

  ngOnInit(): void {
    this.loadShipments();
    this.loadZones();
  }

  loadZones(): void {
    this.logisticaService.getZones(true).subscribe({
      next: (z) => (this.zones = z),
      error: () => {}
    });
  }

  loadShipments(): void {
    this.loading = true;
    this.errorMsg = '';
    this.logisticaService.getShipments(this.statusFilter).subscribe({
      next: (data) => {
        this.shipments = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cargar los envíos.';
        this.loading = false;
      }
    });
  }

  openCreateModal(): void {
    this.showCreateModal = true;
  }

  closeCreateModal(): void {
    this.showCreateModal = false;
  }

  onZoneSelected(): void {
    if (this.newZoneId) {
      const z = this.zones.find(x => x.id === +this.newZoneId!);
      if (z) this.newCost = z.base_rate;
    }
  }

  executeCreateShipment(): void {
    if (!this.newOrderId || !this.newAddress || !this.newRecipient || !this.newPhone) {
      this.errorMsg = 'Por favor completa todos los campos requeridos del despacho.';
      return;
    }
    this.createProcessing = true;
    this.logisticaService.createShipment({
      order_id: +this.newOrderId,
      zone_id: this.newZoneId ? +this.newZoneId : undefined,
      carrier_name: this.newCarrierName,
      carrier_phone: this.newCarrierPhone,
      delivery_address: this.newAddress,
      recipient_name: this.newRecipient,
      recipient_phone: this.newPhone,
      shipping_cost: this.newCost,
      notes: this.newNotes
    }).subscribe({
      next: (res) => {
        this.createProcessing = false;
        this.successMsg = `Despacho creado con éxito. Guía #${res.tracking_number}`;
        this.closeCreateModal();
        this.loadShipments();
        setTimeout(() => (this.successMsg = ''), 4000);
      },
      error: (err) => {
        this.createProcessing = false;
        this.errorMsg = err.error?.detail || 'Error al crear el despacho.';
        setTimeout(() => (this.errorMsg = ''), 4000);
      }
    });
  }

  openEventModal(s: Shipment): void {
    this.selectedShipmentForEvent = s;
    this.newEventStatus = 'DISPATCHED';
    this.newEventLocation = 'Almacén Central Santa Cruz';
    this.newEventDescription = 'Salida de paquete con mensajero en ruta.';
  }

  closeEventModal(): void {
    this.selectedShipmentForEvent = null;
  }

  executeAddEvent(): void {
    if (!this.selectedShipmentForEvent) return;
    this.eventProcessing = true;
    this.logisticaService.addTrackingEvent(this.selectedShipmentForEvent.id, {
      status: this.newEventStatus,
      location: this.newEventLocation,
      description: this.newEventDescription
    }).subscribe({
      next: (res) => {
        this.eventProcessing = false;
        this.successMsg = `Hito agregado y estado actualizado a ${res.status}.`;
        this.closeEventModal();
        this.loadShipments();
        if (this.viewingShipment && this.viewingShipment.id === res.id) {
          this.viewingShipment = res;
        }
        setTimeout(() => (this.successMsg = ''), 3500);
      },
      error: (err) => {
        this.eventProcessing = false;
        this.errorMsg = err.error?.detail || 'Error al registrar hito.';
        setTimeout(() => (this.errorMsg = ''), 3500);
      }
    });
  }

  openDetail(s: Shipment): void {
    this.viewingShipment = s;
  }

  closeDetail(): void {
    this.viewingShipment = null;
  }

  getStatusBadge(status: string): string {
    switch (status) {
      case 'PENDING_DISPATCH': return 'bg-warning text-dark';
      case 'DISPATCHED': return 'bg-info text-dark';
      case 'IN_TRANSIT': return 'bg-primary';
      case 'OUT_FOR_DELIVERY': return 'bg-purple text-white';
      case 'DELIVERED': return 'bg-success';
      case 'FAILED': return 'bg-danger';
      default: return 'bg-secondary';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'PENDING_DISPATCH': return 'En Almacén';
      case 'DISPATCHED': return 'Despachado';
      case 'IN_TRANSIT': return 'En Tránsito';
      case 'OUT_FOR_DELIVERY': return 'En Reparto Final';
      case 'DELIVERED': return 'Entregado';
      case 'FAILED': return 'Fallido';
      default: return status;
    }
  }
}
