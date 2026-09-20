import { Component, OnInit } from '@angular/core';
import { ReservasService, Reservation } from '../reservas.service';
import { CatalogoService } from '../../paquete_catalogo_y_tiendas/catalogo.service';
import { AuthService } from '../../paquete_seguridad_usuarios/auth.service';
import { VentasService } from '../../paquete_ventas_y_pagos/ventas.service';

@Component({
  selector: 'app-reservations-board',
  templateUrl: './reservations-board.component.html',
  styleUrls: ['./reservations-board.component.css']
})
export class ReservationsBoardComponent implements OnInit {
  reservations: Reservation[] = [];
  branches: any[] = [];
  selectedBranchId?: number;
  loading: boolean = false;
  errorMsg: string = '';
  successMsg: string = '';

  // Modal Conversión POS (CU25)
  selectedResForPos: Reservation | null = null;
  posPaymentMethod: string = 'EFECTIVO';
  posNit: string = '0';
  posBusinessName: string = 'SIN NOMBRE';
  posProcessing: boolean = false;

  constructor(
    private reservasService: ReservasService,
    private catalogoService: CatalogoService,
    public authService: AuthService,
    private ventasService: VentasService
  ) {}

  ngOnInit(): void {
    this.loadBranches();
    this.loadReservations();
  }

  loadBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (b: any[]) => (this.branches = b),
      error: () => {}
    });
  }

  loadReservations(): void {
    this.loading = true;
    this.errorMsg = '';
    this.reservasService.getReservations(this.selectedBranchId).subscribe({
      next: (data) => {
        this.reservations = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cargar las reservas.';
        this.loading = false;
      }
    });
  }

  getByStatus(status: string): Reservation[] {
    return this.reservations.filter(r => r.status === status);
  }

  resolveImg(url?: string | null): string {
    return this.catalogoService.resolveImageUrl(url);
  }

  advanceStatus(res: Reservation, nextStatus: string): void {
    this.reservasService.updateStatus(res.id, nextStatus).subscribe({
      next: () => {
        this.successMsg = `Reserva ${res.reservation_code} actualizada a ${nextStatus}.`;
        this.loadReservations();
        setTimeout(() => (this.successMsg = ''), 3500);
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'No se pudo actualizar el estado.';
        setTimeout(() => (this.errorMsg = ''), 3500);
      }
    });
  }

  cancelReservation(res: Reservation): void {
    if (!confirm(`¿Confirmas la cancelación de la reserva ${res.reservation_code}? El stock reservado será liberado inmediatamente.`)) {
      return;
    }
    this.reservasService.cancelReservation(res.id).subscribe({
      next: () => {
        this.successMsg = `Reserva ${res.reservation_code} cancelada y stock liberado correctamente.`;
        this.loadReservations();
        setTimeout(() => (this.successMsg = ''), 3500);
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cancelar la reserva.';
        setTimeout(() => (this.errorMsg = ''), 3500);
      }
    });
  }

  selectedItemIds: number[] = [];
  posCashReceived: number = 0;
  posCardLast4: string = '4242';
  posCardBrand: string = 'VISA';
  posQrVerified: boolean = false;

  get posCashChange(): number {
    return Math.max(0, (this.posCashReceived || 0) - this.calculateBalanceToPay());
  }

  openPosModal(res: Reservation): void {
    this.selectedResForPos = res;
    // Por defecto, se marcan todas las prendas para compra
    this.selectedItemIds = res.items.map((it) => it.id);
    this.posPaymentMethod = 'EFECTIVO';
    this.posNit = res.customer_phone || '0';
    this.posBusinessName = res.customer_name || 'SIN NOMBRE';
    this.posCashReceived = this.calculateBalanceToPay();
    this.posQrVerified = false;
  }

  closePosModal(): void {
    this.selectedResForPos = null;
    this.selectedItemIds = [];
    this.posQrVerified = false;
  }

  toggleItemSelection(itemId: number): void {
    const idx = this.selectedItemIds.indexOf(itemId);
    if (idx >= 0) {
      this.selectedItemIds.splice(idx, 1);
    } else {
      this.selectedItemIds.push(itemId);
    }
  }

  isItemSelected(itemId: number): boolean {
    return this.selectedItemIds.includes(itemId);
  }

  getPurchasedItems(): any[] {
    if (!this.selectedResForPos) return [];
    return this.selectedResForPos.items.filter((it) => this.isItemSelected(it.id));
  }

  getReturnedItems(): any[] {
    if (!this.selectedResForPos) return [];
    return this.selectedResForPos.items.filter((it) => !this.isItemSelected(it.id));
  }

  calculatePurchasedSubtotal(): number {
    return this.getPurchasedItems().reduce((acc, it) => acc + (it.unit_price * it.quantity), 0);
  }

  calculatePurchasedDeposit(): number {
    return Math.round(this.calculatePurchasedSubtotal() * 0.50 * 100) / 100;
  }

  calculateBalanceToPay(): number {
    return Math.round((this.calculatePurchasedSubtotal() - this.calculatePurchasedDeposit()) * 100) / 100;
  }

  calculateSubtotal(res: Reservation): number {
    return res.items.reduce((acc, it) => acc + (it.unit_price * it.quantity), 0);
  }

  executeConvertToPos(): void {
    if (!this.selectedResForPos) return;

    if (this.selectedItemIds.length === 0) {
      alert('Debe marcar al menos una prenda que el cliente compre. Si el cliente no compra ninguna, utilice el botón cancelar para reponer todas al inventario.');
      return;
    }

    this.posProcessing = true;
    const returnedCount = this.getReturnedItems().length;
    const reservation = this.selectedResForPos;

    // El saldo entra a la caja abierta de quien cobra, para que cuadre en su arqueo.
    this.ventasService.getCurrentShift(reservation.branch_id).subscribe({
      next: (shift) => {
        if (!shift) {
          this.posProcessing = false;
          this.errorMsg = 'Abre tu caja en "Arqueo de Caja" (o cobra desde el Punto de Venta) antes de cobrar la reserva.';
          setTimeout(() => (this.errorMsg = ''), 5000);
          return;
        }
        this.submitConvertToPos(reservation, shift.id, returnedCount);
      },
      error: () => {
        this.posProcessing = false;
        this.errorMsg = 'No se pudo verificar tu caja abierta.';
      },
    });
  }

  private submitConvertToPos(reservation: Reservation, cashShiftId: number, returnedCount: number): void {
    this.reservasService.convertToPos(reservation.id, {
      cash_shift_id: cashShiftId,
      payment_method: this.posPaymentMethod,
      nit_ruc: this.posNit,
      business_name: this.posBusinessName,
      selected_item_ids: this.selectedItemIds,
    }).subscribe({
      next: (res) => {
        this.posProcessing = false;
        const msgExtra = returnedCount > 0
          ? ` (${returnedCount} prenda${returnedCount === 1 ? '' : 's'} devuelta${returnedCount === 1 ? '' : 's'} inmediatamente al stock disponible de la sucursal).`
          : '';
        this.successMsg = `¡Venta POS concretada con éxito! Factura emitida vinculada al pedido #${res.completed_sale_id}.${msgExtra}`;
        this.closePosModal();
        this.loadReservations();
        setTimeout(() => (this.successMsg = ''), 5500);
      },
      error: (err) => {
        this.posProcessing = false;
        this.errorMsg = err.error?.detail || 'Error al facturar la reserva en el POS.';
        setTimeout(() => (this.errorMsg = ''), 4000);
      }
    });
  }
}
