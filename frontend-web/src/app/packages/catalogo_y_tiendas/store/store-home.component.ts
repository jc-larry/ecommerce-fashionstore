import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, of, forkJoin } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, catchError } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import {
  CatalogoService,
  Product,
  Category,
  BranchOption,
  CatalogFilterOptions,
  ProductSearchResultItem,
  ProductSearchParams,
} from '../catalogo.service';

import { BranchContextService } from '../branches/branch-context.service';

/**
 * [CU11 / CU12] Tienda del cliente (web): navegación, búsqueda y filtros facetados avanzados
 * (precio, talla, color, ocasión) + disponibilidad por sucursal física.
 */
@Component({
  selector: 'app-store-home',
  templateUrl: './store-home.component.html',
  styleUrls: ['./store-home.component.css'],
})
export class StoreHomeComponent implements OnInit {
  products: ProductSearchResultItem[] = [];
  categories: Category[] = [];
  branches: BranchOption[] = [];
  sizes: any[] = [];
  colors: any[] = [];
  loading = true;

  // Filtros CU12
  search = '';
  categoryFilter: number | 'TODAS' = 'TODAS';
  mainCategories: Category[] = [];
  selectedMainCategoryId: number | 'TODAS' = 'TODAS';
  selectedSubcategoryId: number | null = null;
  branchFilter: number | null = null;
  sizeFilter: number | null = null;
  colorFilter: number | null = null;
  minPrice: number | null = null;
  maxPrice: number | null = null;
  catalogMinPrice = 0;
  catalogMaxPrice = 1000;
  inStockOnly = false;
  sortBy: string = 'newest';
  showFilters = false;
  isCartOpen = false;
  readonly downloadApkUrl = `${environment.apiUrl}/download-apk`;

  private searchSubject = new Subject<string>();
  private ratings = new Map<number, { average: number; count: number }>();
  private wishlistIds = new Set<number>();

  constructor(
    public auth: AuthService,
    private catalogo: CatalogoService,
    private router: Router,
    public branchContext: BranchContextService
  ) {}

  get userName(): string {
    const u = this.auth.getCurrentUser();
    return u ? u.first_name : 'Cliente';
  }

  get selectedBranchName(): string | null {
    if (!this.branchFilter) return null;
    return this.branches.find((b) => b.id === this.branchFilter)?.name || null;
  }

  get activeFiltersCount(): number {
    let count = 0;
    if (this.branchFilter) count++;
    if (this.sizeFilter) count++;
    if (this.colorFilter) count++;
    if (this.minPrice !== null && this.minPrice > this.catalogMinPrice) count++;
    if (this.maxPrice !== null && this.maxPrice < this.catalogMaxPrice) count++;
    if (this.inStockOnly) count++;
    if (this.sortBy !== 'newest') count++;
    return count;
  }

  get currentSubcategories(): Category[] {
    if (this.selectedMainCategoryId === 'TODAS') return [];
    return this.categories.filter((c) => c.parent_id === this.selectedMainCategoryId);
  }

  subcategoriesOf(parentId: number): Category[] {
    return this.categories.filter((c) => c.parent_id === parentId);
  }

  ngOnInit(): void {
    // 1. Cargar opciones dinámicas de filtro y favoritos
    forkJoin({
      options: this.catalogo.getFilterOptions().pipe(catchError(() => of(null))),
      ratings: this.catalogo.getRatingsSummary().pipe(catchError(() => of([]))),
      wishlist: this.auth.isLoggedIn()
        ? this.catalogo.getWishlist().pipe(catchError(() => of([] as Product[])))
        : of([] as Product[]),
    }).subscribe(({ options, ratings, wishlist }) => {
      if (options) {
        this.categories = options.categories || [];
        this.mainCategories = this.categories.filter((c) => !c.parent_id);
        this.branches = options.branches || [];
        this.sizes = options.sizes || [];
        this.colors = options.colors || [];
        this.catalogMinPrice = options.min_price;
        this.catalogMaxPrice = options.max_price;
      }
      for (const r of ratings || []) this.ratings.set(r.product_id, { average: r.average, count: r.count });
      this.wishlistIds = new Set((wishlist || []).map((p) => p.id));
      this.fetchFilteredProducts();
    });

    // 2. Debounce en búsqueda por texto
    this.searchSubject
      .pipe(debounceTime(300), distinctUntilChanged())
      .subscribe(() => {
        this.fetchFilteredProducts();
      });

    // 3. Sincronización con la sucursal activa seleccionada
    this.branchContext.activeBranch$.subscribe((active) => {
      this.branchFilter = active ? active.id : null;
      this.fetchFilteredProducts();
    });
  }

  onSearchChange(val: string): void {
    this.searchSubject.next(val);
  }

  fetchFilteredProducts(): void {
    this.loading = true;
    const params: ProductSearchParams = {
      q: this.search.trim() || undefined,
      category_id: this.categoryFilter !== 'TODAS' ? this.categoryFilter : undefined,
      branch_id: this.branchFilter || undefined,
      size_id: this.sizeFilter || undefined,
      color_id: this.colorFilter || undefined,
      min_price: this.minPrice !== null ? this.minPrice : undefined,
      max_price: this.maxPrice !== null ? this.maxPrice : undefined,
      in_stock_only: this.inStockOnly,
      sort_by: this.sortBy,
      page: 1,
      limit: 50,
    };

    this.catalogo.searchProducts(params).subscribe({
      next: (res) => {
        this.products = res.items || [];
        this.loading = false;
      },
      error: () => {
        this.products = [];
        this.loading = false;
      },
    });
  }

  get activeCategoryName(): string {
    if (this.selectedSubcategoryId) {
      const sub = this.categories.find((c) => c.id === this.selectedSubcategoryId);
      const parent = this.categories.find((c) => c.id === this.selectedMainCategoryId);
      return parent ? `${parent.name} › ${sub?.name}` : (sub?.name || '');
    }
    if (this.selectedMainCategoryId !== 'TODAS') {
      return this.categories.find((c) => c.id === this.selectedMainCategoryId)?.name || '';
    }
    return '';
  }

  selectMainCategory(id: number | 'TODAS'): void {
    this.selectedMainCategoryId = id;
    this.selectedSubcategoryId = null;
    this.categoryFilter = id;
    this.fetchFilteredProducts();
  }

  selectSubcategory(id: number | null): void {
    this.selectedSubcategoryId = id;
    if (id !== null) {
      this.categoryFilter = id;
    } else {
      this.categoryFilter = this.selectedMainCategoryId;
    }
    this.fetchFilteredProducts();
  }

  selectCategory(id: number | 'TODAS'): void {
    this.selectMainCategory(id);
  }

  toggleSize(sizeId: number): void {
    this.sizeFilter = this.sizeFilter === sizeId ? null : sizeId;
    this.fetchFilteredProducts();
  }

  toggleColor(colorId: number): void {
    this.colorFilter = this.colorFilter === colorId ? null : colorId;
    this.fetchFilteredProducts();
  }

  selectBranch(branchId: number | null): void {
    this.branchFilter = branchId;
    this.fetchFilteredProducts();
  }

  resetFilters(): void {
    this.search = '';
    this.selectedMainCategoryId = 'TODAS';
    this.selectedSubcategoryId = null;
    this.categoryFilter = 'TODAS';
    this.branchFilter = null;
    this.sizeFilter = null;
    this.colorFilter = null;
    this.minPrice = null;
    this.maxPrice = null;
    this.inStockOnly = false;
    this.sortBy = 'newest';
    this.fetchFilteredProducts();
  }

  categoryImg(c: Category): string | null {
    return c.image_url ? this.catalogo.resolveImageUrl(c.image_url) : null;
  }

  categoryName(p: Product): string {
    const cat = p.category || this.categories.find((c) => c.id === p.category_id);
    if (!cat) return '';
    if (cat.parent_id) {
      const parent = this.categories.find((c) => c.id === cat.parent_id);
      return parent ? `${parent.name} › ${cat.name}` : cat.name;
    }
    return cat.name;
  }

  primaryImage(p: Product): string | null {
    const img = (p.images || []).find((i) => i.is_primary) || (p.images || [])[0];
    return img?.image_url ? this.catalogo.resolveImageUrl(img.image_url) : null;
  }

  colorDots(p: Product): string[] {
    const seen = new Set<number>();
    const hexes: string[] = [];
    for (const v of p.variants || []) {
      if (v.color && !seen.has(v.color.id)) {
        seen.add(v.color.id);
        hexes.push(v.color.hex_code);
      }
    }
    return hexes.slice(0, 4);
  }

  sizeLabels(p: Product): string[] {
    const order = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
    const set = new Set<string>();
    for (const v of p.variants || []) if (v.is_active) set.add(v.size.name.toUpperCase());
    return [...set].sort((a, b) => {
      const ia = order.indexOf(a),
        ib = order.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  }

  rating(p: Product): { average: number; count: number } {
    return this.ratings.get(p.id) || { average: p.rating_avg || 0, count: p.rating_count || 0 };
  }

  isWished(p: Product): boolean {
    return this.wishlistIds.has(p.id);
  }

  toggleWishlist(p: Product, ev: Event): void {
    ev.stopPropagation();
    ev.preventDefault();
    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }
    const wished = this.isWished(p);
    const obs = wished ? this.catalogo.removeWishlist(p.id) : this.catalogo.addWishlist(p.id);
    obs.subscribe({
      next: () => {
        if (wished) this.wishlistIds.delete(p.id);
        else this.wishlistIds.add(p.id);
      },
      error: () => {},
    });
  }

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => {
        this.auth.clearSession();
        this.router.navigate(['/login']);
      },
    });
  }
}
