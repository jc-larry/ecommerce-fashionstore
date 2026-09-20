import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { Router } from '@angular/router';
import { VentasService, CartResponse, CartItem, OrderResponse } from '../ventas.service';
import { CatalogoService } from '../../paquete_catalogo_y_tiendas/catalogo.service';
import { AuthService } from '../../paquete_seguridad_usuarios/auth.service';
import { PayPalCheckoutService, PayPalCaptureResult } from '../paypal-checkout.service';

@Component({
  selector: 'app-cart-modal',
  templateUrl: './cart-modal.component.html',
  styleUrls: ['./cart-modal.component.css']
})
export class CartModalComponent implements OnInit {
  @Input() isOpen: boolean = false;
  @Output() close = new EventEmitter<void>();

  cart: CartResponse | null = null;
  branches: any[] = [];

  // Checkout step: 'CART' | 'CHECKOUT' | 'SUCCESS'
  currentStep: 'CART' | 'CHECKOUT' | 'SUCCESS' = 'CART';

  // Formulario Checkout
  selectedBranchId: number | null = null;
  paymentType: 'TARJETA' | 'PAYPAL' | 'QR' = 'TARJETA';
  docType: 'FACTURA' | 'NOTA_ENTREGA' = 'FACTURA';
  customerNit: string = '';
  customerName: string = '';
  couponCode: string = '';

  // Datos Tarjeta
  cardBrand: string = 'VISA';
  cardHolder: string = '';
  cardNumber: string = '';
  cardExpiry: string = '';
  cardCvv: string = '';

  // Datos PayPal y Simulador Sandbox
  paypalOrderId: string = '';
  showPayPalSimulator: boolean = false;
  paypalSimulatorStep: 'REVIEW' | 'PROCESSING' | 'SUCCESS' = 'REVIEW';
  /** URL de aprobación real de PayPal (null en modo simulación sin credenciales sandbox). */
  paypalApproveUrl: string | null = null;
  paypalSimulated = true;
  paypalError = '';
  paypalFundingSource: 'BALANCE' | 'CARD' = 'BALANCE';
  paypalPayerEmail: string = 'comprador.sandbox@fashionstore.com';
  paypalPayerName: string = 'Cliente Moda Sandbox';
  paypalPayerId: string = '';
  /** true mientras se cargan los botones oficiales de PayPal (modo conectado). */
  paypalButtonsLoading = false;
  paypalTransactionId: string = '';
  paypalApproved: boolean = false;
  paypalProcessing: boolean = false;
  paypalAuthTime: string = '';
  readonly exchangeRateUsd: number = 6.96;

  get cartTotalUsd(): number {
    return Math.round(((this.cart?.subtotal || 0) / this.exchangeRateUsd) * 100) / 100;
  }

  // Orden completada
  completedOrder: OrderResponse | null = null;

  loading: boolean = false;
  errorMessage: string | null = null;

  constructor(
    private ventasService: VentasService,
    private catalogoService: CatalogoService,
    public auth: AuthService,
    private router: Router,
    private paypalCheckout: PayPalCheckoutService
  ) {}

  ngOnInit(): void {
    if (this.auth.isLoggedIn()) {
      this.loadCart();
    }
    this.loadBranches();
  }

  loadCart(): void {
    if (!this.auth.isLoggedIn()) {
      this.cart = null;
      return;
    }
    this.loading = true;
    this.ventasService.getCart().subscribe({
      next: (data) => {
        this.cart = data;
        this.loading = false;
      },
      error: () => {
        this.cart = null;
        this.loading = false;
      }
    });
  }

  goToLogin(): void {
    this.closeModal();
    this.router.navigate(['/login']);
  }

  goToRegister(): void {
    this.closeModal();
    this.router.navigate(['/register']);
  }

  loadBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (data: any[]) => {
        this.branches = data;
        if (data.length > 0) {
          this.selectedBranchId = data[0].id;
        }
      }
    });
  }

  updateQuantity(item: CartItem, delta: number): void {
    const newQty = item.quantity + delta;
    this.errorMessage = null;
    this.ventasService.updateCartItem(item.id, newQty).subscribe({
      next: (updatedCart) => {
        this.cart = updatedCart;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al actualizar cantidad.';
      }
    });
  }

  removeItem(item: CartItem): void {
    this.ventasService.removeCartItem(item.id).subscribe({
      next: (updatedCart) => {
        this.cart = updatedCart;
      }
    });
  }

  clearAll(): void {
    this.ventasService.clearCart().subscribe({
      next: (emptyCart) => {
        this.cart = emptyCart;
      }
    });
  }

  proceedToCheckout(): void {
    if (!this.cart || this.cart.items.length === 0) return;
    this.currentStep = 'CHECKOUT';
  }

  backToCart(): void {
    this.currentStep = 'CART';
    this.errorMessage = null;
  }

  openPayPalSimulator(): void {
    if (!this.cart || this.cart.items.length === 0) return;
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

  /** Modo conectado: botones oficiales de PayPal; el comprador inicia sesión en PayPal sandbox. */
  private renderRealPayPalButtons(): void {
    if (!this.cart) return;
    const amountBob = this.cart.subtotal;
    const description = `Compra Online FashionStore (${this.cart.items_count} prendas)`;
    this.paypalButtonsLoading = true;
    // Espera a que Angular pinte el contenedor del modal.
    setTimeout(() => {
      const container = document.getElementById('paypal-buttons-cart');
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
    if (!this.cart || this.paypalOrderId) return;
    this.ventasService.createPayPalOrder(
      this.cart.subtotal,
      `Compra Online FashionStore (${this.cart.items_count} prendas)`
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

  /** Pago capturado por PayPal (real o simulado): guarda el comprobante para el checkout. */
  private onPayPalCaptured(res: PayPalCaptureResult): void {
    this.paypalOrderId = res.id;
    this.paypalApproved = true;
    this.paypalProcessing = false;
    this.paypalTransactionId = res.gateway_reference || `PAYPAL:${res.capture_id || res.id}`;
    this.paypalPayerId = res.payer?.payer_id || '';
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
    this.paypalPayerId = '';
    this.paypalApproveUrl = null;
    this.paypalError = '';
    this.paypalSimulatorStep = 'REVIEW';
  }

  submitOrder(): void {
    if (!this.selectedBranchId) {
      this.errorMessage = 'Selecciona la sucursal de retiro o despacho.';
      return;
    }

    let cardLastFour = '4242';
    if (this.paymentType === 'TARJETA') {
      const cleanCard = (this.cardNumber || '').replace(/\s+/g, '');
      if (cleanCard.length < 13) {
        this.errorMessage = 'Por favor ingresa un número de tarjeta válido (mínimo 13 dígitos).';
        return;
      }
      if (!this.cardCvv || this.cardCvv.length < 3) {
        this.errorMessage = 'Por favor ingresa el código CVV (3 o 4 dígitos).';
        return;
      }
      cardLastFour = cleanCard.slice(-4);
    } else if (this.paymentType === 'PAYPAL' && !this.paypalApproved) {
      this.openPayPalSimulator();
      return;
    }

    this.errorMessage = null;
    this.loading = true;

    const payload: any = {
      channel: 'ONLINE',
      branch_id: this.selectedBranchId,
      payment_type: this.paymentType,
      doc_type: this.docType,
      customer_nit: this.customerNit || '0',
      customer_name: this.customerName || 'CLIENTE FINAL',
      coupon_code: this.couponCode ? this.couponCode.trim().toUpperCase() : undefined,
    };

    if (this.paymentType === 'TARJETA') {
      payload.card_payment = {
        card_brand: this.cardBrand,
        card_last4: cardLastFour,
        gateway_reference: `AUTH-${this.cardBrand}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`
      };
    } else if (this.paymentType === 'PAYPAL') {
      payload.paypal_payment = {
        paypal_order_id: this.paypalOrderId,
        paypal_payer_id: this.paypalPayerId || undefined,
        paypal_payer_email: this.paypalPayerEmail,
        gateway_reference: this.paypalTransactionId
      };
    } else if (this.paymentType === 'QR') {
      payload.qr_payment = { qr_reference: `QR-ONLINE-${Date.now().toString().slice(-6)}` };
    }

    this.ventasService.processCheckout(payload).subscribe({
      next: (order) => {
        this.completedOrder = order;
        this.currentStep = 'SUCCESS';
        this.loading = false;
        this.loadCart(); // ya se vació en backend
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al completar la compra.';
        this.loading = false;
      }
    });
  }

  closeModal(): void {
    this.currentStep = 'CART';
    this.completedOrder = null;
    this.close.emit();
  }
}
