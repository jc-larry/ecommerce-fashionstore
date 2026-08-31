import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * [CU06 / CU07 / CU09] Sucursales, catálogo de prendas y asignación de empleados.
 */
@Injectable({ providedIn: 'root' })
export class CatalogoService {
  private readonly api = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ---------- SUCURSALES (CU06) ----------
  getBranches(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/branches`);
  }

  createBranch(branch: any): Observable<any> {
    return this.http.post<any>(`${this.api}/branches`, branch);
  }

  updateBranch(id: number, branch: any): Observable<any> {
    return this.http.put<any>(`${this.api}/branches/${id}`, branch);
  }

  deactivateBranch(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/branches/${id}`);
  }

  // ---------- EMPLEADOS DE SUCURSAL (CU09) ----------
  assignEmployee(branchId: number, userId: number): Observable<any> {
    return this.http.post<any>(`${this.api}/branches/${branchId}/employees`, { user_id: userId });
  }

  removeEmployee(branchId: number, userId: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/branches/${branchId}/employees/${userId}`);
  }

  // ---------- CATÁLOGO DE PRENDAS (CU07) ----------
  getProducts(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/products`);
  }

  createProduct(product: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/products`, product);
  }

  updateProduct(id: number, product: any): Observable<any> {
    return this.http.put<any>(`${this.api}/catalog/products/${id}`, product);
  }

  deactivateProduct(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/products/${id}`);
  }

  // ---------- PARÁMETROS DEL CATÁLOGO ----------
  getCategories(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/categories`);
  }
  createCategory(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/categories`, data);
  }

  getColors(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/colors`);
  }
  createColor(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/colors`, data);
  }

  getSizes(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/sizes`);
  }
  createSize(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/sizes`, data);
  }

  getSeasons(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/seasons`);
  }
  createSeason(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/seasons`, data);
  }
}
