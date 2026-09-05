import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import { CatalogoService, Product } from '../catalogo.service';

/** [CU14] Prendas favoritas del cliente. */
@Component({
  selector: 'app-wishlist',
  templateUrl: './wishlist.component.html',
  styleUrls: ['./store-home.component.css'],
})
export class WishlistComponent implements OnInit {
  products: Product[] = [];
  loading = true;

  constructor(public auth: AuthService, private catalogo: CatalogoService, public router: Router) {}

  ngOnInit(): void {
    this.catalogo.getWishlist().subscribe({
      next: (d) => { this.products = d; this.loading = false; },
      error: () => { this.loading = false; },
    });
  }

  primaryImage(p: Product): string | null {
    const img = (p.images || []).find((i) => i.is_primary) || (p.images || [])[0];
    return img?.image_url ? this.catalogo.resolveImageUrl(img.image_url) : null;
  }

  remove(p: Product, ev: Event): void {
    ev.stopPropagation();
    ev.preventDefault();
    this.catalogo.removeWishlist(p.id).subscribe({
      next: () => (this.products = this.products.filter((x) => x.id !== p.id)),
      error: () => {},
    });
  }
}
