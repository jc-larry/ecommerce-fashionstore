import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import { CatalogoService, Product, Wishlist, WishlistDetail } from '../catalogo.service';

/** [CU14+] Listas de Deseos múltiples y compartibles del cliente. */
@Component({
  selector: 'app-wishlist',
  templateUrl: './wishlist.component.html',
  styleUrls: ['./store-home.component.css'],
})
export class WishlistComponent implements OnInit {
  wishlists: Wishlist[] = [];
  selectedWishlist: Wishlist | null = null;
  products: Product[] = [];
  loading = true;
  loadingItems = false;
  copiedMessage = false;

  // Modal para crear nueva lista
  showCreateModal = false;
  newListName = '';
  newListIsPublic = false;

  constructor(public auth: AuthService, private catalogo: CatalogoService, public router: Router) {}

  ngOnInit(): void {
    this.loadWishlists();
  }

  loadWishlists(selectLast = false): void {
    this.loading = true;
    this.catalogo.getUserWishlists().subscribe({
      next: (lists) => {
        this.wishlists = lists;
        if (lists.length > 0) {
          const target = selectLast ? lists[lists.length - 1] : (this.selectedWishlist ? lists.find(l => l.id === this.selectedWishlist!.id) || lists[0] : lists[0]);
          this.selectWishlist(target);
        } else {
          this.products = [];
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  selectWishlist(wl: Wishlist): void {
    this.selectedWishlist = wl;
    this.loadingItems = true;
    this.catalogo.getWishlistDetail(wl.id).subscribe({
      next: (detail: WishlistDetail) => {
        this.products = detail.products;
        this.loadingItems = false;
      },
      error: () => {
        // Fallback a getWishlist() si es la primera
        this.catalogo.getWishlist().subscribe({
          next: (d) => { this.products = d; this.loadingItems = false; },
          error: () => { this.loadingItems = false; }
        });
      }
    });
  }

  togglePublic(wl: Wishlist): void {
    const nextState = !wl.is_public;
    this.catalogo.updateWishlist(wl.id, { is_public: nextState }).subscribe({
      next: (updated) => {
        wl.is_public = updated.is_public;
      }
    });
  }

  createList(): void {
    if (!this.newListName.trim()) return;
    this.catalogo.createWishlist({
      name: this.newListName.trim(),
      is_public: this.newListIsPublic,
    }).subscribe({
      next: (created) => {
        this.showCreateModal = false;
        this.newListName = '';
        this.newListIsPublic = false;
        this.loadWishlists(true);
      }
    });
  }

  deleteCurrentList(): void {
    if (!this.selectedWishlist) return;
    if (!confirm(`¿Eliminar la lista "${this.selectedWishlist.name}"?`)) return;

    this.catalogo.deleteWishlist(this.selectedWishlist.id).subscribe({
      next: () => {
        this.selectedWishlist = null;
        this.loadWishlists();
      }
    });
  }

  copyShareLink(): void {
    if (!this.selectedWishlist) return;
    const url = `${window.location.origin}/tienda/favoritos/compartida/${this.selectedWishlist.share_token}`;
    navigator.clipboard.writeText(url).then(() => {
      this.copiedMessage = true;
      setTimeout(() => this.copiedMessage = false, 3000);
    });
  }

  primaryImage(p: Product): string | null {
    const img = (p.images || []).find((i) => i.is_primary) || (p.images || [])[0];
    return img?.image_url ? this.catalogo.resolveImageUrl(img.image_url) : null;
  }

  remove(p: Product, ev: Event): void {
    ev.stopPropagation();
    ev.preventDefault();

    if (this.selectedWishlist) {
      this.catalogo.removeItemFromWishlist(this.selectedWishlist.id, p.id).subscribe({
        next: () => {
          this.products = this.products.filter((x) => x.id !== p.id);
          this.selectedWishlist!.items_count = Math.max(0, this.selectedWishlist!.items_count - 1);
        },
        error: () => {
          this.catalogo.removeWishlist(p.id).subscribe({
            next: () => (this.products = this.products.filter((x) => x.id !== p.id))
          });
        }
      });
    } else {
      this.catalogo.removeWishlist(p.id).subscribe({
        next: () => (this.products = this.products.filter((x) => x.id !== p.id)),
      });
    }
  }
}
