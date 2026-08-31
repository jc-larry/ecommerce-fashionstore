import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import { CatalogoService } from '../catalogo.service';

@Component({
  selector: 'app-store-home',
  templateUrl: './store-home.component.html',
  styleUrls: ['./store-home.component.css']
})
export class StoreHomeComponent implements OnInit {
  products: any[] = [];
  categories: any[] = [];
  loading = true;

  search = '';
  categoryFilter = 'TODAS';

  constructor(
    public auth: AuthService,
    private catalogo: CatalogoService,
    private router: Router
  ) {}

  get userName(): string {
    const u = this.auth.getCurrentUser();
    return u ? `${u.first_name} ${u.last_name}` : 'Cliente';
  }

  /**
   * [CU11] Consultar catálogo (cliente)
   * @description Recupera el listado de productos activos desde el backend para que el cliente pueda navegar por la tienda.
   */
  // [CU11 - Paso 1] / [DSC011 - Paso 1] +entrarATienda()
  ngOnInit(): void {
    // [CU11 - Paso 2] / [DSC011 - Paso 2] +get_products()
    forkJoin({
      products: this.catalogo.getProducts().pipe(catchError(() => of([]))),
      categories: this.catalogo.getCategories().pipe(catchError(() => of([]))),
    }).subscribe(({ products, categories }) => {
      // El cliente solo ve prendas visibles
      this.products = (products || []).filter((p: any) => p.is_active);
      this.categories = categories || [];
      this.loading = false;
      // [CU11 - Paso 4] / [DSC011 - Paso 4] +Mostrar lista de prendas
    });
  }

  get filtered(): any[] {
    const t = this.search.trim().toLowerCase();
    return this.products.filter((p) => {
      const matchesText = !t || `${p.name} ${p.description || ''}`.toLowerCase().includes(t);
      const catId = p.category?.id ?? p.category_id;
      const matchesCat = this.categoryFilter === 'TODAS' || String(catId) === this.categoryFilter;
      return matchesText && matchesCat;
    });
  }

  categoryName(p: any): string {
    return p.category?.name || this.categories.find((c) => c.id === (p.category_id))?.name || '';
  }

  primaryImage(p: any): string | null {
    const img = (p.images || []).find((i: any) => i.is_primary) || (p.images || [])[0];
    return img?.image_url || null;
  }

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => { this.auth.clearSession(); this.router.navigate(['/login']); },
    });
  }
}
