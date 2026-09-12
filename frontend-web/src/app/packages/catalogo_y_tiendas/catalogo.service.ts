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
  price_override?: number | null;
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
export interface ReviewSummary { average: number; count: number; }
export interface ProductReviews {
  summary: ReviewSummary;
  items: Review[];
}
export interface RatingSummaryItem { product_id: number; average: number; count: number; }

export interface BranchOption {
  id: number;
  name: string;
  code?: string | null;
  city?: string | null;
  is_active?: boolean;
  is_temporarily_closed?: boolean;
  closure_reason?: string | null;
  opening_time?: string | null;
  closing_time?: string | null;
  days_open?: string | null;
  has_fitting_room?: boolean;
  pickup_enabled?: boolean;
}

export interface CatalogFilterOptions {
  min_price: number;
  max_price: number;
  categories: Category[];
  sizes: SizeRef[];
  colors: ColorRef[];
  seasons: any[];
  branches: BranchOption[];
}

export interface ProductSearchParams {
  q?: string;
  category_id?: number;
  season_id?: number;
  min_price?: number;
  max_price?: number;
  size_id?: number;
  color_id?: number;
  branch_id?: number;
  in_stock_only?: boolean;
  sort_by?: string;
  page?: number;
  limit?: number;
}

export interface ProductSearchResultItem extends Product {
  branch_stock?: number | null;
  total_stock: number;
}

export interface ProductSearchResponse {
  items: ProductSearchResultItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface BranchStockDetail {
  branch_id: number;
  branch_name: string;
  branch_code?: string | null;
  city?: string | null;
  stock: number;
}

export interface VariantBranchStock {
  variant_id: number;
  sku: string;
  color_id: number;
  color_name: string;
  color_hex: string;
  size_id: number;
  size_name: string;
  branches: BranchStockDetail[];
  total_stock: number;
}

export interface ProductAvailabilityResponse {
  product_id: number;
  product_name: string;
  variants: VariantBranchStock[];
  total_stock: number;
}

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

  toggleBranchClosure(id: number, isTemporarilyClosed: boolean, reason?: string): Observable<any> {
    return this.http.patch<any>(`${this.api}/branches/${id}/toggle-closure`, {
      is_temporarily_closed: isTemporarilyClosed,
      closure_reason: reason || null
    });
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

  // ---------- BÚSQUEDA Y DISPONIBILIDAD POR SUCURSAL (CU12) ----------
  getFilterOptions(): Observable<CatalogFilterOptions> {
    return this.http.get<CatalogFilterOptions>(`${this.api}/catalog/filter-options`);
  }

  searchProducts(params: ProductSearchParams): Observable<ProductSearchResponse> {
    const qParts: string[] = [];
    if (params.q) qParts.push(`q=${encodeURIComponent(params.q)}`);
    if (params.category_id) qParts.push(`category_id=${params.category_id}`);
    if (params.season_id) qParts.push(`season_id=${params.season_id}`);
    if (params.min_price !== undefined && params.min_price !== null) qParts.push(`min_price=${params.min_price}`);
    if (params.max_price !== undefined && params.max_price !== null) qParts.push(`max_price=${params.max_price}`);
    if (params.size_id) qParts.push(`size_id=${params.size_id}`);
    if (params.color_id) qParts.push(`color_id=${params.color_id}`);
    if (params.branch_id) qParts.push(`branch_id=${params.branch_id}`);
    if (params.in_stock_only) qParts.push(`in_stock_only=true`);
    if (params.sort_by) qParts.push(`sort_by=${params.sort_by}`);
    if (params.page) qParts.push(`page=${params.page}`);
    if (params.limit) qParts.push(`limit=${params.limit}`);
    const query = qParts.length > 0 ? '?' + qParts.join('&') : '';

    return this.http.get<ProductSearchResponse>(`${this.api}/catalog/products/search${query}`);
  }

  getProductBranchAvailability(productId: number): Observable<ProductAvailabilityResponse> {
    return this.http.get<ProductAvailabilityResponse>(
      `${this.api}/catalog/products/${productId}/branch-availability`
    );
  }

  // ---------- CUPONES Y PROMOCIONES (CU13) ----------
  getCoupons(): Observable<Coupon[]> {
    return this.http.get<Coupon[]>(`${this.api}/catalog/coupons`);
  }

  createCoupon(data: any): Observable<Coupon> {
    return this.http.post<Coupon>(`${this.api}/catalog/coupons`, data);
  }

  updateCoupon(id: number, data: any): Observable<Coupon> {
    return this.http.put<Coupon>(`${this.api}/catalog/coupons/${id}`, data);
  }

  deleteCoupon(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/coupons/${id}`);
  }

  validateCoupon(code: string, cartTotal: number): Observable<CouponValidateResponse> {
    return this.http.post<CouponValidateResponse>(`${this.api}/catalog/coupons/validate`, {
      code,
      cart_total: cartTotal,
    });
  }

  getPromotions(): Observable<SeasonalPromotion[]> {
    return this.http.get<SeasonalPromotion[]>(`${this.api}/catalog/promotions`);
  }

  createPromotion(data: any): Observable<SeasonalPromotion> {
    return this.http.post<SeasonalPromotion>(`${this.api}/catalog/promotions`, data);
  }

  updatePromotion(id: number, data: any): Observable<SeasonalPromotion> {
    return this.http.put<SeasonalPromotion>(`${this.api}/catalog/promotions/${id}`, data);
  }

  deletePromotion(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/promotions/${id}`);
  }

  // ---------- CU14+ Moderación de Reseñas ----------
  getAdminReviews(statusFilter?: string): Observable<ReviewModerationItem[]> {
    const params: any = {};
    if (statusFilter) params.status_filter = statusFilter;
    return this.http.get<ReviewModerationItem[]>(`${this.api}/catalog/admin/reviews`, { params });
  }

  moderateReview(reviewId: number, status: 'APPROVED' | 'REJECTED'): Observable<ReviewModerationItem> {
    return this.http.put<ReviewModerationItem>(`${this.api}/catalog/admin/reviews/${reviewId}/moderate`, { status });
  }

  // ---------- CU14+ Wishlists Múltiples y Compartibles ----------
  getUserWishlists(): Observable<Wishlist[]> {
    return this.http.get<Wishlist[]>(`${this.api}/catalog/wishlists`);
  }

  createWishlist(data: { name: string; is_public?: boolean }): Observable<Wishlist> {
    return this.http.post<Wishlist>(`${this.api}/catalog/wishlists`, data);
  }

  updateWishlist(id: number, data: { name?: string; is_public?: boolean }): Observable<Wishlist> {
    return this.http.put<Wishlist>(`${this.api}/catalog/wishlists/${id}`, data);
  }

  deleteWishlist(id: number): Observable<void> {
    return this.http.delete<void>(`${this.api}/catalog/wishlists/${id}`);
  }

  getWishlistDetail(id: number): Observable<WishlistDetail> {
    return this.http.get<WishlistDetail>(`${this.api}/catalog/wishlists/${id}`);
  }

  addItemToWishlist(wishlistId: number, productId: number): Observable<any> {
    return this.http.post<any>(`${this.api}/catalog/wishlists/${wishlistId}/items/${productId}`, {});
  }

  removeItemFromWishlist(wishlistId: number, productId: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/catalog/wishlists/${wishlistId}/items/${productId}`);
  }

  getSharedWishlist(shareToken: string): Observable<WishlistDetail> {
    return this.http.get<WishlistDetail>(`${this.api}/catalog/wishlists/shared/${shareToken}`);
  }
}

// ---------- Interfaces de CU13 ----------
export interface Coupon {
  id: number;
  code: string;
  discount_type: 'PORCENTAJE' | 'MONTO_FIJO';
  discount_value: number;
  min_purchase_amount: number;
  valid_from: string;
  valid_until: string;
  max_uses: number;
  used_count: number;
  is_active: boolean;
  created_at: string;
}

export interface CouponValidateResponse {
  valid: boolean;
  code: string;
  discount_type: string;
  discount_value: number;
  discount_amount: number;
  new_total: number;
  message: string;
}

export interface SeasonalPromotion {
  id: number;
  name: string;
  description?: string | null;
  discount_percent: number;
  category_id?: number | null;
  start_date: string;
  end_date: string;
  is_active: boolean;
  created_at: string;
  category?: Category;
}

// ---------- Interfaces de CU14+ ----------
export interface ReviewModerationItem {
  id: number;
  product_id: number;
  product_name: string;
  user_id: number;
  author_name: string;
  author_email: string;
  rating: number;
  comment?: string | null;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
}

export interface Wishlist {
  id: number;
  name: string;
  is_public: boolean;
  share_token: string;
  created_at: string;
  items_count: number;
}

export interface WishlistDetail {
  id: number;
  name: string;
  is_public: boolean;
  share_token: string;
  created_at: string;
  owner_name?: string | null;
  products: Product[];
}
