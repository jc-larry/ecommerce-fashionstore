import { Component, OnInit } from '@angular/core';
import { InventarioService } from '../inventario.service';
import { CatalogoService } from '../../paquete_catalogo_y_tiendas/catalogo.service';
import { AuthService } from '../../paquete_seguridad_usuarios/auth.service';

type RequestsTab = 'reposicion' | 'ofertas';

/**
 * [CU08 / CU10] Casa Matriz ↔ Proveedores.
 * - Solicitudes de reposición: el administrador elige proveedor, prenda (variante) y la
 *   SUCURSAL que necesita la reposición; el proveedor la recibe en su bandeja.
 * - Ofertas recibidas: nuevos modelos que los proveedores proponen a Casa Matriz.
 * - Para un ENCARGADO: solo las reposiciones dirigidas a su sucursal, para confirmar la recepción.
 */
@Component({
  selector: 'app-supplier-requests',
  templateUrl: './supplier-requests.component.html',
})
export class SupplierRequestsComponent implements OnInit {
  activeTab: RequestsTab = 'reposicion';
  error = '';
  success = '';

  suppliers: any[] = [];
  branches: any[] = [];
  products: any[] = [];

  reorders: any[] = [];
  statusFilter = '';

  showForm = false;
  form = this.emptyForm();
  branchInventory: any[] = [];
  saving = false;

  offers: any[] = [];
  offerStatusFilter = 'PENDING';
  reviewingOffer: any = null;
  reviewForm = { target_branch_id: null as number | null, admin_notes: '', product_id: null as number | null };
  photoPreview: string | null = null;

  readonly reorderStatusLabels: Record<string, string> = {
    PENDING: 'Esperando al proveedor',
    ACCEPTED: 'Aceptado por el proveedor',
    SHIPPED: 'En camino a la sucursal',
    RECEIVED: 'Recibido en sucursal',
    REJECTED: 'Rechazado por el proveedor',
    CANCELLED: 'Anulado',
  };

  readonly isCentral: boolean;

  constructor(private inventario: InventarioService, private catalogo: CatalogoService, auth: AuthService) {
    this.isCentral = auth.isCentralUser();
  }

  ngOnInit(): void {
    if (!this.isCentral) {
      this.loadReorders();
      return;
    }
    this.inventario.getSuppliers().subscribe({ next: (s) => (this.suppliers = s.filter((x: any) => x.is_active)) });
    this.catalogo.getBranches().subscribe({ next: (b) => (this.branches = b.filter((x: any) => x.is_active)) });
    this.catalogo.getProducts().subscribe({ next: (p) => (this.products = p) });
    this.loadReorders();
    this.loadOffers();
  }

  setTab(tab: RequestsTab): void {
    this.activeTab = tab;
    this.error = '';
    this.success = '';
  }

  // ---------- Solicitudes de reposición ----------
  emptyForm() {
    return {
      supplier_id: null as number | null,
      target_branch_id: null as number | null,
      product_id: null as number | null,
      variant_id: null as number | null,
      requested_quantity: 10,
      unit_cost: 0,
    };
  }

  loadReorders(): void {
    this.inventario.getReorderRequests({ status_filter: this.statusFilter || undefined }).subscribe({
      next: (data) => (this.reorders = data),
      error: (e) => (this.error = e.error?.detail || 'No se pudieron cargar las solicitudes de reposición.'),
    });
  }

  openNew(prefill?: { branchId?: number; variantId?: number }): void {
    this.form = this.emptyForm();
    this.branchInventory = [];
    this.showForm = true;
    if (prefill?.branchId) {
      this.form.target_branch_id = prefill.branchId;
      this.onBranchChange();
    }
  }

  get selectedProductVariants(): any[] {
    const p = this.products.find((x) => x.id === this.form.product_id);
    return p?.variants || [];
  }

  /** Prendas con stock en o bajo el mínimo en la sucursal elegida: candidatas a reposición. */
  get lowStockItems(): any[] {
    return this.branchInventory.filter((i) => i.stock_actual <= i.stock_minimo);
  }

  get stockAtBranch(): number | null {
    if (!this.form.variant_id || !this.form.target_branch_id) return null;
    const row = this.branchInventory.find((i) => i.variant_id === this.form.variant_id);
    return row ? row.stock_actual : 0;
  }

  discontinuedWarning: string | null = null;

  onBranchChange(): void {
    this.branchInventory = [];
    if (!this.form.target_branch_id) return;
    this.inventario.getInventory(this.form.target_branch_id).subscribe({
      next: (rows) => (this.branchInventory = rows),
    });
  }

  onSupplierChange(): void {
    this.checkDiscontinuedStatus();
  }

  onProductChange(): void {
    this.form.variant_id = null;
    this.checkDiscontinuedStatus();
  }

  onVariantChange(): void {
    const row = this.branchInventory.find((i) => i.variant_id === this.form.variant_id);
    if (row && row.avg_cost > 0) this.form.unit_cost = Number(row.avg_cost);
    this.checkDiscontinuedStatus();
  }

  /** Consulta en el backend si el proveedor todavía trae la prenda; si no, se bloquea el pedido. */
  checkDiscontinuedStatus(): void {
    this.discontinuedWarning = null;
    const supplierId = this.form.supplier_id;
    const productId = this.form.product_id;
    if (!supplierId || !productId) return;
    this.inventario.getSupplierProductStatus(supplierId, productId).subscribe({
      next: ({ status }) => {
        if (this.form.supplier_id !== supplierId || this.form.product_id !== productId) return;
        if (status === 'DESCONTINUADO') {
          this.discontinuedWarning = 'El proveedor indicó que ya no trae esta prenda. Elige otro proveedor.';
        } else if (status === 'AGOTADO') {
          this.discontinuedWarning = 'El proveedor indicó que esta prenda está agotada. No se le puede pedir por ahora.';
        }
      },
    });
  }

  get selectedProductImage(): string | null {
    const p = this.products.find((x) => x.id === this.form.product_id);
    if (!p?.images?.length) return null;
    const variant = (p.variants || []).find((v: any) => v.id === this.form.variant_id);
    const byColor = variant ? p.images.find((i: any) => i.color_id === variant.color?.id) : null;
    return (byColor || p.images.find((i: any) => i.is_primary) || p.images[0]).image_url;
  }

  offerPhotos(o: any): string[] {
    return o.image_urls?.length ? o.image_urls : (o.image_url ? [o.image_url] : []);
  }

  pickLowStock(item: any): void {
    const product = this.products.find((p) => (p.variants || []).some((v: any) => v.id === item.variant_id));
    this.form.product_id = product?.id ?? null;
    this.form.variant_id = item.variant_id;
    this.form.requested_quantity = Math.max((item.stock_maximo || 0) - item.stock_actual, 1);
    if (item.avg_cost > 0) this.form.unit_cost = Number(item.avg_cost);
    this.checkDiscontinuedStatus();
  }

  saveReorder(): void {
    this.error = '';
    const f = this.form;
    if (!f.supplier_id || !f.target_branch_id || !f.variant_id) {
      this.error = 'Selecciona proveedor, sucursal destino y la prenda (talla/color).';
      return;
    }
    if (!f.requested_quantity || f.requested_quantity <= 0 || f.unit_cost < 0) {
      this.error = 'La cantidad debe ser mayor a 0 y el costo no puede ser negativo.';
      return;
    }
    this.saving = true;
    this.inventario.createReorderRequest({
      supplier_id: f.supplier_id,
      variant_id: f.variant_id,
      target_branch_id: f.target_branch_id,
      requested_quantity: Number(f.requested_quantity),
      unit_cost: Number(f.unit_cost),
    }).subscribe({
      next: (r) => {
        this.saving = false;
        this.showForm = false;
        this.success = `Solicitud ${r.code} enviada a ${r.supplier_name} para la sucursal ${r.target_branch_name}.`;
        this.loadReorders();
      },
      error: (e) => {
        this.saving = false;
        this.error = e.error?.detail || 'No se pudo crear la solicitud.';
      },
    });
  }

  cancelReorder(r: any): void {
    if (!confirm(`¿Anular la solicitud ${r.code}?`)) return;
    this.inventario.cancelReorderRequest(r.id).subscribe({
      next: () => {
        this.success = `Solicitud ${r.code} anulada.`;
        this.loadReorders();
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo anular la solicitud.'),
    });
  }

  /** [CU10] El encargado confirma que la mercadería llegó: el stock ingresa al inventario de su sucursal. */
  receive(r: any): void {
    if (!confirm(`¿Confirmas que recibiste ${r.requested_quantity} unidades de ${r.product_name} (${r.variant_label}) de ${r.supplier_name}?`)) return;
    this.inventario.markReorderReceived(r.id).subscribe({
      next: () => {
        this.success = `Recepción de ${r.code} confirmada: ${r.requested_quantity} unidades ingresaron al inventario de ${r.target_branch_name}.`;
        this.loadReorders();
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo confirmar la recepción.'),
    });
  }

  // ---------- Ofertas de proveedores ----------
  get pendingOffers(): number {
    return this.offers.filter((o) => o.status === 'PENDING').length;
  }

  get visibleOffers(): any[] {
    return this.offerStatusFilter ? this.offers.filter((o) => o.status === this.offerStatusFilter) : this.offers;
  }

  loadOffers(): void {
    this.inventario.getSupplierOffers().subscribe({
      next: (data) => (this.offers = data),
      error: (e) => (this.error = e.error?.detail || 'No se pudieron cargar las ofertas.'),
    });
  }

  startReview(o: any): void {
    this.reviewingOffer = o;
    this.reviewForm = { target_branch_id: null, admin_notes: '', product_id: null };
  }

  review(status: 'APPROVED' | 'REJECTED'): void {
    const o = this.reviewingOffer;
    if (!o) return;
    this.inventario.reviewSupplierOffer(o.id, {
      status,
      admin_notes: this.reviewForm.admin_notes || undefined,
      target_branch_id: status === 'APPROVED' ? this.reviewForm.target_branch_id : null,
      product_id: status === 'APPROVED' ? this.reviewForm.product_id : null,
    }).subscribe({
      next: () => {
        this.success = `Oferta "${o.product_name}" ${status === 'APPROVED' ? 'aprobada' : 'rechazada'}. El proveedor verá la respuesta en su portal.`;
        this.reviewingOffer = null;
        this.loadOffers();
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo registrar la revisión.'),
    });
  }
}
