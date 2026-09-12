import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * [CU08 / CU10 / CU37 / CU38] Proveedores, ingreso de mercadería, inventario,
 * valoración (capital invertido) y ajustes (mermas).
 */
@Injectable({ providedIn: 'root' })
export class InventarioService {
  private readonly api = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ---------- PROVEEDORES (CU08) ----------
  getSuppliers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/suppliers`);
  }

  createSupplier(supplier: any): Observable<any> {
    return this.http.post<any>(`${this.api}/suppliers`, supplier);
  }

  updateSupplier(id: number, supplier: any): Observable<any> {
    return this.http.put<any>(`${this.api}/suppliers/${id}`, supplier);
  }

  deleteSupplier(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/suppliers/${id}`);
  }

  toggleSupplier(id: number): Observable<any> {
    return this.http.patch<any>(`${this.api}/suppliers/${id}/toggle`, {});
  }

  // ---------- MERCADERÍA / INGRESOS (CU10) ----------
  registerIntake(intake: any): Observable<any> {
    return this.http.post<any>(`${this.api}/merchandise/intake`, intake);
  }

  getInventory(branchId?: number): Observable<any[]> {
    const query = branchId ? `?branch_id=${branchId}` : '';
    return this.http.get<any[]>(`${this.api}/merchandise/inventory${query}`);
  }

  getLedger(branchId?: number): Observable<any[]> {
    const query = branchId ? `?branch_id=${branchId}` : '';
    return this.http.get<any[]>(`${this.api}/merchandise/ledger${query}`);
  }

  // ---------- VALORACIÓN DE INVENTARIO / CAPITAL INVERTIDO (CU37) ----------
  getValuation(branchId?: number): Observable<InventoryValuation> {
    const query = branchId ? `?branch_id=${branchId}` : '';
    return this.http.get<InventoryValuation>(`${this.api}/merchandise/valuation${query}`);
  }

  // ---------- AJUSTES DE INVENTARIO / MERMAS (CU38) ----------
  createAdjustment(payload: InventoryAdjustment): Observable<any> {
    return this.http.post<any>(`${this.api}/merchandise/adjustments`, payload);
  }

  // ---------- TRANSFERENCIAS ENTRE SUCURSALES (CU15) ----------
  getTransfers(branchId?: number, statusFilter?: string): Observable<StockTransfer[]> {
    const params: any = {};
    if (branchId) params.branch_id = branchId;
    if (statusFilter) params.status_filter = statusFilter;
    return this.http.get<StockTransfer[]>(`${this.api}/merchandise/transfers`, { params });
  }

  createTransfer(payload: StockTransferCreate): Observable<StockTransfer> {
    return this.http.post<StockTransfer>(`${this.api}/merchandise/transfers`, payload);
  }

  updateTransferStatus(transferId: number, status: string, notes?: string): Observable<StockTransfer> {
    return this.http.put<StockTransfer>(`${this.api}/merchandise/transfers/${transferId}/status`, { status, notes });
  }

  // ---------- ALERTAS Y UMBRALES DE STOCK (CU16) ----------
  getStockAlerts(branchId?: number): Observable<StockAlertItem[]> {
    const params: any = {};
    if (branchId) params.branch_id = branchId;
    return this.http.get<StockAlertItem[]>(`${this.api}/merchandise/inventory/alerts`, { params });
  }

  updateStockThresholds(branchId: number, variantId: number, stockMin: number, stockMax: number): Observable<any> {
    return this.http.put<any>(`${this.api}/merchandise/inventory/thresholds/${branchId}/${variantId}`, {
      stock_minimo: stockMin,
      stock_maximo: stockMax,
    });
  }
}

export interface InventoryValuationItem {
  branch_id: number;
  branch_name?: string | null;
  variant_id: number;
  sku: string | null;
  product_name: string | null;
  image_url?: string | null;
  color_name?: string | null;
  color_hex?: string | null;
  size_name?: string | null;
  stock_actual: number;
  avg_cost: number;
  valor: number;
  sale_price: number;
  valor_venta: number;
  margen_bruto_unit: number;
  margen_bruto_percent: number;
}

export interface InventoryValuation {
  branch_id: number | null;
  capital_invertido: number;
  total_valor_venta: number;
  utilidad_bruta_proyectada: number;
  margen_bruto_promedio_percent: number;
  total_unidades: number;
  items: InventoryValuationItem[];
}

export interface InventoryAdjustment {
  branch_id: number;
  variant_id: number;
  quantity: number;
  reason: string;
  note?: string;
}

export interface InventoryAdjustmentResponse {
  id: number;
  branch_id: number;
  variant_id: number;
  quantity: number;
  financial_impact: number;
  reason: string;
  reason_label: string;
  note?: string | null;
  created_at: string;
}

export interface PurchaseDetailCreate {
  variant_id: number;
  quantity: number;
  unit_cost: number;
}

export interface PurchaseOrderCreate {
  branch_id: number;
  supplier_id: number;
  invoice_number?: string;
  shipping_cost?: number;
  notes?: string;
  details: PurchaseDetailCreate[];
}

// ---------- Interfaces CU15 ----------
export interface StockTransferDetail {
  id: number;
  variant_id: number;
  quantity: number;
  sku?: string | null;
  product_name?: string | null;
  size?: string | null;
  color?: string | null;
}

export interface StockTransfer {
  id: number;
  transfer_number: string;
  origin_branch_id: number;
  origin_branch_name: string;
  destination_branch_id: number;
  destination_branch_name: string;
  status: 'SOLICITADA' | 'EN_TRANSITO' | 'COMPLETADA' | 'CANCELADA';
  notes?: string | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  details: StockTransferDetail[];
}

export interface StockTransferCreate {
  origin_branch_id: number;
  destination_branch_id: number;
  notes?: string;
  details: { variant_id: number; quantity: number }[];
}

// ---------- Interfaces CU16 ----------
export interface StockAlertItem {
  branch_id: number;
  branch_name: string;
  variant_id: number;
  product_name: string;
  sku: string;
  size: string;
  color: string;
  stock_actual: number;
  stock_minimo: number;
  stock_maximo: number;
  alert_type: 'QUIEBRE_STOCK' | 'SOBRESTOCK';
}
