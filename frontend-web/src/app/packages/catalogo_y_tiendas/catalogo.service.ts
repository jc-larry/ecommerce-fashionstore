import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

// ---------- Tipos del catálogo ----------
export interface Category {
  id: number;
  name: string;
  description?: string | null;
  image_url?: string | null;
  parent_id?: number | null;
}
export interface ColorRef { id: number; name: string; hex_code: string; }
export interface SizeRef { id: number; name: string; category_type?: string | null; }
export interface ProductVariant {
  id: number;
  color_id: number;
  size_id: number;
  sku: string;
  is_active: boolean;
  color: ColorRef;
  size: SizeRef;
}
export interface ProductImage {
  id: number;
  image_url: string;
  color_id?: number | null;
  is_primary: boolean;
}
export interface Product {
  id: number;
  name: string;
  description?: string | null;
  base_price: number;
  compare_at_price?: number | null;
  discount_percent: number;
  rating_avg: number;
  rating_count: number;
  category_id: number;
  season_id?: number | null;
  is_active: boolean;
  material?: string | null;
  neck_type?: string | null;
  sleeve_length?: string | null;
  tags?: string | null;
  category?: Category;
  variants: ProductVariant[];
  images: ProductImage[];
}
export interface Review {
  id: number;
  rating: number;
  comment?: string | null;
  author_name: string;
  is_mine: boolean;
  created_at: string;
}
export interface ProductReviews {
  summary: { average: number; count: number };
  items: Review[];
}
export interface RatingSummaryItem { product_id: number; average: number; count: number; }

/**
 * [CU06 / CU07 / CU09 / CU11 / CU14] Sucursales, catálogo de prendas, tienda del cliente,
 * reseñas y favoritos.
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

  // ---------- CATÁLOGO DE PRENDAS (CU07 / CU11) ----------
  getProducts(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.api}/catalog/products`);
  }

  getProduct(id: number): Observable<Product> {
    return this.http.get<Product>(`${this.api}/catalog/products/${id}`);
  }

  createProduct(product: any): Observable<Product> {
    return this.http.post<Product>(`${this.api}/catalog/products`, product);
  }

  updateProduct(id: number, product: any): Observable<Product> {
    return this.http.put<Product>(`${this.api}/catalog/products/${id}`, product);
  }

  deactivateProduct(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/products/${id}`);
  }

  // ---------- RESEÑAS Y CALIFICACIONES (CU14) ----------
  getReviews(productId: number): Observable<ProductReviews> {
    return this.http.get<ProductReviews>(`${this.api}/catalog/products/${productId}/reviews`);
  }

  submitReview(productId: number, body: { rating: number; comment?: string }): Observable<Review> {
    return this.http.post<Review>(`${this.api}/catalog/products/${productId}/reviews`, body);
  }

  getRatingsSummary(): Observable<RatingSummaryItem[]> {
    return this.http.get<RatingSummaryItem[]>(`${this.api}/catalog/ratings-summary`);
  }

  // ---------- FAVORITOS / WISHLIST (CU14) ----------
  getWishlist(): Observable<Product[]> {
    return this.http.get<Product[]>(`${this.api}/catalog/wishlist`);
  }

  addWishlist(productId: number): Observable<{ product_id: number; in_wishlist: boolean }> {
    return this.http.post<{ product_id: number; in_wishlist: boolean }>(
      `${this.api}/catalog/wishlist/${productId}`, {}
    );
  }

  removeWishlist(productId: number): Observable<{ product_id: number; in_wishlist: boolean }> {
    return this.http.delete<{ product_id: number; in_wishlist: boolean }>(
      `${this.api}/catalog/wishlist/${productId}`
    );
  }

  // ---------- PARÁMETROS DEL CATÁLOGO ----------
  getCategories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.api}/catalog/categories`);
  }
  createCategory(data: any): Observable<Category> {
    return this.http.post<Category>(`${this.api}/catalog/categories`, data);
  }
  updateCategory(id: number, data: any): Observable<Category> {
    return this.http.put<Category>(`${this.api}/catalog/categories/${id}`, data);
  }
  deleteCategory(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/categories/${id}`);
  }

  getColors(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/colors`);
  }
  createColor(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/colors`, data);
  }
  deleteColor(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/colors/${id}`);
  }

  getSizes(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/sizes`);
  }
  createSize(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/sizes`, data);
  }
  deleteSize(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/sizes/${id}`);
  }

  getSeasons(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/catalog/seasons`);
  }
  createSeason(data: any): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/seasons`, data);
  }

  // ---------- SUBIDA Y RESOLUCIÓN DE IMÁGENES ----------
  uploadImage(file: File): Observable<{ image_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ image_url: string }>(`${this.api}/catalog/upload-image`, formData);
  }

  resolveImageUrl(url?: string | null): string {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
      return url;
    }
    const base = this.api.replace(/\/api\/v1\/?$/, '');
    return `${base}${url.startsWith('/') ? '' : '/'}${url}`;
  }
}
