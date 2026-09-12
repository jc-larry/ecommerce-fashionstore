import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface CartItem {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
  sku: string;
  product_name: string;
  size: string;
  color: string;
  image_url?: string | null;
  stock_available: number;
}

export interface CartResponse {
  id: number;
  items: CartItem[];
  subtotal: number;
  items_count: number;
}

export interface PaymentResponse {
  id: number;
  payment_type: string;
  amount: number;
  status: string;
  paid_at: string;
  cash_received?: number | null;
  cash_change?: number | null;
  card_brand?: string | null;
  card_last4?: string | null;
  qr_reference?: string | null;
}

export interface InvoiceResponse {
  id: number;
  doc_type: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  control_code?: string | null;
  customer_nit?: string | null;
  customer_name?: string | null;
  issued_at: string;
  qr_payload: string;
}

export interface OrderItemResponse {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
  product_name: string;
  sku: string;
  size: string;
  color: string;
}

export interface OrderResponse {
  id: number;
  order_number: string;
  channel: string;
  status: string;
  subtotal: number;
  discount_amount: number;
  branch_id?: number;
  branch_name?: string;
  total_amount: number;
  created_at: string;
  items: OrderItemResponse[];
  payments: PaymentResponse[];
  invoice?: InvoiceResponse | null;
}

export interface CashShiftResponse {
  id: number;
  cashier_id: number;
  cashier_name: string;
  branch_id: number;
  branch_name: string;
  opening_amount: number;
  closing_amount_declared?: number | null;
  closing_amount_system?: number | null;
  difference?: number | null;
  status: string;
  opened_at: string;
  closed_at?: string | null;
  notes?: string | null;
  total_sales_count: number;
  total_cash_sales: number;
}

export interface QuotationResponse {
  id: number;
  quotation_number: string;
  customer_name: string;
  customer_email?: string | null;
  customer_phone?: string | null;
  total_amount: number;
  valid_until: string;
  status: string;
  created_at: string;
  items: OrderItemResponse[];
}

export interface OrderReturnResponse {
  id: number;
  return_number: string;
  order_id: number;
  return_type: string;
  reason?: string | null;
  refund_amount: number;
  status: string;
  created_at: string;
}

export interface CheckoutRequest {
  channel: 'ONLINE' | 'POS';
  branch_id: number;
  payment_type: 'EFECTIVO' | 'TARJETA' | 'QR' | 'CREDITO';
  doc_type: 'FACTURA' | 'NOTA_ENTREGA';
  customer_nit?: string;
  customer_name?: string;
  coupon_code?: string;
  cash_shift_id?: number;
  pos_items?: { variant_id: number; quantity: number }[];
  cash_payment?: { cash_received: number };
  card_payment?: { card_brand: string; card_last4: string; gateway_reference?: string };
  qr_payment?: { qr_reference?: string };
  credit_payment?: { credit_due_date?: string };
}

@Injectable({
  providedIn: 'root'
})
export class VentasService {
  private readonly baseUrl = `${environment.apiUrl}/sales`;

  constructor(private http: HttpClient) {}

  // CU17 — Carrito
  getCart(): Observable<CartResponse> {
    return this.http.get<CartResponse>(`${this.baseUrl}/cart`);
  }

  addToCart(variantId: number, quantity: number = 1): Observable<CartResponse> {
    return this.http.post<CartResponse>(`${this.baseUrl}/cart/items`, {
      variant_id: variantId,
      quantity
    });
  }

  updateCartItem(itemId: number, quantity: number): Observable<CartResponse> {
    return this.http.put<CartResponse>(`${this.baseUrl}/cart/items/${itemId}`, { quantity });
  }

  removeCartItem(itemId: number): Observable<CartResponse> {
    return this.http.delete<CartResponse>(`${this.baseUrl}/cart/items/${itemId}`);
  }

  clearCart(): Observable<CartResponse> {
    return this.http.delete<CartResponse>(`${this.baseUrl}/cart/clear`);
  }

  // CU18, CU19, CU20 — Checkout Polimórfico y POS
  processCheckout(payload: CheckoutRequest): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(`${this.baseUrl}/checkout`, payload);
  }

  // CU24 — Historial de pedidos
  getMyOrders(): Observable<OrderResponse[]> {
    return this.http.get<OrderResponse[]>(`${this.baseUrl}/orders/my-orders`);
  }

  getOrderById(id: number): Observable<OrderResponse> {
    return this.http.get<OrderResponse>(`${this.baseUrl}/orders/${id}`);
  }

  // CU23 — Turno de caja y Arqueo
  getCurrentShift(branchId?: number): Observable<CashShiftResponse | null> {
    const url = branchId ? `${this.baseUrl}/shifts/current?branch_id=${branchId}` : `${this.baseUrl}/shifts/current`;
    return this.http.get<CashShiftResponse | null>(url);
  }

  getCashShifts(branchId?: number, status?: string): Observable<CashShiftResponse[]> {
    const params: string[] = [];
    if (branchId) params.push(`branch_id=${branchId}`);
    if (status) params.push(`status=${status}`);
    const query = params.length > 0 ? `?${params.join('&')}` : '';
    return this.http.get<CashShiftResponse[]>(`${this.baseUrl}/shifts${query}`);
  }

  openShift(branchId: number, openingAmount: number): Observable<CashShiftResponse> {
    return this.http.post<CashShiftResponse>(`${this.baseUrl}/shifts/open`, {
      branch_id: branchId,
      opening_amount: openingAmount
    });
  }

  closeShift(shiftId: number, closingAmountDeclared: number, notes?: string): Observable<CashShiftResponse> {
    return this.http.post<CashShiftResponse>(`${this.baseUrl}/shifts/${shiftId}/close`, {
      closing_amount_declared: closingAmountDeclared,
      notes
    });
  }

  // CU21 — Cotizaciones
  createQuotation(payload: {
    customer_name: string;
    customer_email?: string;
    customer_phone?: string;
    valid_days: number;
    details: { variant_id: number; quantity: number }[];
  }): Observable<QuotationResponse> {
    return this.http.post<QuotationResponse>(`${this.baseUrl}/quotations`, payload);
  }

  getQuotations(): Observable<QuotationResponse[]> {
    return this.http.get<QuotationResponse[]>(`${this.baseUrl}/quotations`);
  }

  convertQuotationToOrder(quotationId: number, payload: {
    branch_id: number;
    cash_shift_id?: number | null;
    payment_method: string;
    customer_nit?: string;
    customer_business_name?: string;
  }): Observable<OrderResponse> {
    return this.http.post<OrderResponse>(`${this.baseUrl}/quotations/${quotationId}/convert`, payload);
  }

  // CU22 — Devoluciones y cambios
  processReturn(payload: {
    order_id: number;
    return_type: 'DEVOLUCION_DINERO' | 'CAMBIO_PRENDA';
    reason?: string;
    items: { variant_id: number; quantity: number; replacement_variant_id?: number }[];
  }): Observable<OrderReturnResponse> {
    return this.http.post<OrderReturnResponse>(`${this.baseUrl}/returns`, payload);
  }
}
