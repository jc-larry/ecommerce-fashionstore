import { Component, OnInit } from '@angular/core';
import { CatalogoService } from '../catalogo.service';

@Component({
  selector: 'app-products',
  templateUrl: './products.component.html',
  styleUrls: ['./products.component.css']
})
export class ProductsComponent implements OnInit {
  products: any[] = [];
  categories: any[] = [];
  colors: any[] = [];
  sizes: any[] = [];
  seasons: any[] = [];

  loading = false;
  error = '';
  search = '';

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();

  // Alta rápida de parámetros
  quick = { category: '', color: '', colorHex: '#C66F5C', size: '', season: '', seasonStart: '', seasonEnd: '' };

  constructor(private catalogo: CatalogoService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  emptyForm() {
    return {
      name: '',
      description: '',
      base_price: 0,
      category_id: null as number | null,
      season_id: null as number | null,
      is_active: true,
      variants: [] as { color_id: number | null; size_id: number | null; sku: string }[],
    };
  }

  loadAll(): void {
    this.loading = true;
    this.catalogo.getProducts().subscribe({
      next: (d) => { this.products = d; this.loading = false; },
      error: () => { this.error = 'No se pudo cargar el catálogo.'; this.loading = false; },
    });
    this.catalogo.getCategories().subscribe({ next: (d) => (this.categories = d), error: () => {} });
    this.catalogo.getColors().subscribe({ next: (d) => (this.colors = d), error: () => {} });
    this.catalogo.getSizes().subscribe({ next: (d) => (this.sizes = d), error: () => {} });
    this.catalogo.getSeasons().subscribe({ next: (d) => (this.seasons = d), error: () => {} });
  }

  get filtered(): any[] {
    const t = this.search.trim().toLowerCase();
    if (!t) return this.products;
    return this.products.filter((p) => `${p.name}`.toLowerCase().includes(t));
  }

  categoryName(p: any): string {
    return p.category?.name || this.categories.find((c) => c.id === p.category_id)?.name || '—';
  }

  seasonName(p: any): string {
    return p.season?.name || this.seasons.find((s) => s.id === p.season_id)?.name || 'Toda estación';
  }

  // ---- Producto ----
  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.showForm = true;
  }

  openEdit(p: any): void {
    this.editingId = p.id;
    this.form = {
      name: p.name,
      description: p.description || '',
      base_price: p.base_price,
      category_id: p.category_id ?? p.category?.id ?? null,
      season_id: p.season_id ?? p.season?.id ?? null,
      is_active: p.is_active,
      variants: [],
    };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  addVariantRow(): void {
    this.form.variants.push({ color_id: null, size_id: null, sku: '' });
  }

  removeVariantRow(i: number): void {
    this.form.variants.splice(i, 1);
  }

  /**
   * [CU07] Gestionar catálogo
   * @description Registra un nuevo producto de ropa junto con sus variantes (tallas, colores y SKU), o actualiza uno existente.
   */
  // [CU07 - Paso 1] / [DSC007 - Paso 1] +registrar(datos, variantes)
  save(): void {
    this.error = '';
    if (this.editingId) {
      const payload = {
        name: this.form.name,
        description: this.form.description,
        base_price: Number(this.form.base_price),
        category_id: this.form.category_id,
        season_id: this.form.season_id,
        is_active: this.form.is_active,
      };
      this.catalogo.updateProduct(this.editingId, payload).subscribe({
        next: () => { this.loadAll(); this.closeForm(); },
        error: (e) => (this.error = e.error?.detail || 'Error al actualizar la prenda.'),
      });
    } else {
      const payload = {
        name: this.form.name,
        description: this.form.description,
        base_price: Number(this.form.base_price),
        category_id: this.form.category_id,
        season_id: this.form.season_id,
        is_active: this.form.is_active,
        variants: this.form.variants
          .filter((v) => v.color_id && v.size_id && v.sku)
          .map((v) => ({ color_id: v.color_id, size_id: v.size_id, sku: v.sku })),
      };
      // [CU07 - Paso 2] / [DSC007 - Paso 2] +create_product(datos, variantes)
      this.catalogo.createProduct(payload).subscribe({
        next: () => { 
          // [CU07 - Paso 7] / [DSC007 - Paso 7] +Actualizar UI
          this.loadAll(); 
          this.closeForm(); 
        },
        error: (e) => (this.error = e.error?.detail || 'Error al crear la prenda.'),
      });
    }
  }

  /**
   * [CU07] Gestionar catálogo
   * @description Oculta lógicamente un producto del catálogo para que ya no sea visible en la tienda del cliente.
   */
  deactivate(p: any): void {
    if (!confirm(`¿Ocultar la prenda ${p.name} del catálogo?`)) return;
    this.catalogo.deactivateProduct(p.id).subscribe({
      next: () => this.loadAll(),
      error: (e) => (this.error = e.error?.detail || 'Error al ocultar la prenda.'),
    });
  }

  // ---- Alta rápida de parámetros ----
  addCategory(): void {
    if (!this.quick.category.trim()) return;
    this.catalogo.createCategory({ name: this.quick.category.trim() }).subscribe({
      next: () => { this.quick.category = ''; this.catalogo.getCategories().subscribe((d) => (this.categories = d)); },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar la categoría.'),
    });
  }

  addColor(): void {
    if (!this.quick.color.trim()) return;
    this.catalogo.createColor({ name: this.quick.color.trim(), hex_code: this.quick.colorHex }).subscribe({
      next: () => { this.quick.color = ''; this.catalogo.getColors().subscribe((d) => (this.colors = d)); },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar el color.'),
    });
  }

  addSize(): void {
    if (!this.quick.size.trim()) return;
    this.catalogo.createSize({ name: this.quick.size.trim() }).subscribe({
      next: () => { this.quick.size = ''; this.catalogo.getSizes().subscribe((d) => (this.sizes = d)); },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar la talla.'),
    });
  }

  addSeason(): void {
    if (!this.quick.season.trim() || !this.quick.seasonStart || !this.quick.seasonEnd) return;
    this.catalogo
      .createSeason({ name: this.quick.season.trim(), start_date: this.quick.seasonStart, end_date: this.quick.seasonEnd })
      .subscribe({
        next: () => { this.quick.season = ''; this.catalogo.getSeasons().subscribe((d) => (this.seasons = d)); },
        error: (e) => (this.error = e.error?.detail || 'Error al agregar la temporada.'),
      });
  }
}
