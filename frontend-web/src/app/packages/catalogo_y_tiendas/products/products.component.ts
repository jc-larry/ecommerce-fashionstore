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

  // Gestión de imágenes
  uploadingImage = false;
  imageUploadError = '';

  // Filtro de tallas por tipo de curva
  sizeTab: 'ALL' | 'TOPS' | 'BOTTOMS' | 'BOTTOMS_US' = 'ALL';

  // Acordeón de categorías desplegadas
  expandedParents: { [id: number]: boolean } = {};

  // Categoría principal seleccionada en formulario
  selectedMainCatId: number | null = null;

  // Alta rápida de parámetros
  quick = {
    category: '',
    parentId: null as number | null,
    color: '',
    colorHex: '#C66F5C',
    size: '',
    sizeType: 'TOPS',
    season: '',
    seasonStart: '',
    seasonEnd: ''
  };

  // Opciones de atributos de moda femenina
  suggestedMaterials = [
    'Algodón', 'Lino', 'Seda', 'Denim / Mezclilla', 'Poliéster', 
    'Viscosa', 'Lana / Tejido', 'Satén', 'Cuero sintético', 'Encaje'
  ];
  suggestedNecks = [
    'Cuello camisero', 'Cuello en V', 'Cuello redondo', 
    'Cuello tortuga / alto', 'Cuello cuadrado', 'Halter / Strapless', 'Cuello barco'
  ];
  suggestedSleeves = [
    'Sin mangas', 'Manga corta', 'Manga 3/4', 'Manga larga', 'Tirantes finos'
  ];
  suggestedTags = [
    'Casual', 'Elegante / Oficina', 'Fiesta / Noche', 'Verano', 
    'Oversize', 'Bordado', 'Estampado floral', 'Básico imprescindible'
  ];

  constructor(private catalogo: CatalogoService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  emptyForm() {
    return {
      name: '',
      description: '',
      base_price: 0,
      compare_at_price: null as number | null,
      category_id: null as number | null,
      season_id: null as number | null,
      is_active: true,
      material: '',
      neck_type: '',
      sleeve_length: '',
      tags: '',
      images: [] as { image_url: string; color_id: number | null; is_primary: boolean }[],
      variants: [] as { color_id: number | null; size_id: number | null; sku: string }[],
    };
  }

  loadAll(): void {
    this.loading = true;
    this.catalogo.getProducts().subscribe({
      next: (d) => { this.products = d; this.loading = false; },
      error: () => { this.error = 'No se pudo cargar el catálogo.'; this.loading = false; },
    });
    this.catalogo.getCategories().subscribe({
      next: (d) => {
        this.categories = d;
        // Expandir por defecto las categorías principales
        this.categories.filter(c => !c.parent_id).forEach(p => this.expandedParents[p.id] = true);
      },
      error: () => {}
    });
    this.catalogo.getColors().subscribe({ next: (d) => (this.colors = d), error: () => {} });
    this.catalogo.getSizes().subscribe({ next: (d) => (this.sizes = d), error: () => {} });
    this.catalogo.getSeasons().subscribe({ next: (d) => (this.seasons = d), error: () => {} });
  }

  get filtered(): any[] {
    const t = this.search.trim().toLowerCase();
    if (!t) return this.products;
    return this.products.filter((p) => 
      `${p.name}`.toLowerCase().includes(t) ||
      `${p.material || ''}`.toLowerCase().includes(t) ||
      `${p.tags || ''}`.toLowerCase().includes(t)
    );
  }

  // --- Helpers de taxonomía de categorías ---
  get mainCategories(): any[] {
    return this.categories.filter(c => !c.parent_id);
  }

  subcategoriesOf(parentId: number): any[] {
    return this.categories.filter(c => c.parent_id === parentId);
  }

  toggleParent(parentId: number): void {
    this.expandedParents[parentId] = !this.expandedParents[parentId];
  }

  categoryName(p: any): string {
    const cat = p.category || this.categories.find((c) => c.id === p.category_id);
    if (!cat) return '—';
    if (cat.parent_id) {
      const parent = this.categories.find(c => c.id === cat.parent_id);
      return parent ? `${parent.name} > ${cat.name}` : cat.name;
    }
    return cat.name;
  }

  seasonName(p: any): string {
    return p.season?.name || this.seasons.find((s) => s.id === p.season_id)?.name || 'Toda estación';
  }

  primaryImageUrl(p: any): string | null {
    const img = (p.images || []).find((i: any) => i.is_primary) || (p.images || [])[0];
    return img?.image_url ? this.catalogo.resolveImageUrl(img.image_url) : null;
  }

  resolveImg(url?: string | null): string {
    return this.catalogo.resolveImageUrl(url);
  }

  discountPct(p: any): number {
    const base = Number(p.base_price || 0);
    const cmp = Number(p.compare_at_price || 0);
    return cmp > base && base > 0 ? Math.round((1 - base / cmp) * 100) : 0;
  }

  // --- Tallas por pestaña ---
  get filteredSizesList(): any[] {
    if (this.sizeTab === 'ALL') return this.sizes;
    return this.sizes.filter(s => s.category_type === this.sizeTab);
  }

  /** Sube o cambia la foto de portada de una categoría. */
  onCategoryImage(cat: any, event: any): void {
    const file = event.target?.files?.[0];
    event.target.value = '';
    if (!file) return;
    this.catalogo.uploadImage(file).subscribe({
      next: (res) => {
        this.catalogo.updateCategory(cat.id, { image_url: res.image_url }).subscribe({
          next: (updated) => { cat.image_url = updated.image_url; },
          error: (e) => (this.error = e.error?.detail || 'No se pudo guardar la foto de la categoría.'),
        });
      },
      error: (e) => (this.error = e.error?.detail || 'Error al subir la imagen.'),
    });
  }

  /** Sube un archivo y lo añade a la galería de la prenda. */
  onFileSelected(event: any): void {
    const file = event.target?.files?.[0];
    event.target.value = '';
    if (!file) return;
    this.uploadingImage = true;
    this.imageUploadError = '';
    this.catalogo.uploadImage(file).subscribe({
      next: (res) => {
        this.form.images.push({
          image_url: res.image_url,
          color_id: null,
          is_primary: this.form.images.length === 0,
        });
        this.uploadingImage = false;
      },
      error: (err) => {
        this.imageUploadError = err.error?.detail || 'Error al subir la imagen.';
        this.uploadingImage = false;
      }
    });
  }

  addImageByUrl(url: string): void {
    const u = (url || '').trim();
    if (!u) return;
    this.form.images.push({ image_url: u, color_id: null, is_primary: this.form.images.length === 0 });
  }

  removeImage(i: number): void {
    const wasPrimary = this.form.images[i].is_primary;
    this.form.images.splice(i, 1);
    if (wasPrimary && this.form.images.length) this.form.images[0].is_primary = true;
  }

  setPrimaryImage(i: number): void {
    this.form.images.forEach((img, idx) => (img.is_primary = idx === i));
  }

  // ---- Formulario de Prenda ----
  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.selectedMainCatId = null;
    this.imageUploadError = '';
    this.showForm = true;
  }

  openEdit(p: any): void {
    this.editingId = p.id;
    this.imageUploadError = '';
    
    // Identificar categoría principal si es subcategoría
    const cat = this.categories.find(c => c.id === p.category_id);
    if (cat?.parent_id) {
      this.selectedMainCatId = cat.parent_id;
    } else {
      this.selectedMainCatId = p.category_id;
    }

    this.form = {
      name: p.name,
      description: p.description || '',
      base_price: p.base_price,
      compare_at_price: p.compare_at_price ?? null,
      category_id: p.category_id ?? null,
      season_id: p.season_id ?? null,
      is_active: p.is_active,
      material: p.material || '',
      neck_type: p.neck_type || '',
      sleeve_length: p.sleeve_length || '',
      tags: p.tags || '',
      images: (p.images || []).map((i: any) => ({
        image_url: i.image_url,
        color_id: i.color_id ?? null,
        is_primary: !!i.is_primary,
      })),
      variants: (p.variants || [])
        .filter((v: any) => v.is_active)
        .map((v: any) => ({
          color_id: v.color_id ?? v.color?.id ?? null,
          size_id: v.size_id ?? v.size?.id ?? null,
          sku: v.sku,
        })),
    };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  onMainCatChange(): void {
    const subs = this.selectedMainCatId ? this.subcategoriesOf(this.selectedMainCatId) : [];
    if (subs.length > 0) {
      this.form.category_id = subs[0].id;
    } else {
      this.form.category_id = this.selectedMainCatId;
    }
  }

  get availableSubcategories(): any[] {
    if (!this.selectedMainCatId) return [];
    return this.subcategoriesOf(this.selectedMainCatId);
  }

  addTag(tag: string): void {
    const current = (this.form.tags || '').split(',').map(t => t.trim()).filter(Boolean);
    if (!current.includes(tag)) {
      current.push(tag);
      this.form.tags = current.join(', ');
    }
  }

  /** Genera automáticamente variantes sugeridas para la prenda según su categoría y un color elegido */
  generateSuggestedVariants(): void {
    const colorId = this.form.variants[0]?.color_id || (this.colors[0]?.id ?? null);
    if (!colorId) {
      this.error = 'Registra o selecciona un color primero para generar las variantes.';
      return;
    }

    // Identificar si la categoría es inferior (pantalón/jean) o superior/vestido
    const cat = this.categories.find(c => c.id === this.form.category_id);
    const parent = cat?.parent_id ? this.categories.find(c => c.id === cat.parent_id) : null;
    const isBottom = (parent?.name || cat?.name || '').toLowerCase().includes('inferior') ||
                     (cat?.name || '').toLowerCase().includes('jean') ||
                     (cat?.name || '').toLowerCase().includes('pantal');

    const targetType = isBottom ? 'BOTTOMS' : 'TOPS';
    const suggestedSizes = this.sizes.filter(s => s.category_type === targetType);
    const sizesToUse = suggestedSizes.length > 0 ? suggestedSizes : this.sizes.slice(0, 5);

    const prefix = (this.form.name || 'PRD').substring(0, 3).toUpperCase().replace(/[^A-Z]/g, 'X');
    const colObj = this.colors.find(c => c.id === colorId);
    const colCode = (colObj?.name || 'COL').substring(0, 3).toUpperCase().replace(/[^A-Z]/g, 'C');

    // Añadir variantes para cada talla sin duplicar
    sizesToUse.forEach(s => {
      const exists = this.form.variants.some(v => v.color_id === colorId && v.size_id === s.id);
      if (!exists) {
        this.form.variants.push({
          color_id: colorId,
          size_id: s.id,
          sku: `${prefix}-${colCode}-${s.name}-${Math.floor(100 + Math.random() * 900)}`
        });
      }
    });
  }

  addVariantRow(): void {
    this.form.variants.push({ color_id: null, size_id: null, sku: '' });
  }

  removeVariantRow(i: number): void {
    this.form.variants.splice(i, 1);
  }

  private cleanVariants() {
    return this.form.variants
      .filter((v) => v.color_id && v.size_id && v.sku.trim())
      .map((v) => ({ color_id: v.color_id, size_id: v.size_id, sku: v.sku.trim() }));
  }

  save(): void {
    this.error = '';
    if (!this.form.name.trim()) {
      this.error = 'El nombre de la prenda es obligatorio.';
      return;
    }
    if (!this.form.category_id) {
      this.error = 'Debes seleccionar una categoría o subcategoría.';
      return;
    }

    const base: any = {
      name: this.form.name.trim(),
      description: this.form.description,
      base_price: Number(this.form.base_price),
      compare_at_price: this.form.compare_at_price ? Number(this.form.compare_at_price) : null,
      category_id: this.form.category_id,
      season_id: this.form.season_id,
      is_active: this.form.is_active,
      material: this.form.material ? this.form.material.trim() : null,
      neck_type: this.form.neck_type ? this.form.neck_type.trim() : null,
      sleeve_length: this.form.sleeve_length ? this.form.sleeve_length.trim() : null,
      tags: this.form.tags ? this.form.tags.trim() : null,
      images: this.form.images.map((i) => ({
        image_url: i.image_url, color_id: i.color_id, is_primary: i.is_primary,
      })),
      variants: this.cleanVariants(),
    };

    const done = () => { this.loadAll(); this.closeForm(); };
    if (this.editingId) {
      this.catalogo.updateProduct(this.editingId, base).subscribe({
        next: done,
        error: (e) => (this.error = e.error?.detail || 'Error al actualizar la prenda.'),
      });
    } else {
      this.catalogo.createProduct(base).subscribe({
        next: done,
        error: (e) => (this.error = e.error?.detail || 'Error al crear la prenda.'),
      });
    }
  }

  deactivate(p: any): void {
    if (!confirm(`¿Ocultar la prenda "${p.name}" del catálogo?`)) return;
    this.catalogo.deactivateProduct(p.id).subscribe({
      next: () => this.loadAll(),
      error: (e) => (this.error = e.error?.detail || 'Error al ocultar la prenda.'),
    });
  }

  // ---- Alta rápida de parámetros con validación ----
  addCategory(): void {
    const raw = (this.quick.category || '').trim();
    if (!raw) return;

    // Validación: las categorías deben contener texto/letras y no solo números
    if (/^\d+$/.test(raw)) {
      this.error = 'El nombre de la categoría debe ser descriptivo (letras), no solo números.';
      return;
    }

    const payload: any = { name: raw };
    if (this.quick.parentId) {
      payload.parent_id = Number(this.quick.parentId);
    }

    this.catalogo.createCategory(payload).subscribe({
      next: () => {
        this.quick.category = '';
        this.catalogo.getCategories().subscribe((d) => (this.categories = d));
      },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar la categoría.'),
    });
  }

  deleteCategory(c: any): void {
    if (!confirm(`¿Eliminar la categoría "${c.name}"?`)) return;
    this.catalogo.deleteCategory(c.id).subscribe({
      next: () => this.catalogo.getCategories().subscribe((d) => (this.categories = d)),
      error: (e) => (this.error = e.error?.detail || 'No se pudo eliminar la categoría.')
    });
  }

  addColor(): void {
    const name = (this.quick.color || '').trim();
    if (!name) return;

    if (/^\d+$/.test(name)) {
      this.error = 'El nombre del color debe ser descriptivo (ej. Blanco, Rojo Vino), no solo números.';
      return;
    }

    this.catalogo.createColor({ name, hex_code: this.quick.colorHex }).subscribe({
      next: () => {
        this.quick.color = '';
        this.catalogo.getColors().subscribe((d) => (this.colors = d));
      },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar el color.'),
    });
  }

  deleteColor(col: any): void {
    if (!confirm(`¿Eliminar el color "${col.name}"?`)) return;
    this.catalogo.deleteColor(col.id).subscribe({
      next: () => this.catalogo.getColors().subscribe((d) => (this.colors = d)),
      error: (e) => (this.error = e.error?.detail || 'No se puede eliminar porque está en uso por prendas.')
    });
  }

  addSize(): void {
    const name = (this.quick.size || '').trim().toUpperCase();
    if (!name) return;

    this.catalogo.createSize({ name, category_type: this.quick.sizeType }).subscribe({
      next: () => {
        this.quick.size = '';
        this.catalogo.getSizes().subscribe((d) => (this.sizes = d));
      },
      error: (e) => (this.error = e.error?.detail || 'Error al agregar la talla.'),
    });
  }

  deleteSize(s: any): void {
    if (!confirm(`¿Eliminar la talla "${s.name}"?`)) return;
    this.catalogo.deleteSize(s.id).subscribe({
      next: () => this.catalogo.getSizes().subscribe((d) => (this.sizes = d)),
      error: (e) => (this.error = e.error?.detail || 'No se puede eliminar porque está en uso por prendas.')
    });
  }

  addSeason(): void {
    if (!this.quick.season.trim() || !this.quick.seasonStart || !this.quick.seasonEnd) return;
    this.catalogo
      .createSeason({ name: this.quick.season.trim(), start_date: this.quick.seasonStart, end_date: this.quick.seasonEnd })
      .subscribe({
        next: () => {
          this.quick.season = '';
          this.catalogo.getSeasons().subscribe((d) => (this.seasons = d));
        },
        error: (e) => (this.error = e.error?.detail || 'Error al agregar la temporada.'),
      });
  }
}

