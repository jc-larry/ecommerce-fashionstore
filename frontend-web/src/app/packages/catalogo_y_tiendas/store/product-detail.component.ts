import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import {
  CatalogoService, Product, ProductImage, Review, ColorRef, ProductAvailabilityResponse,
} from '../catalogo.service';
import { VentasService } from '../../ventas_y_pagos/ventas.service';

/**
 * [CU11] Detalle de prenda para el cliente + [CU14] reseñas y favorito.
 * [CU12] Disponibilidad y existencia física por sucursal para la variante seleccionada.
 */
@Component({
  selector: 'app-product-detail',
  templateUrl: './product-detail.component.html',
  styleUrls: ['./product-detail.component.css'],
})
export class ProductDetailComponent implements OnInit {
  loading = true;
  notFound = false;
  product: Product | null = null;
  availability: ProductAvailabilityResponse | null = null;

  selectedColorId: number | null = null;
  selectedSizeId: number | null = null;
  activeImageIndex = 0;

  reviews: Review[] = [];
  ratingAvg = 0;
  ratingCount = 0;

  // Formulario de reseña
  myRating = 0;
  myComment = '';
  hoverRating = 0;
  savingReview = false;
  reviewError = '';

  inWishlist = false;
  showSizeGuide = false;
  isCartOpen = false;
  cartFeedback: string | null = null;
  addingToCart = false;

  allBranches: any[] = [];

  // Formulario de cita de vestidor
  showFittingModal = false;
  selectedAppointmentBranch: any = null;
  appointmentDate = '';
  appointmentTime = '15:00';
  appointmentNotes = '';
  customerPhone = '';
  bookingConfirmed = false;
  bookingCode = '';

  constructor(
    public auth: AuthService,
    private catalogo: CatalogoService,
    private ventasService: VentasService,
    private route: ActivatedRoute,
    public router: Router,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.notFound = true; this.loading = false; return; }

    forkJoin({
      product: this.catalogo.getProduct(id).pipe(catchError(() => of(null))),
      reviews: this.catalogo.getReviews(id).pipe(catchError(() => of({ summary: { average: 0, count: 0 }, items: [] }))),
      availability: this.catalogo.getProductBranchAvailability(id).pipe(catchError(() => of(null))),
      branches: this.catalogo.getBranches().pipe(catchError(() => of([] as any[]))),
      wishlist: this.auth.isLoggedIn()
        ? this.catalogo.getWishlist().pipe(catchError(() => of([] as Product[])))
        : of([] as Product[]),
    }).subscribe(({ product, reviews, availability, branches, wishlist }) => {
      this.loading = false;
      if (!product) { this.notFound = true; return; }
      this.product = product;
      this.reviews = reviews.items;
      this.ratingAvg = reviews.summary.average;
      this.ratingCount = reviews.summary.count;
      this.availability = availability;
      this.allBranches = branches;
      this.inWishlist = wishlist.some((p) => p.id === product.id);

      const colors = this.colors;
      this.selectedColorId = colors.length ? colors[0].id : null;
      this.syncSelection();

      const mine = this.reviews.find((r) => r.is_mine);
      if (mine) { this.myRating = mine.rating; this.myComment = mine.comment || ''; }
    });
  }

  // ---- Datos derivados ----
  get colors(): ColorRef[] {
    if (!this.product) return [];
    const seen = new Map<number, ColorRef>();
    for (const v of this.product.variants) {
      if (v.color && !seen.has(v.color.id)) seen.set(v.color.id, v.color);
    }
    return [...seen.values()];
  }

  get galleryImages(): ProductImage[] {
    if (!this.product) return [];
    const imgs = this.product.images || [];
    const forColor = imgs.filter((i) => i.color_id === this.selectedColorId);
    const chosen = forColor.length ? forColor : imgs;
    // primaria primero
    return [...chosen].sort((a, b) => Number(b.is_primary) - Number(a.is_primary));
  }

  get currentImageUrl(): string | null {
    const g = this.galleryImages;
    return g.length ? this.resolveImg(g[Math.min(this.activeImageIndex, g.length - 1)].image_url) : null;
  }

  /** Tallas disponibles para el color elegido (todas las tallas del producto, marcando cuáles hay). */
  get sizeOptions(): { id: number; name: string; available: boolean }[] {
    if (!this.product) return [];
    const all = new Map<number, string>();
    for (const v of this.product.variants) all.set(v.size.id, v.size.name);
    const availForColor = new Set(
      this.product.variants
        .filter((v) => v.color_id === this.selectedColorId && v.is_active)
        .map((v) => v.size.id),
    );
    return [...all.entries()]
      .map(([id, name]) => ({ id, name, available: availForColor.has(id) }))
      .sort((a, b) => this.sizeRank(a.name) - this.sizeRank(b.name));
  }

  private sizeRank(name: string): number {
    const order = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
    const i = order.indexOf(name.toUpperCase());
    return i >= 0 ? i : 99;
  }

  selectColor(id: number): void {
    this.selectedColorId = id;
    this.activeImageIndex = 0;
    this.syncSelection();
  }

  private syncSelection(): void {
    const avail = this.sizeOptions.filter((s) => s.available);
    this.selectedSizeId = avail.length ? avail[0].id : null;
  }

  selectSize(id: number, available: boolean): void {
    if (available) this.selectedSizeId = id;
  }

  resolveImg(url?: string | null): string {
    return this.catalogo.resolveImageUrl(url);
  }

  get selectedColor(): ColorRef | undefined {
    return this.colors.find(c => c.id === this.selectedColorId);
  }

  get selectedSize(): { id: number; name: string; available: boolean } | undefined {
    return this.sizeOptions.find(s => s.id === this.selectedSizeId);
  }

  // ---- Disponibilidad por Sucursal (CU12) ----
  get branchStockList(): {
    branchId: number;
    branchName: string;
    city: string;
    stock: number;
    hasStock: boolean;
    isTemporarilyClosed: boolean;
    closureReason: string | null;
    hasFittingRoom: boolean;
    openingTime: string;
    closingTime: string;
    daysOpen: string;
    phone: string;
  }[] {
    if (!this.availability || !this.selectedColorId || !this.selectedSizeId) return [];
    const variant = this.availability.variants.find(
      (v) => v.color_id === this.selectedColorId && v.size_id === this.selectedSizeId
    );
    if (!variant) return [];
    return variant.branches.map((b) => {
      const full = this.allBranches.find((br) => br.id === b.branch_id || br.name === b.branch_name);
      return {
        branchId: b.branch_id,
        branchName: b.branch_name,
        city: b.city || full?.city || 'Santa Cruz',
        stock: b.stock,
        hasStock: b.stock > 0,
        isTemporarilyClosed: !!full?.is_temporarily_closed,
        closureReason: full?.closure_reason || null,
        hasFittingRoom: full?.has_fitting_room ?? true,
        openingTime: full?.opening_time || '09:00',
        closingTime: full?.closing_time || '21:00',
        daysOpen: full?.days_open || 'Lunes a Sábado',
        phone: full?.phone || full?.whatsapp || ''
      };
    });
  }

  // ---- Cita de Probador / Ensayo en Tienda ----
  openFittingModal(b: any): void {
    if (b.isTemporarilyClosed) {
      alert(`Esta sucursal está cerrada temporalmente (${b.closureReason || 'en refacciones'}). No es posible agendar citas aquí por el momento.`);
      return;
    }
    this.selectedAppointmentBranch = b;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    this.appointmentDate = tomorrow.toISOString().split('T')[0];
    this.appointmentTime = b.openingTime || '15:00';
    this.bookingConfirmed = false;
    this.bookingCode = '';
    this.showFittingModal = true;
  }

  closeFittingModal(): void {
    this.showFittingModal = false;
  }

  confirmAppointment(): void {
    if (!this.appointmentDate || !this.appointmentTime) {
      alert('Por favor selecciona la fecha y hora de tu cita.');
      return;
    }
    this.bookingCode = 'CITA-' + Math.floor(100000 + Math.random() * 900000);
    this.bookingConfirmed = true;

    const saved = JSON.parse(localStorage.getItem('fashionstore_fitting_appointments') || '[]');
    const newAppointment = {
      code: this.bookingCode,
      branchName: this.selectedAppointmentBranch.branchName,
      branchCity: this.selectedAppointmentBranch.city,
      productName: this.product?.name,
      colorName: this.selectedColor?.name,
      sizeName: this.selectedSize?.name,
      date: this.appointmentDate,
      time: this.appointmentTime,
      phone: this.customerPhone,
      notes: this.appointmentNotes,
      createdAt: new Date().toISOString(),
      status: 'CONFIRMADA'
    };
    saved.push(newAppointment);
    localStorage.setItem('fashionstore_fitting_appointments', JSON.stringify(saved));
  }

  get totalSelectedVariantStock(): number {
    if (!this.availability || !this.selectedColorId || !this.selectedSizeId) return 0;
    const variant = this.availability.variants.find(
      (v) => v.color_id === this.selectedColorId && v.size_id === this.selectedSizeId
    );
    return variant ? variant.total_stock : 0;
  }

  // ---- Favorito ----
  toggleWishlist(): void {
    if (!this.product) return;
    if (!this.auth.isLoggedIn()) { this.router.navigate(['/login']); return; }
    const obs = this.inWishlist
      ? this.catalogo.removeWishlist(this.product.id)
      : this.catalogo.addWishlist(this.product.id);
    obs.subscribe({ next: (r) => (this.inWishlist = r.in_wishlist), error: () => {} });
  }

  // ---- Reseña ----
  setRating(n: number): void { this.myRating = n; }

  submitReview(): void {
    if (!this.product) return;
    this.reviewError = '';
    if (this.myRating < 1) { this.reviewError = 'Elige una calificación (1 a 5 estrellas).'; return; }
    this.savingReview = true;
    this.catalogo.submitReview(this.product.id, { rating: this.myRating, comment: this.myComment.trim() || undefined })
      .subscribe({
        next: () => {
          this.savingReview = false;
          this.catalogo.getReviews(this.product!.id).subscribe((r) => {
            this.reviews = r.items;
            this.ratingAvg = r.summary.average;
            this.ratingCount = r.summary.count;
          });
        },
        error: (e) => {
          this.savingReview = false;
          this.reviewError = e.error?.detail || 'No se pudo guardar tu reseña.';
        },
      });
  }

  addToCart(): void {
    if (!this.product) return;
    if (!this.auth.isLoggedIn()) { this.router.navigate(['/login']); return; }

    const variant = this.product.variants.find(
      (v) => v.color_id === this.selectedColorId && v.size_id === this.selectedSizeId
    );
    if (!variant) {
      this.cartFeedback = 'Selecciona color y talla disponibles.';
      return;
    }

    this.addingToCart = true;
    this.cartFeedback = null;
    this.ventasService.addToCart(variant.id, 1).subscribe({
      next: () => {
        this.addingToCart = false;
        this.cartFeedback = '¡Prenda agregada al carrito!';
        this.isCartOpen = true;
      },
      error: (err) => {
        this.addingToCart = false;
        this.cartFeedback = err?.error?.detail || 'No se pudo agregar al carrito (stock insuficiente).';
      }
    });
  }

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => { this.auth.clearSession(); this.router.navigate(['/login']); },
    });
  }
}
