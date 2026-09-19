import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { InventarioService } from '../inventario.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

type SupplierTab = 'pedidos' | 'ofertar' | 'perfil' | 'productos' | 'compras';
type SupplierProductStatus = 'DISPONIBLE' | 'AGOTADO' | 'DESCONTINUADO';

const SUPPLIER_TABS: SupplierTab[] = ['pedidos', 'ofertar', 'perfil', 'productos', 'compras'];
const MAX_OFFER_PHOTOS = 6;
/** Lado mayor (px) y calidad JPEG de las fotos de ofertas antes de enviarlas. */
const PHOTO_MAX_SIDE = 900;
const PHOTO_JPEG_QUALITY = 0.72;

interface ProductCard {
  product_id: number;
  product_name: string;
  image_url: string | null;
  supplier_status: SupplierProductStatus;
  total_stock: number;
  variants: any[];
}

/**
 * [Rol PROVEEDOR] Portal de autoservicio: bandeja de pedidos de reposición de Casa Matriz
 * (con foto de la prenda y sucursal destino), ofertas de nuevos modelos con galería de fotos,
 * disponibilidad por prenda (si todavía la trae), ficha de contacto e historial de compras.
 * La pestaña activa se sincroniza con ?tab= para que el menú lateral la abra.
 */
@Component({
  selector: 'app-supplier-portal',
  templateUrl: './supplier-portal.component.html',
  styleUrls: ['./supplier-portal.component.css'],
})
export class SupplierPortalComponent implements OnInit, OnDestroy {
  activeTab: SupplierTab = 'pedidos';

  loading = false;
  error = '';
  success = '';

  profile: any = null;
  contactForm = { contact_name: '', email: '', phone: '', address: '' };

  products: any[] = [];
  purchaseOrders: any[] = [];

  reorders: any[] = [];
  reorderFilter: 'ACTIVOS' | 'TODOS' = 'ACTIVOS';
  respondingId: number | null = null;
  respondForm = { estimated_delivery: '', supplier_notes: '' };

  offers: any[] = [];
  offerForm = this.emptyOfferForm();
  sendingOffer = false;
  processingPhotos = false;

  photoPreview: string | null = null;
  galleryIndex: Record<number, number> = {};

  readonly maxPhotos = MAX_OFFER_PHOTOS;
  readonly reorderStatusLabels: Record<string, string> = {
    PENDING: 'Pendiente de respuesta',
    ACCEPTED: 'Aceptado · por despachar',
    SHIPPED: 'Enviado a sucursal',
    RECEIVED: 'Recibido por la sucursal',
    REJECTED: 'Rechazado',
    CANCELLED: 'Anulado por Casa Matriz',
  };
  readonly offerStatusLabels: Record<string, string> = {
    PENDING: 'En revisión',
    APPROVED: 'Aprobada',
    DISPONIBLE: 'Disponible',
    AGOTADO: 'Agotado',
    DESCONTINUADO: 'Ya no lo traigo',
    REJECTED: 'Rechazada',
  };
  readonly productStatusOptions: { value: SupplierProductStatus; label: string }[] = [
    { value: 'DISPONIBLE', label: 'Disponible' },
    { value: 'AGOTADO', label: 'Agotado' },
    { value: 'DESCONTINUADO', label: 'Ya no lo traigo' },
  ];

  private routeSub?: Subscription;

  constructor(
    private inventario: InventarioService,
    public authService: AuthService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.loadProfile();
    this.loadReorders();
    this.routeSub = this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab') as SupplierTab | null;
      this.applyTab(tab && SUPPLIER_TABS.includes(tab) ? tab : 'pedidos');
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
  }

  /** Cambiar de pestaña actualiza la URL; el menú lateral queda sincronizado. */
  setTab(tab: SupplierTab): void {
    this.router.navigate([], { relativeTo: this.route, queryParams: { tab }, queryParamsHandling: 'merge' });
  }

  private applyTab(tab: SupplierTab): void {
    this.activeTab = tab;
    this.error = '';
    this.success = '';
    if (tab === 'ofertar' && this.offers.length === 0) this.loadOffers();
    if (tab === 'productos' && this.products.length === 0) this.loadProducts();
    if (tab === 'compras' && this.purchaseOrders.length === 0) this.loadPurchaseOrders();
  }

  // ---------- Perfil ----------
  loadProfile(): void {
    this.inventario.getMySupplierProfile().subscribe({
      next: (data) => {
        this.profile = data;
        this.contactForm = {
          contact_name: data.contact_name || '',
          email: data.email || '',
          phone: data.phone || '',
          address: data.address || '',
        };
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo cargar tu ficha de proveedor.'),
    });
  }

  saveContact(): void {
    this.error = '';
    this.success = '';
    this.inventario.updateMySupplierProfile(this.contactForm).subscribe({
      next: (data) => {
        this.profile = data;
        this.success = 'Datos de contacto actualizados correctamente.';
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo actualizar tu ficha.'),
    });
  }

  // ---------- Mis productos (con foto y disponibilidad) ----------
  loadProducts(): void {
    this.loading = true;
    this.inventario.getMySuppliedProducts().subscribe({
      next: (data) => {
        this.products = data;
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudieron cargar tus productos.';
        this.loading = false;
      },
    });
  }

  get productCards(): ProductCard[] {
    const byProduct = new Map<number, ProductCard>();
    for (const p of this.products) {
      let card = byProduct.get(p.product_id);
      if (!card) {
        card = {
          product_id: p.product_id,
          product_name: p.product_name,
          image_url: p.image_url,
          supplier_status: p.supplier_status || 'DISPONIBLE',
          total_stock: 0,
          variants: [],
        };
        byProduct.set(p.product_id, card);
      }
      card.image_url = card.image_url || p.image_url;
      card.total_stock += Number(p.stock_actual) || 0;
      card.variants.push(p);
    }
    return Array.from(byProduct.values());
  }

  setProductStatus(card: ProductCard, status: SupplierProductStatus): void {
    if (card.supplier_status === status) return;
    if (status === 'DESCONTINUADO' && !confirm(`¿Confirmas que ya no traes "${card.product_name}"? Casa Matriz no podrá pedírtela.`)) return;
    this.error = '';
    this.inventario.updateMyProductStatus(card.product_id, status).subscribe({
      next: () => {
        this.products.filter((p) => p.product_id === card.product_id).forEach((p) => (p.supplier_status = status));
        this.success = `"${card.product_name}" marcada como ${this.productStatusOptions.find((o) => o.value === status)?.label}.`;
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo actualizar la disponibilidad.'),
    });
  }

  loadPurchaseOrders(): void {
    this.loading = true;
    this.inventario.getPurchaseOrders().subscribe({
      next: (data) => {
        this.purchaseOrders = data;
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudo cargar tu historial de compras.';
        this.loading = false;
      },
    });
  }

  // ---------- Bandeja de pedidos de reposición ----------
  get pendingCount(): number {
    return this.reorders.filter((r) => r.status === 'PENDING').length;
  }

  get visibleReorders(): any[] {
    if (this.reorderFilter === 'TODOS') return this.reorders;
    return this.reorders.filter((r) => ['PENDING', 'ACCEPTED', 'SHIPPED'].includes(r.status));
  }

  loadReorders(): void {
    this.inventario.getMyReorderRequests().subscribe({
      next: (data) => (this.reorders = data),
      error: (e) => (this.error = e.error?.detail || 'No se pudieron cargar los pedidos de reposición.'),
    });
  }

  startAccept(r: any): void {
    this.respondingId = r.id;
    this.respondForm = { estimated_delivery: '', supplier_notes: '' };
  }

  confirmAccept(r: any): void {
    if (!this.respondForm.estimated_delivery) {
      this.error = 'Indica la fecha estimada de entrega en la sucursal.';
      return;
    }
    this.respond(r, 'ACCEPTED');
  }

  reject(r: any): void {
    const reason = prompt(`¿Por qué rechazas el pedido ${r.code}? (opcional)`);
    if (reason === null) return;
    this.respondForm = { estimated_delivery: '', supplier_notes: reason };
    this.respond(r, 'REJECTED');
  }

  private respond(r: any, status: 'ACCEPTED' | 'REJECTED'): void {
    this.error = '';
    this.inventario.respondReorderRequest(r.id, {
      status,
      estimated_delivery: status === 'ACCEPTED' ? this.respondForm.estimated_delivery : null,
      supplier_notes: this.respondForm.supplier_notes || null,
    }).subscribe({
      next: () => {
        this.success = status === 'ACCEPTED'
          ? `Pedido ${r.code} aceptado. Despáchalo a la sucursal ${r.target_branch_name}.`
          : `Pedido ${r.code} rechazado.`;
        this.respondingId = null;
        this.loadReorders();
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo responder el pedido.'),
    });
  }

  markShipped(r: any): void {
    if (!confirm(`¿Confirmas que despachaste ${r.requested_quantity} unidades de ${r.product_name} hacia ${r.target_branch_name}?`)) return;
    this.inventario.markReorderShipped(r.id).subscribe({
      next: () => {
        this.success = `Pedido ${r.code} marcado como enviado. La sucursal confirmará la recepción.`;
        this.loadReorders();
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo marcar el envío.'),
    });
  }

  // ---------- Ofertas de nuevos modelos (con galería de fotos) ----------
  emptyOfferForm() {
    return {
      product_name: '',
      description: '',
      category: '',
      unit_cost: null as number | null,
      suggested_retail_price: null as number | null,
      min_order_quantity: 10,
      available_quantity: 100,
      sizes_available: 'S, M, L, XL',
      colors_available: '',
      image_urls: [] as string[],
      image_url: '' as string,
    };
  }

  loadOffers(): void {
    this.inventario.getMyOffers().subscribe({
      next: (data) => (this.offers = data),
      error: (e) => (this.error = e.error?.detail || 'No se pudieron cargar tus ofertas.'),
    });
  }

  async onOfferPhotosSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []).filter((f) => f.type.startsWith('image/'));
    input.value = '';
    const room = MAX_OFFER_PHOTOS - this.offerForm.image_urls.length;
    if (files.length === 0 || room <= 0) {
      if (room <= 0) this.error = `Puedes subir hasta ${MAX_OFFER_PHOTOS} fotos por prenda.`;
      return;
    }
    this.processingPhotos = true;
    this.error = '';
    try {
      for (const file of files.slice(0, room)) {
        this.offerForm.image_urls.push(await this.compressImage(file));
      }
      if (!this.offerForm.image_url) this.offerForm.image_url = this.offerForm.image_urls[0];
    } catch {
      this.error = 'No se pudo procesar una de las fotos.';
    } finally {
      this.processingPhotos = false;
    }
  }

  setCoverPhoto(url: string): void {
    this.offerForm.image_url = url;
  }

  removePhoto(index: number): void {
    const [removed] = this.offerForm.image_urls.splice(index, 1);
    if (removed === this.offerForm.image_url) {
      this.offerForm.image_url = this.offerForm.image_urls[0] || '';
    }
  }

  submitOffer(): void {
    this.error = '';
    const f = this.offerForm;
    if (f.product_name.trim().length < 2 || f.description.trim().length < 5) {
      this.error = 'Completa el nombre del modelo y una descripción (mínimo 5 caracteres).';
      return;
    }
    if (!f.unit_cost || f.unit_cost <= 0 || !f.suggested_retail_price || f.suggested_retail_price <= 0) {
      this.error = 'Indica el costo unitario y el precio sugerido de venta (mayores a 0).';
      return;
    }
    if (!f.colors_available.trim() || !f.sizes_available.trim()) {
      this.error = 'Indica las tallas y colores disponibles.';
      return;
    }
    if (f.image_urls.length === 0) {
      this.error = 'Agrega al menos una foto de la prenda para que Casa Matriz pueda evaluarla.';
      return;
    }
    this.sendingOffer = true;
    this.inventario.createSupplierOffer({
      ...f,
      product_name: f.product_name.trim(),
      description: f.description.trim(),
      category: f.category.trim() || 'Prendas Casuales',
      image_url: f.image_url || f.image_urls[0],
    }).subscribe({
      next: () => {
        this.sendingOffer = false;
        this.success = 'Oferta enviada a Casa Matriz. Verás aquí cuando sea aprobada o rechazada.';
        this.offerForm = this.emptyOfferForm();
        this.loadOffers();
      },
      error: (e) => {
        this.sendingOffer = false;
        this.error = e.error?.detail || 'No se pudo enviar la oferta.';
      },
    });
  }

  offerPhotos(o: any): string[] {
    return o.image_urls?.length ? o.image_urls : (o.image_url ? [o.image_url] : []);
  }

  shownPhoto(o: any): string | null {
    const photos = this.offerPhotos(o);
    const idx = this.galleryIndex[o.id];
    return idx != null && photos[idx] ? photos[idx] : (o.image_url || photos[0] || null);
  }

  canChangeAvailability(o: any): boolean {
    return !['PENDING', 'REJECTED'].includes(o.status);
  }

  toggleOfferAvailability(offer: any, status: SupplierProductStatus): void {
    this.error = '';
    this.inventario.updateOfferStatus(offer.id, { status }).subscribe({
      next: (updated) => {
        offer.status = updated.status;
        this.success = `"${offer.product_name}": ${this.offerStatusLabels[updated.status] || updated.status}.`;
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo actualizar la disponibilidad.'),
    });
  }

  updateOfferAvailableQuantity(offer: any, qtyStr: string): void {
    const qty = parseInt(qtyStr, 10);
    if (isNaN(qty) || qty < 0) return;
    this.error = '';
    const status = qty === 0 ? 'AGOTADO' : (offer.status === 'AGOTADO' ? 'DISPONIBLE' : offer.status === 'APPROVED' ? 'DISPONIBLE' : offer.status);
    this.inventario.updateOfferStatus(offer.id, { status, available_quantity: qty }).subscribe({
      next: (updated) => {
        offer.available_quantity = updated.available_quantity;
        offer.status = updated.status;
        this.success = `Stock disponible de "${offer.product_name}" actualizado a ${qty} unidades.`;
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo actualizar el stock.'),
    });
  }

  /** Redimensiona y comprime la foto en el navegador (se guarda en la base, sobrevive a los deploys). */
  private compressImage(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = () => {
        const img = new Image();
        img.onerror = reject;
        img.onload = () => {
          const scale = Math.min(1, PHOTO_MAX_SIDE / Math.max(img.width, img.height));
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(img.width * scale);
          canvas.height = Math.round(img.height * scale);
          const ctx = canvas.getContext('2d');
          if (!ctx) return reject(new Error('canvas'));
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', PHOTO_JPEG_QUALITY));
        };
        img.src = reader.result as string;
      };
      reader.readAsDataURL(file);
    });
  }
}
