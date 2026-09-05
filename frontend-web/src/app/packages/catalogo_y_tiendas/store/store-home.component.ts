import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import { CatalogoService, Product, Category } from '../catalogo.service';

/**
 * [CU11] Tienda del cliente (web): navegación por categorías, grilla lookbook con
 * foto/precio/oferta/★/♥. Enlaza al detalle de prenda. [CU14] toggle de favorito.
 */
@Component({
  selector: 'app-store-home',
  templateUrl: './store-home.component.html',
  styleUrls: ['./store-home.component.css'],
})
export class StoreHomeComponent implements OnInit {
  products: Product[] = [];
  categories: Category[] = [];
  loading = true;

  search = '';
  categoryFilter: number | 'TODAS' = 'TODAS';

  private ratings = new Map<number, { average: number; count: number }>();
  private wishlistIds = new Set<number>();

  constructor(public auth: AuthService, private catalogo: CatalogoService, private router: Router) {}

  get userName(): string {
    const u = this.auth.getCurrentUser();
    return u ? u.first_name : 'Cliente';
  }

  // [CU11 - Paso 1] / [DSC011 - Paso 1] +entrarATienda()
  ngOnInit(): void {
    // [CU11 - Paso 2] / [DSC011 - Paso 2] +get_products()
    forkJoin({
      products: this.catalogo.getProducts().pipe(catchError(() => of([] as Product[]))),
      categories: this.catalogo.getCategories().pipe(catchError(() => of([] as Category[]))),
      ratings: this.catalogo.getRatingsSummary().pipe(catchError(() => of([]))),
      wishlist: this.auth.isLoggedIn()
        ? this.catalogo.getWishlist().pipe(catchError(() => of([] as Product[])))
        : of([] as Product[]),
    }).subscribe(({ products, categories, ratings, wishlist }) => {
      this.products = (products || []).filter((p) => p.is_active);
      this.categories = categories || [];
      for (const r of ratings) this.ratings.set(r.product_id, { average: r.average, count: r.count });
      this.wishlistIds = new Set(wishlist.map((p) => p.id));
      this.loading = false;
      // [CU11 - Paso 4] / [DSC011 - Paso 4] +Mostrar lista de prendas
    });
  }

  get filtered(): Product[] {
    const t = this.search.trim().toLowerCase();
    return this.products.filter((p) => {
      const matchesText = !t || `${p.name} ${p.description || ''}`.toLowerCase().includes(t);
      const catId = p.category?.id ?? p.category_id;
      const matchesCat = this.categoryFilter === 'TODAS' || catId === this.categoryFilter;
      return matchesText && matchesCat;
    });
  }

  get activeCategoryName(): string {
    if (this.categoryFilter === 'TODAS') return '';
    return this.categories.find((c) => c.id === this.categoryFilter)?.name || '';
  }

  selectCategory(id: number | 'TODAS'): void {
    this.categoryFilter = id;
  }

  categoryImg(c: Category): string | null {
    return c.image_url ? this.catalogo.resolveImageUrl(c.image_url) : null;
  }

  categoryName(p: Product): string {
    return p.category?.name || this.categories.find((c) => c.id === p.category_id)?.name || '';
  }

  primaryImage(p: Product): string | null {
    const img = (p.images || []).find((i) => i.is_primary) || (p.images || [])[0];
    return img?.image_url ? this.catalogo.resolveImageUrl(img.image_url) : null;
  }

  colorDots(p: Product): string[] {
    const seen = new Set<number>();
    const hexes: string[] = [];
    for (const v of p.variants || []) {
      if (v.color && !seen.has(v.color.id)) { seen.add(v.color.id); hexes.push(v.color.hex_code); }
    }
    return hexes.slice(0, 4);
  }

  sizeLabels(p: Product): string[] {
    const order = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
    const set = new Set<string>();
    for (const v of p.variants || []) if (v.is_active) set.add(v.size.name.toUpperCase());
    return [...set].sort((a, b) => {
      const ia = order.indexOf(a), ib = order.indexOf(b);
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
    if (!this.auth.isLoggedIn()) { this.router.navigate(['/login']); return; }
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
      error: () => { this.auth.clearSession(); this.router.navigate(['/login']); },
    });
  }
}
