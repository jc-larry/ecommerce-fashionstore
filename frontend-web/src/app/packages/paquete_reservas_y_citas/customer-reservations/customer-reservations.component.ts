import { Component, OnInit } from '@angular/core';
import { ReservasService, Reservation } from '../reservas.service';
import { CatalogoService, Product, BranchOption } from '../../paquete_catalogo_y_tiendas/catalogo.service';
import { VentasService } from '../../paquete_ventas_y_pagos/ventas.service';
import { AuthService } from '../../paquete_seguridad_usuarios/auth.service';
import { PayPalCheckoutService, PayPalCaptureResult } from '../../paquete_ventas_y_pagos/paypal-checkout.service';

export interface FittingItem {
  product: Product;
  variantId: number;
  colorId: number;
  colorName: string;
  sizeId: number;
  sizeName: string;
  unitPrice: number;
  depositAmount: number; // 50% del precio
  imageUrl?: string;
  availableBranchIds: number[];
}

@Component({
  selector: 'app-customer-reservations',
  templateUrl: './customer-reservations.component.html',
  styleUrls: ['./customer-reservations.component.css']
})
export class CustomerReservationsComponent implements OnInit {
  selectedTab: 'mis-reservas' | 'agendar-cita' = 'mis-reservas';

  reservations: Reservation[] = [];
  loading: boolean = false;
  errorMsg: string = '';
  successMsg: string = '';

  // Catálogo visual para reserva
  products: Product[] = [];
  branches: BranchOption[] = [];
  loadingCatalog: boolean = false;
  searchFilter: string = '';
  selectedBranchFilter: number | null = null;

  // Bandeja de probador (máximo 5 prendas)
  fittingItems: FittingItem[] = [];

  // Configuración de la cita principal
  primaryBranchId: number | null = null;
  appointmentDate: string = '';
  appointmentTime: string = '15:00';
  appointmentNotes: string = '';
  customerPhone: string = '';

  // Configuración de segunda sucursal si hay prendas divididas (multi-sucursal)
  secondaryAppointmentTime: string = '17:30';

  // Modal de Pago de Seña (50%)
  showPaymentModal: boolean = false;
  paymentMethod: 'TARJETA' | 'PAYPAL' | 'QR' = 'TARJETA';
  bookingInProgress: boolean = false;

  // Datos de Tarjeta
  cardHolder: string = '';
  cardNumber: string = '';
  cardExpiry: string = '';
  cardCvv: string = '';
  cardBrand: string = 'VISA';

  // Simulador PayPal Sandbox
  showPayPalSimulator: boolean = false;
  paypalSimulatorStep: 'REVIEW' | 'PROCESSING' | 'SUCCESS' = 'REVIEW';
  /** URL de aprobación real de PayPal (null en modo simulación sin credenciales sandbox). */
  paypalApproveUrl: string | null = null;
  paypalSimulated = true;
  paypalError = '';
  paypalOrderId: string = '';
  paypalApproved: boolean = false;
  paypalProcessing: boolean = false;
  paypalFundingSource: 'BALANCE' | 'CARD' = 'BALANCE';
  paypalPayerEmail: string = 'cliente.sandbox@fashionstore.com';
  paypalPayerName: string = 'Cliente Sandbox Bolivia';
  paypalTransactionId: string = '';
  paypalAuthTime: string = '';
  /** true mientras se cargan los botones oficiales de PayPal (modo conectado). */
  paypalButtonsLoading = false;
  readonly exchangeRateUsd: number = 6.96;

  get depositUsd(): number {
    return Math.round((this.totalDepositRequired / this.exchangeRateUsd) * 100) / 100;
  }

  constructor(
    private reservasService: ReservasService,
    public catalogo: CatalogoService,
    private ventasService: VentasService,
    public auth: AuthService,
    private paypalCheckout: PayPalCheckoutService,
  ) {}

  ngOnInit(): void {
    this.loadMyReservations();
    this.loadCatalogAndBranches();

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.appointmentDate = tomorrow.toISOString().split('T')[0];
  }

  loadMyReservations(): void {
    this.loading = true;
    this.reservasService.getMyReservations().subscribe({
      next: (res) => {
        this.reservations = res;
        this.loading = false;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'No se pudieron cargar tus reservas.';
        this.loading = false;
      }
    });
  }

  loadCatalogAndBranches(): void {
    this.loadingCatalog = true;
    this.catalogo.getBranches().subscribe({
      next: (b) => {
        this.branches = b.filter((x) => x.is_active !== false);
        if (this.branches.length > 0 && !this.primaryBranchId) {
          this.primaryBranchId = this.branches[0].id;
        }
      }
    });

    this.catalogo.getProducts().subscribe({
      next: (p) => {
        this.products = p;
        this.loadingCatalog = false;
      },
      error: () => {
        this.loadingCatalog = false;
      }
    });
  }

  resolveImg(url?: string | null): string {
    return this.catalogo.resolveImageUrl(url);
  }

  primaryProductImage(p: Product): string {
    if (p.images && p.images.length > 0) {
      return this.resolveImg(p.images[0].image_url);
    }
    return 'assets/placeholder-fashion.jpg';
  }

  // Filtrado de prendas en catálogo
  get filteredProducts(): Product[] {
    return this.products.filter((p) => {
      const matchSearch = !this.searchFilter ||
        p.name.toLowerCase().includes(this.searchFilter.toLowerCase()) ||
        (p.category?.name && p.category.name.toLowerCase().includes(this.searchFilter.toLowerCase()));
      return matchSearch;
    });
  }

  // Agregar prenda al probador (hasta 5 prendas)
  addToFittingBag(p: Product, variantIndex: number = 0): void {
    if (this.fittingItems.length >= 5) {
      alert('Puedes agendar hasta un máximo de 5 prendas por cita de probador.');
      return;
    }

    if (!p.variants || p.variants.length === 0) {
      alert('Esta prenda no tiene variantes de talla disponibles.');
      return;
    }

    const v = p.variants[variantIndex] || p.variants[0];
    const exists = this.fittingItems.find((it) => it.variantId === v.id);
    if (exists) {
      alert('Esta prenda y talla ya está agregada en tu lista de probador.');
      return;
    }

    const unitPrice = Number(p.base_price);
    const depositAmount = Math.round(unitPrice * 0.5 * 100) / 100;

    // Obtener imagen del color o la principal
    let img = p.images && p.images.length > 0 ? this.resolveImg(p.images[0].image_url) : '';

    this.fittingItems.push({
      product: p,
      variantId: v.id,
      colorId: v.color_id || 1,
      colorName: v.color?.name || 'Estándar',
      sizeId: v.size_id || 1,
      sizeName: v.size?.name || 'M',
      unitPrice: unitPrice,
      depositAmount: depositAmount,
      imageUrl: img,
      availableBranchIds: this.branches.map(b => b.id), // Se valida contra sucursales
    });

    this.successMsg = `¡"${p.name}" (Talla ${v.size?.name || 'M'}) añadida al probador!`;
    setTimeout(() => (this.successMsg = ''), 3000);
  }

  removeFromFittingBag(index: number): void {
    this.fittingItems.splice(index, 1);
  }

  // Cálculos financieros de la seña del 50%
  get totalProductsValue(): number {
    return this.fittingItems.reduce((sum, it) => sum + it.unitPrice, 0);
  }

  get totalDepositRequired(): number {
    return Math.round(this.totalProductsValue * 0.5 * 100) / 100;
  }

  get remainingBalance(): number {
    return Math.round((this.totalProductsValue - this.totalDepositRequired) * 100) / 100;
  }

  // Detección multi-sucursal
  get primaryBranch(): BranchOption | undefined {
    return this.branches.find((b) => b.id === this.primaryBranchId);
  }

  get hasMultiBranchConflict(): boolean {
    // Si hay más de 1 sucursal y tenemos prendas seleccionadas
    return this.branches.length > 1 && this.fittingItems.length >= 2;
  }

  openPaymentModal(): void {
    if (this.fittingItems.length === 0) {
      alert('Agrega al menos una prenda a tu probador antes de agendar la cita.');
      return;
    }
    if (!this.primaryBranchId) {
      alert('Por favor selecciona una sucursal para tu cita.');
      return;
    }
    if (!this.appointmentDate || !this.appointmentTime) {
      alert('Por favor selecciona la fecha y hora de tu cita.');
      return;
    }
    this.showPaymentModal = true;
  }

  openPayPalSimulator(): void {
    this.paypalSimulatorStep = 'REVIEW';
    this.paypalProcessing = false;
    this.paypalError = '';
    this.showPayPalSimulator = true;

    // Con credenciales en el backend se usa PayPal real (sandbox); sin ellas, el simulador.
    this.paypalCheckout.getConfig().subscribe({
      next: (config) => {
        this.paypalSimulated = config.simulated;
        if (config.simulated) {
          this.createSimulatedPayPalOrder();
        } else {
          this.renderRealPayPalButtons();
        }
      },
      error: () => (this.paypalError = 'No se pudo obtener la configuración de PayPal.')
    });
  }

  /** Modo conectado: botones oficiales de PayPal; el cliente inicia sesión en PayPal sandbox. */
  private renderRealPayPalButtons(): void {
    const amountBob = this.totalDepositRequired;
    const description = `Seña 50% Reserva Probador FashionStore (${this.fittingItems.length} prendas)`;
    this.paypalButtonsLoading = true;
    // Espera a que Angular pinte el contenedor del modal.
    setTimeout(() => {
      const container = document.getElementById('paypal-buttons-reserva');
      if (!container) return;
      this.paypalCheckout.renderButtons(container, {
        amountBob,
        description,
        onApproved: (capture) => this.onPayPalCaptured(capture),
        onError: (msg) => {
          this.paypalSimulatorStep = 'REVIEW';
          this.paypalError = msg;
        },
        onCancel: () => (this.paypalError = 'Cancelaste el pago en PayPal. No se realizó ningún cobro.')
      })
        .catch((e: Error) => (this.paypalError = e.message))
        .finally(() => (this.paypalButtonsLoading = false));
    });
  }

  private createSimulatedPayPalOrder(): void {
    if (this.paypalOrderId) return;
    this.ventasService.createPayPalOrder(
      this.totalDepositRequired,
      `Seña 50% Reserva Probador FashionStore (${this.fittingItems.length} prendas)`
    ).subscribe({
      next: (order) => {
        this.paypalOrderId = order.id;
        this.paypalSimulated = !!order.simulated;
      },
      error: (e) => {
        this.paypalOrderId = '';
        this.paypalError = e?.error?.detail || 'No se pudo iniciar el pago con PayPal.';
      }
    });
  }

  /** Seña capturada por PayPal (real o simulada): guarda el comprobante para la reserva. */
  private onPayPalCaptured(res: PayPalCaptureResult): void {
    this.paypalOrderId = res.id;
    this.paypalApproved = true;
    this.paypalProcessing = false;
    this.paypalTransactionId = res.gateway_reference || `PAYPAL:${res.capture_id || res.id}`;
    if (res.payer?.email_address) this.paypalPayerEmail = res.payer.email_address;
    const name = [res.payer?.name?.given_name, res.payer?.name?.surname].filter(Boolean).join(' ');
    if (name) this.paypalPayerName = name;
    this.paypalAuthTime = new Date().toLocaleString('es-BO', { timeZone: 'America/La_Paz' });
    this.paypalSimulatorStep = 'SUCCESS';
  }

  executePayPalSimulation(): void {
    this.paypalSimulatorStep = 'PROCESSING';
    this.paypalProcessing = true;

    if (!this.paypalOrderId) {
      this.paypalSimulatorStep = 'REVIEW';
      this.paypalProcessing = false;
      this.paypalError = this.paypalError || 'La orden de PayPal aún no está lista. Intenta nuevamente.';
      return;
    }
    const orderIdToCapture = this.paypalOrderId;

    // Simulamos latencia realista de autorización bancaria y llamada a API PayPal Sandbox
    setTimeout(() => {
      this.ventasService.capturePayPalOrder(orderIdToCapture).subscribe({
        next: (res) => this.onPayPalCaptured(res),
        error: (e) => {
          this.paypalApproved = false;
          this.paypalProcessing = false;
          this.paypalSimulatorStep = 'REVIEW';
          this.paypalError = e?.error?.detail || 'PayPal no confirmó el pago. No se realizó ningún cobro.';
        }
      });
    }, 1400);
  }

  closePayPalSimulator(): void {
    this.showPayPalSimulator = false;
  }

  resetPayPalPayment(): void {
    this.paypalApproved = false;
    this.paypalTransactionId = '';
    this.paypalOrderId = '';
    this.paypalApproveUrl = null;
    this.paypalError = '';
    this.paypalSimulatorStep = 'REVIEW';
  }

  confirmBookingAndDeposit(): void {
    if (!this.auth.isLoggedIn()) {
      alert('Debes iniciar sesión con tu cuenta para agendar una reserva.');
      return;
    }

    let paymentRef = '';
    if (this.paymentMethod === 'TARJETA') {
      const cleanCard = (this.cardNumber || '').replace(/\s+/g, '');
      if (cleanCard.length < 13) {
        alert('Por favor ingresa un número de tarjeta válido (mínimo 13 dígitos).');
        return;
      }
      if (!this.cardCvv || this.cardCvv.length < 3) {
        alert('Por favor ingresa el código de seguridad CVV (3 o 4 dígitos).');
        return;
      }
      paymentRef = `TARJETA-${this.cardBrand}-****${cleanCard.slice(-4)}`;
    } else if (this.paymentMethod === 'PAYPAL') {
      if (!this.paypalApproved) {
        // Si no ha procesado aún la pasarela PayPal, abrimos el simulador
        this.openPayPalSimulator();
        return;
      }
      // El backend verifica esta orden directamente con PayPal antes de registrar la seña.
      paymentRef = `PAYPAL:${this.paypalOrderId}`;
    } else if (this.paymentMethod === 'QR') {
      paymentRef = `QR-BNB-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
    }

    this.bookingInProgress = true;
    const itemsPayload = this.fittingItems.map((it) => ({
      variant_id: it.variantId,
      quantity: 1,
      notes: `Seña 50% calculada: Bs. ${it.depositAmount}`,
    }));

    const notesPayload = `Cita Probador para ${this.appointmentDate} a las ${this.appointmentTime}. Seña pagada online vía ${this.paymentMethod} (Ref: ${paymentRef}). Abono: Bs. ${this.totalDepositRequired}. Saldo en caja: Bs. ${this.remainingBalance}. Tel: ${this.customerPhone || 'S/N'}. ${this.appointmentNotes}`.trim();

    this.reservasService.createReservation({
      branch_id: this.primaryBranchId!,
      items: itemsPayload,
      notes: notesPayload,
      appointment_date: this.appointmentDate,
      appointment_time: this.appointmentTime,
      payment_method: this.paymentMethod,
      payment_reference: paymentRef,
      reserved_at: `${this.appointmentDate}T${this.appointmentTime}:00`,
    }).subscribe({
      next: (res) => {
        this.bookingInProgress = false;
        this.showPaymentModal = false;
        this.fittingItems = [];
        this.successMsg = `¡Cita confirmada con éxito! Código: ${res.reservation_code}. Seña del 50% pagada online vía ${this.paymentMethod} (Bs. ${this.totalDepositRequired}). Prendas bloqueadas por 48 horas.`;
        this.selectedTab = 'mis-reservas';
        this.loadMyReservations();
      },
      error: (err) => {
        this.bookingInProgress = false;
        this.errorMsg = err.error?.detail || 'No se pudo registrar la reserva en la sucursal seleccionada.';
      }
    });
  }

  canCancelReservation(r: Reservation): boolean {
    if (r.status !== 'PENDING' && r.status !== 'PREPARING') return false;
    if (!r.reserved_at) return false;
    const resDate = new Date(r.reserved_at).getTime();
    const now = new Date().getTime();
    const hoursRemaining = (resDate - now) / (1000 * 3600);
    return hoursRemaining >= 24;
  }

  cancelReservation(r: Reservation): void {
    if (!this.canCancelReservation(r)) {
      alert('No es posible cancelar la cita con menos de 24 horas de anticipación. Las prendas ya se encuentran preparadas en probador y se considera venta perdida.');
      return;
    }
    if (!confirm(`¿Deseas cancelar tu reserva ${r.reservation_code}? Las prendas serán liberadas de inmediato.`)) {
      return;
    }
    this.reservasService.cancelReservation(r.id).subscribe({
      next: () => {
        this.successMsg = `Tu reserva ${r.reservation_code} fue cancelada exitosamente y las prendas fueron repuestas al stock libre.`;
        this.loadMyReservations();
        setTimeout(() => (this.successMsg = ''), 3500);
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cancelar la reserva.';
        setTimeout(() => (this.errorMsg = ''), 3500);
      }
    });
  }

  getStatusBadge(status: string): string {
    switch (status) {
      case 'PENDING': return 'bg-warning text-dark';
      case 'PREPARING': return 'bg-primary text-white';
      case 'READY': return 'bg-success text-white';
      case 'COMPLETED': return 'bg-dark text-white';
      case 'CANCELLED': return 'bg-secondary text-white';
      default: return 'bg-light text-dark';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'PENDING': return '🟡 Pendiente de Preparación';
      case 'PREPARING': return '🔵 Prendas en Perchero';
      case 'READY': return '🟢 Listo en Vestidor';
      case 'COMPLETED': return '🟣 Venta Concretada';
      case 'CANCELLED': return '⚪ Cancelada';
      default: return status;
    }
  }
}
