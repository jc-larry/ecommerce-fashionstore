import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import {
  CatalogoService, Product, ProductImage, Review, ColorRef,
} from '../catalogo.service';

/**
 * [CU11] Detalle de prenda para el cliente + [CU14] reseñas y favorito.
 * Prendas multicolor: al elegir un color cambian las fotos y las tallas disponibles.
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

  constructor(
    public auth: AuthService,
    private catalogo: CatalogoService,
    private route: ActivatedRoute,
    public router: Router,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.notFound = true; this.loading = false; return; }

    forkJoin({
      product: this.catalogo.getProduct(id).pipe(catchError(() => of(null))),
      reviews: this.catalogo.getReviews(id).pipe(catchError(() => of({ summary: { average: 0, count: 0 }, items: [] }))),
      wishlist: this.auth.isLoggedIn()
        ? this.catalogo.getWishlist().pipe(catchError(() => of([] as Product[])))
        : of([] as Product[]),
    }).subscribe(({ product, reviews, wishlist }) => {
      this.loading = false;
      if (!product) { this.notFound = true; return; }
      this.product = product;
      this.reviews = reviews.items;
      this.ratingAvg = reviews.summary.average;
      this.ratingCount = reviews.summary.count;
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

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => { this.auth.clearSession(); this.router.navigate(['/login']); },
    });
  }
}
