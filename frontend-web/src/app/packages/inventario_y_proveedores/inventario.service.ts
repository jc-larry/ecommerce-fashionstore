import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * [CU08 / CU10] Proveedores, ingreso de mercadería e inventario.
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
}
