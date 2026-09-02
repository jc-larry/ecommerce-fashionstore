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

  // ---------- MERCADERÍA / INGRESOS (CU10) ----------
  registerIntake(intake: any): Observable<any> {
    return this.http.post<any>(`${this.api}/merchandise/intake`, intake);
  }

  getInventory(branchId?: number): Observable<any[]> {
    const query = branchId ? `?branch_id=${branchId}` : '';
    return this.http.get<any[]>(`${this.api}/merchandise/inventory${query}`);
  }

  getLedger(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/merchandise/ledger`);
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
}

export interface InventoryValuationItem {
  branch_id: number;
  variant_id: number;
  sku: string | null;
  product_name: string | null;
  stock_actual: number;
  avg_cost: number;
  valor: number;
}

export interface InventoryValuation {
  branch_id: number | null;
  capital_invertido: number;
  items: InventoryValuationItem[];
}

export interface InventoryAdjustment {
  branch_id: number;
  variant_id: number;
  quantity: number;
  reason: 'MERMA' | 'DANO' | 'PERDIDA' | 'CONTEO';
  note?: string;
}
