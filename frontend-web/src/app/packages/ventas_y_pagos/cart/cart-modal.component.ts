import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { Router } from '@angular/router';
import { VentasService, CartResponse, CartItem, OrderResponse } from '../ventas.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

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
  selectedBranchId: number | null = null;

  // Checkout step: 'CART' | 'CHECKOUT' | 'SUCCESS'
  currentStep: 'CART' | 'CHECKOUT' | 'SUCCESS' = 'CART';

  // Datos de Checkout
  paymentType: 'TARJETA' | 'QR' | 'EFECTIVO' | 'CREDITO' = 'TARJETA';
  docType: 'FACTURA' | 'NOTA_ENTREGA' = 'FACTURA';
  customerNit: string = '0';
  customerName: string = '';
  couponCode: string = '';

  // Datos Tarjeta
  cardBrand: string = 'VISA';
  cardLast4: string = '4242';

  // Orden completada
  completedOrder: OrderResponse | null = null;

  loading: boolean = false;
  errorMessage: string | null = null;

  constructor(
    private ventasService: VentasService,
    private catalogoService: CatalogoService,
    public auth: AuthService,
    private router: Router
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

  submitOrder(): void {
    if (!this.selectedBranchId) {
      this.errorMessage = 'Selecciona la sucursal de retiro o despacho.';
      return;
    }

    this.errorMessage = null;
    this.loading = true;

    const payload: any = {
      channel: 'ONLINE',
      branch_id: this.selectedBranchId,
      payment_type: this.paymentType,
      doc_type: this.docType,
      customer_nit: this.customerNit,
      customer_name: this.customerName,
      coupon_code: this.couponCode ? this.couponCode.trim().toUpperCase() : undefined,
    };

    if (this.paymentType === 'TARJETA') {
      payload.card_payment = {
        card_brand: this.cardBrand,
        card_last4: this.cardLast4 ? this.cardLast4.slice(-4) : '4242'
      };
    } else if (this.paymentType === 'QR') {
      payload.qr_payment = { qr_reference: `QR-ONLINE-${Date.now().toString().slice(-6)}` };
    } else if (this.paymentType === 'EFECTIVO') {
      payload.cash_payment = { cash_received: this.cart ? this.cart.subtotal : 0 };
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
