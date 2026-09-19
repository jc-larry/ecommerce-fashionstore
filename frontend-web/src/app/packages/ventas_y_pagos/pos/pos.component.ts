import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { VentasService, CashShiftResponse, OrderResponse } from '../ventas.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';
import { InventarioService, InventoryValuationItem } from '../../inventario_y_proveedores/inventario.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';
import { ReservasService, Reservation, ReservationItem } from '../../reservas_y_citas/reservas.service';

interface PosItem {
  variant_id: number;
  product_name: string;
  sku: string;
  size: string;
  color: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
  stock_available: number;
}

@Component({
  selector: 'app-pos',
  templateUrl: './pos.component.html',
  styleUrls: ['./pos.component.css']
})
export class PosComponent implements OnInit, OnDestroy {
  activeTab: 'POS' | 'RESERVAS' | 'ALISTADO' = 'POS';

  currentShift: CashShiftResponse | null = null;
  branches: any[] = [];
  selectedBranchId: number | null = null;
  selectedBranchName: string = '';
  isCentral: boolean = false;

  private branchSub!: Subscription;

  // Apertura rápida de turno
  openingAmount: number = 100;
  openingNotes: string = '';
  shiftError: string | null = null;

  // Catálogo e inventario real exclusivo de la sucursal activa
  searchQuery: string = '';
  searchResults: InventoryValuationItem[] = [];
  branchInventory: InventoryValuationItem[] = [];
  loadingInventory: boolean = false;

  // Ticket actual
  ticketItems: PosItem[] = [];
  couponCode: string = '';
  discountAmount: number = 0;

  // Pago
  paymentType: 'EFECTIVO' | 'TARJETA' | 'QR' | 'CREDITO' = 'EFECTIVO';
  cashReceived: number = 0;
  cardBrand: string = 'VISA';
  cardLast4: string = '';
  docType: 'FACTURA' | 'NOTA_ENTREGA' = 'FACTURA';
  customerNit: string = '0';
  customerName: string = 'Cliente de Paso';

  // Reservas de Probador Virtual en Sucursal
  branchReservations: Reservation[] = [];
  loadingReservations: boolean = false;
  selectedReservation: Reservation | null = null;
  reservationSelectedItems: { [itemId: number]: boolean } = {};
  resPaymentMethod: 'EFECTIVO' | 'TARJETA' | 'QR' = 'EFECTIVO';
  resCustomerNit: string = '0';
  resCustomerName: string = '';
  resCashReceived: number | null = null;
  resCardLast4 = '';
  resPaymentReference = '';
  resLoading: boolean = false;
  resSuccessMessage: string | null = null;
  resErrorMessage: string | null = null;

  // Alistado y Despacho de Pedidos
  fulfillmentOrders: OrderResponse[] = [];
  fulfillmentStatusFilter: string = '';
  loadingFulfillment: boolean = false;
  fulfillmentSuccessMsg: string | null = null;
  fulfillmentErrorMsg: string | null = null;

  // Estado general
  loading: boolean = false;
  errorMessage: string | null = null;
  lastOrderSuccess: OrderResponse | null = null;

  constructor(
    private ventasService: VentasService,
    private catalogoService: CatalogoService,
    private inventarioService: InventarioService,
    private reservasService: ReservasService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.branchSub = this.branchContext.activeBranch$.subscribe((activeBranch) => {
      if (!activeBranch) {
        // Solo Casa Matriz elige sucursal; un cajero/encargado siempre opera en la suya.
        this.isCentral = this.branchContext.isCentral();
        this.selectedBranchId = null;
        this.selectedBranchName = this.isCentral ? 'Casa Matriz (Consolidado)' : 'Sin sucursal asignada';
        this.currentShift = null;
        this.branchInventory = [];
        this.ticketItems = [];
      } else {
        this.isCentral = false;
        this.selectedBranchId = activeBranch.id;
        this.selectedBranchName = activeBranch.name;
        this.loadShiftForBranch(activeBranch.id);
        this.loadBranchInventory(activeBranch.id);
      }
    });

    this.catalogoService.getBranches().subscribe({
      next: (data: any[]) => {
        this.branches = data;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.branchSub) {
      this.branchSub.unsubscribe();
    }
  }

  selectBranch(branch: any): void {
    this.branchContext.setActiveBranch({
      id: branch.id,
      name: branch.name,
      code: branch.code,
      city: branch.city
    });
  }

  loadShiftForBranch(branchId: number): void {
    this.loading = true;
    this.ventasService.getCurrentShift(branchId).subscribe({
      next: (shift) => {
        this.currentShift = shift;
        this.loading = false;
      },
      error: () => {
        this.currentShift = null;
        this.loading = false;
      }
    });
  }

  loadBranchInventory(branchId: number): void {
    this.loadingInventory = true;
    // [Separación por sucursal] Se usa /inventory (accesible para CAJERO) en vez de
    // /valuation (solo SUPERADMIN/ENCARGADO, expone costo/margen) — el POS solo necesita
    // stock y precio de venta, no capital invertido.
    this.inventarioService.getInventory(branchId).subscribe({
      next: (items) => {
        // Solo prendas con existencias reales en esta tienda física
        this.branchInventory = (items || []).filter((item: any) => item.stock_actual > 0);
        this.loadingInventory = false;
      },
      error: () => {
        this.branchInventory = [];
        this.loadingInventory = false;
      }
    });
  }

  openShift(): void {
    if (!this.selectedBranchId) {
      this.shiftError = 'Selecciona una sucursal para abrir el turno de caja.';
      return;
    }
    this.shiftError = null;
    this.loading = true;
    this.ventasService.openShift(this.selectedBranchId, this.openingAmount).subscribe({
      next: (shift) => {
        this.currentShift = shift;
        this.loading = false;
      },
      error: (err) => {
        this.shiftError = err?.error?.detail || 'Error al abrir turno de caja.';
        this.loading = false;
      }
    });
  }

  onSearchChange(): void {
    const q = this.searchQuery.trim().toLowerCase();
    if (q.length < 2) {
      this.searchResults = [];
      return;
    }

    this.searchResults = this.branchInventory.filter(item => {
      const matchName = item.product_name && item.product_name.toLowerCase().includes(q);
      const matchSku = item.sku && item.sku.toLowerCase().includes(q);
      const matchColor = item.color_name && item.color_name.toLowerCase().includes(q);
      return (matchName || matchSku || matchColor) && item.stock_actual > 0;
    }).slice(0, 8);
  }

  addItemToTicket(item: InventoryValuationItem): void {
    if (!item || item.stock_actual <= 0) {
      this.errorMessage = `La prenda ${item.product_name || 'seleccionada'} no cuenta con stock disponible en esta sucursal.`;
      return;
    }

    const existing = this.ticketItems.find(i => i.variant_id === item.variant_id);
    if (existing) {
      if (existing.quantity + 1 > item.stock_actual) {
        this.errorMessage = `Límite de existencias alcanzado: Solo hay ${item.stock_actual} unidad(es) de esta prenda en esta sucursal.`;
        return;
      }
      existing.quantity += 1;
      existing.subtotal = Math.round(existing.quantity * existing.unit_price * 100) / 100;
    } else {
      this.ticketItems.push({
        variant_id: item.variant_id,
        product_name: item.product_name || 'Prenda',
        sku: item.sku || 'SKU',
        size: item.size_name || 'Única',
        color: item.color_name || 'Estándar',
        unit_price: Number(item.sale_price || 0),
        quantity: 1,
        subtotal: Number(item.sale_price || 0),
        stock_available: item.stock_actual
      });
    }
    this.searchQuery = '';
    this.searchResults = [];
    this.errorMessage = null;
    this.recalculateCash();
  }

  updateQuantity(item: PosItem, delta: number): void {
    item.quantity += delta;
    if (item.quantity <= 0) {
      this.ticketItems = this.ticketItems.filter(i => i.variant_id !== item.variant_id);
    } else {
      item.subtotal = Math.round(item.quantity * item.unit_price * 100) / 100;
    }
    this.recalculateCash();
  }

  removeItem(item: PosItem): void {
    this.ticketItems = this.ticketItems.filter(i => i.variant_id !== item.variant_id);
    this.recalculateCash();
  }

  clearTicket(): void {
    this.ticketItems = [];
    this.lastOrderSuccess = null;
    this.recalculateCash();
  }

  get ticketSubtotal(): number {
    return Math.round(this.ticketItems.reduce((acc, i) => acc + i.subtotal, 0) * 100) / 100;
  }

  get ticketTotal(): number {
    const total = Math.max(0, this.ticketSubtotal - this.discountAmount);
    return Math.round(total * 100) / 100;
  }

  get cashChange(): number {
    if (this.paymentType !== 'EFECTIVO') return 0;
    return Math.max(0, Math.round((this.cashReceived - this.ticketTotal) * 100) / 100);
  }

  recalculateCash(): void {
    if (this.cashReceived < this.ticketTotal) {
      this.cashReceived = this.ticketTotal;
    }
  }

  processSale(): void {
    if (!this.currentShift) {
      this.errorMessage = 'No hay una caja abierta en esta tienda. Para cobrar, primero debes abrir el turno indicando el fondo inicial con el que comienzas el día.';
      return;
    }
    if (this.ticketItems.length === 0) {
      this.errorMessage = 'El ticket de venta está vacío. Agrega al menos una prenda antes de confirmar el cobro.';
      return;
    }

    if (this.docType === 'FACTURA') {
      const nitClean = (this.customerNit || '').trim();
      const nameClean = (this.customerName || '').trim();
      if (!nitClean) {
        this.errorMessage = 'Por favor ingresa el NIT o C.I. del cliente para emitir su factura legal (o "0" para cliente casual).';
        return;
      }
      if (!nameClean) {
        this.errorMessage = 'Por favor escribe el nombre o la razón social del cliente para la factura.';
        return;
      }
    }

    if (this.paymentType === 'EFECTIVO' && this.cashReceived < this.ticketTotal) {
      const faltante = (this.ticketTotal - this.cashReceived).toFixed(2);
      this.errorMessage = `El efectivo recibido (Bs. ${Number(this.cashReceived).toFixed(2)}) no alcanza para cubrir el total (Bs. ${Number(this.ticketTotal).toFixed(2)}). Faltan cobrar Bs. ${faltante}.`;
      return;
    }

    if (this.paymentType === 'TARJETA') {
      const last4 = (this.cardLast4 || '').trim();
      if (!last4 || last4.length !== 4 || !/^\d{4}$/.test(last4)) {
        this.errorMessage = 'Por favor ingresa los últimos 4 dígitos de la tarjeta del cliente para el comprobante de pago.';
        return;
      }
    }

    this.errorMessage = null;
    this.loading = true;

    const payload: any = {
      channel: 'POS',
      branch_id: this.currentShift.branch_id,
      cash_shift_id: this.currentShift.id,
      payment_type: this.paymentType,
      doc_type: this.docType,
      customer_nit: this.customerNit,
      customer_name: this.customerName,
      coupon_code: this.couponCode ? this.couponCode.trim().toUpperCase() : undefined,
      pos_items: this.ticketItems.map(i => ({ variant_id: i.variant_id, quantity: i.quantity }))
    };

    if (this.paymentType === 'EFECTIVO') {
      payload.cash_payment = { cash_received: Number(this.cashReceived) };
    } else if (this.paymentType === 'TARJETA') {
      payload.card_payment = {
        card_brand: this.cardBrand,
        card_last4: this.cardLast4 ? this.cardLast4.slice(-4) : '0000'
      };
    } else if (this.paymentType === 'QR') {
      payload.qr_payment = { qr_reference: `QR-POS-${Date.now().toString().slice(-6)}` };
    }

    this.ventasService.processCheckout(payload).subscribe({
      next: (order) => {
        this.lastOrderSuccess = order;
        this.ticketItems = [];
        this.loading = false;
        if (this.selectedBranchId) {
          this.loadShiftForBranch(this.selectedBranchId);
          this.loadBranchInventory(this.selectedBranchId);
        }
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al procesar la venta en caja.';
        this.loading = false;
      }
    });
  }

  printReceipt(): void {
    window.print();
  }

  // --- MÉTODOS PARA ATENCIÓN Y COBRO DE RESERVAS DE PROBADOR VIRTUAL ---
  setTab(tab: 'POS' | 'RESERVAS' | 'ALISTADO'): void {
    this.activeTab = tab;
    this.errorMessage = null;
    if (tab === 'RESERVAS') {
      this.loadBranchReservations();
    } else if (tab === 'ALISTADO') {
      this.loadFulfillmentOrders();
    }
  }

  loadBranchReservations(): void {
    if (!this.selectedBranchId) return;
    this.loadingReservations = true;
    this.reservasService.getReservations(this.selectedBranchId).subscribe({
      next: (resList) => {
        // Filtrar reservas que están listas para atenderse o pendientes de liquidación
        this.branchReservations = resList.filter(r => r.status === 'READY' || r.status === 'PREPARING' || r.status === 'PENDING');
        this.loadingReservations = false;
      },
      error: () => {
        this.branchReservations = [];
        this.loadingReservations = false;
      }
    });
  }

  selectReservation(res: Reservation): void {
    this.selectedReservation = res;
    this.resCustomerName = res.customer_name || 'Cliente';
    this.resCustomerNit = '0';
    this.resSuccessMessage = null;
    this.resErrorMessage = null;
    this.reservationSelectedItems = {};
    if (res.items) {
      res.items.forEach(it => {
        this.reservationSelectedItems[it.id] = true;
      });
    }
  }

  toggleResItem(itemId: number): void {
    this.reservationSelectedItems[itemId] = !this.reservationSelectedItems[itemId];
  }

  isResItemSelected(itemId: number): boolean {
    return !!this.reservationSelectedItems[itemId];
  }

  get resSelectedItems(): ReservationItem[] {
    if (!this.selectedReservation || !this.selectedReservation.items) return [];
    return this.selectedReservation.items.filter(it => this.reservationSelectedItems[it.id]);
  }

  get resReturnedItems(): ReservationItem[] {
    if (!this.selectedReservation || !this.selectedReservation.items) return [];
    return this.selectedReservation.items.filter(it => !this.reservationSelectedItems[it.id]);
  }

  get resSelectedSubtotal(): number {
    return Math.round(this.resSelectedItems.reduce((acc, it) => acc + (it.unit_price * it.quantity), 0) * 100) / 100;
  }

  get resDepositCredited(): number {
    return Math.round(this.resSelectedSubtotal * 0.50 * 100) / 100;
  }

  get resBalanceToPay(): number {
    return Math.max(0, Math.round((this.resSelectedSubtotal - this.resDepositCredited) * 100) / 100);
  }

  get resChange(): number {
    if (this.resPaymentMethod !== 'EFECTIVO' || this.resCashReceived == null) return 0;
    return Math.max(0, Math.round((this.resCashReceived - this.resBalanceToPay) * 100) / 100);
  }

  checkoutReservation(): void {
    if (!this.currentShift) {
      this.resErrorMessage = 'Debes tener una caja abierta para realizar el cobro de la reserva.';
      return;
    }
    if (!this.selectedReservation) {
      this.resErrorMessage = 'No se ha seleccionado ninguna reserva.';
      return;
    }
    if (this.resPaymentMethod === 'EFECTIVO' && this.resCashReceived != null && this.resCashReceived < this.resBalanceToPay) {
      this.resErrorMessage = `El efectivo recibido no cubre el saldo de Bs. ${this.resBalanceToPay.toFixed(2)}.`;
      return;
    }
    if (this.resPaymentMethod === 'TARJETA' && this.resCardLast4 && !/^\d{4}$/.test(this.resCardLast4)) {
      this.resErrorMessage = 'Ingresa los 4 últimos dígitos de la tarjeta.';
      return;
    }
    const selectedIds = this.resSelectedItems.map(it => it.id);
    if (selectedIds.length === 0) {
      this.resErrorMessage = 'Debes seleccionar al menos una prenda que el cliente compre. Si rechaza todas, cancele la reserva para retornar todas las prendas al stock.';
      return;
    }

    this.resLoading = true;
    this.resErrorMessage = null;
    this.resSuccessMessage = null;

    this.reservasService.convertToPos(this.selectedReservation.id, {
      cash_shift_id: this.currentShift.id,
      payment_method: this.resPaymentMethod,
      cash_received: this.resPaymentMethod === 'EFECTIVO' ? this.resCashReceived : null,
      card_last4: this.resPaymentMethod === 'TARJETA' ? (this.resCardLast4 || null) : null,
      payment_reference: this.resPaymentMethod !== 'EFECTIVO' ? (this.resPaymentReference || null) : null,
      nit_ruc: this.resCustomerNit,
      business_name: this.resCustomerName,
      selected_item_ids: selectedIds
    }).subscribe({
      next: (completedRes) => {
        this.resLoading = false;
        const boughtCount = this.resSelectedItems.length;
        const returnedCount = this.resReturnedItems.length;
        this.resSuccessMessage = `¡Venta de reserva ${completedRes.reservation_code} cobrada exitosamente! Factura emitida. Prendas compradas: ${boughtCount}. Prendas devueltas al stock: ${returnedCount}.`;
        this.selectedReservation = null;
        if (this.selectedBranchId) {
          this.loadShiftForBranch(this.selectedBranchId);
          this.loadBranchInventory(this.selectedBranchId);
          this.loadBranchReservations();
        }
      },
      error: (err) => {
        this.resLoading = false;
        this.resErrorMessage = err?.error?.detail || 'Error al liquidar la reserva en caja.';
      }
    });
  }

  // --- MÉTODOS PARA ALISTADO Y DESPACHO DE PEDIDOS DE LA SUCURSAL ---
  loadFulfillmentOrders(): void {
    this.loadingFulfillment = true;
    this.fulfillmentSuccessMsg = null;
    this.fulfillmentErrorMsg = null;
    this.ventasService.getBranchFulfillmentOrders(this.fulfillmentStatusFilter || undefined).subscribe({
      next: (orders) => {
        this.fulfillmentOrders = orders;
        this.loadingFulfillment = false;
      },
      error: (err) => {
        this.fulfillmentErrorMsg = 'Error al cargar los pedidos de la sucursal.';
        this.loadingFulfillment = false;
      }
    });
  }

  updateOrderStatus(order: OrderResponse, newStatus: string): void {
    this.loading = true;
    this.fulfillmentSuccessMsg = null;
    this.fulfillmentErrorMsg = null;
    this.ventasService.updateOrderFulfillment(order.id, newStatus).subscribe({
      next: (updatedOrder) => {
        this.loading = false;
        this.fulfillmentSuccessMsg = `Pedido ${updatedOrder.order_number} actualizado a estado: ${updatedOrder.status}`;
        this.loadFulfillmentOrders();
      },
      error: (err) => {
        this.loading = false;
        this.fulfillmentErrorMsg = err?.error?.detail || 'Error al actualizar el estado del pedido.';
      }
    });
  }
}
