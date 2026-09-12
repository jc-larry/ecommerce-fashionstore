import { Component, OnInit } from '@angular/core';
import { VentasService, QuotationResponse, OrderReturnResponse, OrderResponse } from '../ventas.service';
import { CatalogoService, Product } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';

@Component({
  selector: 'app-quotations-returns',
  templateUrl: './quotations-returns.component.html',
  styleUrls: ['./quotations-returns.component.css']
})
export class QuotationsReturnsComponent implements OnInit {
  activeTab: 'QUOTATIONS' | 'RETURNS' = 'QUOTATIONS';

  // --- CU21 Cotizaciones ---
  customerName: string = '';
  customerEmail: string = '';
  customerPhone: string = '';
  validDays: number = 15;
  quoteItems: { variant_id: number; product_name: string; sku: string; price: number; quantity: number; subtotal: number }[] = [];
  lastQuotation: QuotationResponse | null = null;
  quotationsList: QuotationResponse[] = [];

  // Conversión de cotización a venta / pago
  convertingQuote: QuotationResponse | null = null;
  convertPaymentMethod: string = 'EFECTIVO';
  convertNit: string = '0';
  convertBusinessName: string = '';

  // Catálogo para seleccionar
  allProducts: Product[] = [];
  selectedVariantId: number | null = null;
  itemQty: number = 1;

  // --- CU22 Devoluciones y Cambios ---
  orderIdToReturn: number | null = null;
  returnType: 'DEVOLUCION_DINERO' | 'CAMBIO_PRENDA' = 'DEVOLUCION_DINERO';
  returnReason: string = 'Talla no adecuada';
  returnItems: { variant_id: number; product_name?: string; quantity: number; replacement_variant_id?: number }[] = [];
  lastReturn: OrderReturnResponse | null = null;

  // Búsqueda y validación de orden para devolución
  searchedOrder: OrderResponse | null = null;
  orderSearchLoading: boolean = false;
  orderSearchError: string | null = null;
  daysSincePurchase: number = 0;
  isReturnExpired: boolean = false;

  // Selección de prenda dentro de la orden
  returnVariantId: number | null = null;
  returnQty: number = 1;
  selectedItemDescription: string = '';
  maxReturnQty: number = 1;
  replacementVariantId: number | null = null;

  loading: boolean = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;

  constructor(
    private ventasService: VentasService,
    private catalogoService: CatalogoService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.loadCatalog();
    this.loadQuotations();
  }

  loadCatalog(): void {
    this.catalogoService.getProducts().subscribe({
      next: (products: Product[]) => {
        this.allProducts = products || [];
      }
    });
  }

  loadQuotations(): void {
    this.ventasService.getQuotations().subscribe({
      next: (quotes) => {
        this.quotationsList = quotes || [];
      },
      error: () => {
        this.quotationsList = [];
      }
    });
  }

  // --- CU21 Helpers ---
  addQuoteItem(): void {
    if (!this.selectedVariantId || this.itemQty <= 0) return;

    for (const p of this.allProducts) {
      for (const v of p.variants) {
        if (v.id === Number(this.selectedVariantId)) {
          const price = Number(p.base_price);
          const existing = this.quoteItems.find(i => i.variant_id === v.id);
          if (existing) {
            existing.quantity += this.itemQty;
            existing.subtotal = Math.round(existing.quantity * price * 100) / 100;
          } else {
            this.quoteItems.push({
              variant_id: v.id,
              product_name: p.name,
              sku: v.sku,
              price: price,
              quantity: this.itemQty,
              subtotal: Math.round(this.itemQty * price * 100) / 100
            });
          }
          this.itemQty = 1;
          return;
        }
      }
    }
  }

  removeQuoteItem(index: number): void {
    this.quoteItems.splice(index, 1);
  }

  get quoteTotal(): number {
    return Math.round(this.quoteItems.reduce((acc, i) => acc + i.subtotal, 0) * 100) / 100;
  }

  onSubmitQuotation(): void {
    if (!this.customerName.trim()) {
      this.errorMessage = 'Por favor ingresa el nombre o razón social del cliente para la cotización.';
      return;
    }
    if (this.quoteItems.length === 0) {
      this.errorMessage = 'La cotización no tiene prendas agregadas. Selecciona al menos una prenda para calcular el presupuesto.';
      return;
    }

    this.errorMessage = null;
    this.loading = true;

    this.ventasService.createQuotation({
      customer_name: this.customerName,
      customer_email: this.customerEmail || undefined,
      customer_phone: this.customerPhone || undefined,
      valid_days: this.validDays,
      details: this.quoteItems.map(i => ({ variant_id: i.variant_id, quantity: i.quantity }))
    }).subscribe({
      next: (res) => {
        this.lastQuotation = res;
        this.quoteItems = [];
        this.customerName = '';
        this.customerEmail = '';
        this.customerPhone = '';
        this.successMessage = `Cotización #${res.quotation_number} generada correctamente con validez de ${this.validDays} días para ${res.customer_name}.`;
        this.loading = false;
        this.loadQuotations();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'No se pudo generar la cotización. Verifica los datos e inténtalo de nuevo.';
        this.loading = false;
      }
    });
  }

  // Conversión de cotización a venta real (CU21 -> CU18/CU20)
  openConvertModal(q: QuotationResponse): void {
    this.convertingQuote = q;
    this.convertBusinessName = q.customer_name;
    this.convertNit = '0';
    this.convertPaymentMethod = 'EFECTIVO';
    this.errorMessage = null;
    this.successMessage = null;
  }

  onConfirmConvertQuotation(): void {
    if (!this.convertingQuote) return;
    const activeBranch = this.branchContext.getActiveBranch();
    const branchId = activeBranch ? activeBranch.id : 1;

    this.loading = true;
    this.errorMessage = null;
    this.successMessage = null;

    this.ventasService.convertQuotationToOrder(this.convertingQuote.id, {
      branch_id: branchId,
      payment_method: this.convertPaymentMethod,
      customer_nit: this.convertNit,
      customer_business_name: this.convertBusinessName
    }).subscribe({
      next: (order) => {
        this.successMessage = `¡Venta Confirmada! Cotización #${this.convertingQuote?.quotation_number} convertida a Orden de Venta #${order.id}. Factura fiscal emitida e inventario descontado.`;
        this.convertingQuote = null;
        this.loading = false;
        this.loadQuotations();
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al convertir la cotización a venta.';
        this.loading = false;
      }
    });
  }

  // --- CU22 Devoluciones y Cambios ---
  onSearchOrder(): void {
    if (!this.orderIdToReturn) {
      this.orderSearchError = 'Ingresa un número de orden para buscar.';
      return;
    }
    this.orderSearchLoading = true;
    this.orderSearchError = null;
    this.searchedOrder = null;
    this.returnItems = [];
    this.isReturnExpired = false;
    this.returnVariantId = null;

    this.ventasService.getOrderById(Number(this.orderIdToReturn)).subscribe({
      next: (order) => {
        this.searchedOrder = order;
        this.orderSearchLoading = false;
        if (order.created_at) {
          const pDate = new Date(order.created_at);
          this.daysSincePurchase = Math.floor((Date.now() - pDate.getTime()) / (1000 * 3600 * 24));
          if (this.daysSincePurchase > 30) {
            this.isReturnExpired = true;
            this.orderSearchError = `Plazo de devolución vencido. Esta orden fue comprada hace ${this.daysSincePurchase} días (el ${pDate.toLocaleDateString()}). El límite máximo permitido es de 30 días calendario.`;
          }
        }
      },
      error: (err) => {
        this.orderSearchError = err?.error?.detail || `Orden #${this.orderIdToReturn} no encontrada. Verifica el número de compra.`;
        this.orderSearchLoading = false;
      }
    });
  }

  selectItemForReturn(item: any): void {
    if (this.isReturnExpired) return;
    this.returnVariantId = item.variant_id;
    this.returnQty = 1;
    this.maxReturnQty = item.quantity;
    this.selectedItemDescription = `${item.product_name} (${item.sku} - ${item.size} / ${item.color})`;
  }

  addReturnItem(): void {
    if (!this.returnVariantId || this.returnQty <= 0) return;
    if (this.returnQty > this.maxReturnQty) {
      this.errorMessage = `No puedes devolver más de ${this.maxReturnQty} unidades de esta prenda.`;
      return;
    }

    const existing = this.returnItems.find(i => i.variant_id === this.returnVariantId);
    if (existing) {
      existing.quantity = Math.min(this.maxReturnQty, existing.quantity + this.returnQty);
    } else {
      this.returnItems.push({
        variant_id: Number(this.returnVariantId),
        product_name: this.selectedItemDescription || `Variante #${this.returnVariantId}`,
        quantity: this.returnQty,
        replacement_variant_id: this.returnType === 'CAMBIO_PRENDA' && this.replacementVariantId ? Number(this.replacementVariantId) : undefined
      });
    }

    this.returnVariantId = null;
    this.selectedItemDescription = '';
    this.returnQty = 1;
    this.replacementVariantId = null;
  }

  removeReturnItem(index: number): void {
    this.returnItems.splice(index, 1);
  }

  onSubmitReturn(): void {
    if (!this.orderIdToReturn || !this.searchedOrder) {
      this.errorMessage = 'Por favor busca y selecciona una orden de venta válida primero.';
      return;
    }
    if (this.isReturnExpired) {
      this.errorMessage = `Operación rechazada: La orden superó el plazo máximo de 30 días (${this.daysSincePurchase} días transcurridos).`;
      return;
    }
    if (this.returnItems.length === 0) {
      this.errorMessage = 'Debes seleccionar al menos una prenda que el cliente desea cambiar o devolver.';
      return;
    }

    this.errorMessage = null;
    this.loading = true;

    this.ventasService.processReturn({
      order_id: Number(this.orderIdToReturn),
      return_type: this.returnType,
      reason: this.returnReason,
      items: this.returnItems.map(i => ({
        variant_id: i.variant_id,
        quantity: i.quantity,
        replacement_variant_id: i.replacement_variant_id
      }))
    }).subscribe({
      next: (res) => {
        this.lastReturn = res;
        this.returnItems = [];
        this.searchedOrder = null;
        this.orderIdToReturn = null;
        this.returnVariantId = null;
        this.selectedItemDescription = '';
        this.successMessage = `Devolución #${res.return_number} procesada exitosamente. Stock actualizado en la sucursal emisora.`;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al procesar la devolución.';
        this.loading = false;
      }
    });
  }
}
