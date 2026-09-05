import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { InventarioService, InventoryAdjustment } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

/**
 * [CU38] Gestionar ajustes de inventario (mermas, daños, pérdidas, sobrantes de conteo).
 * El ajuste descuenta/incrementa existencias y deja un movimiento AJUSTE auditable en el
 * libro mayor, valorado al costo promedio ponderado vigente.
 */
@Component({
  selector: 'app-adjustments',
  templateUrl: './adjustments.component.html',
  styleUrls: ['./adjustments.component.css'],
})
export class AdjustmentsComponent implements OnInit {
  branches: any[] = [];
  variants: { id: number; label: string; imageUrl?: string | null }[] = [];
  ledger: any[] = [];

  branchId: number | null = null;
  variantId: number | null = null;
  quantity = -1;
  reason: InventoryAdjustment['reason'] = 'MERMA';
  note = '';

  loading = false;
  saving = false;
  error = '';
  success = '';

  readonly reasons: { value: InventoryAdjustment['reason']; label: string }[] = [
    { value: 'MERMA', label: 'Merma' },
    { value: 'DANO', label: 'Daño' },
    { value: 'PERDIDA', label: 'Pérdida / robo' },
    { value: 'CONTEO', label: 'Ajuste por conteo físico' },
  ];

  constructor(private inventario: InventarioService, private catalogo: CatalogoService) {}

  ngOnInit(): void {
    this.loading = true;
    forkJoin({
      branches: this.catalogo.getBranches(),
      products: this.catalogo.getProducts(),
    }).subscribe({
      next: ({ branches, products }) => {
        this.branches = branches;
        this.variants = [];
        for (const p of products) {
          for (const v of p.variants || []) {
            const colorImg = (p.images || []).find((i: any) => i.color_id === v.color_id);
            const primaryImg = (p.images || []).find((i: any) => i.is_primary) || (p.images || [])[0];
            const rawUrl = colorImg?.image_url || primaryImg?.image_url || null;
            this.variants.push({
              id: v.id,
              label: `${p.name} · ${v.color?.name || ''} ${v.size?.name || ''} · ${v.sku}`,
              imageUrl: rawUrl ? this.catalogo.resolveImageUrl(rawUrl) : null,
            });
          }
        }
        this.loading = false;
      },
      error: () => { this.error = 'No se pudieron cargar los datos.'; this.loading = false; },
    });
    this.loadLedger();
  }

  get selectedVariant(): any {
    return this.variants.find((v) => v.id === this.variantId);
  }

  /** Las mermas, daños y pérdidas siempre restan del stock: si el motivo es de salida y la
   *  cantidad quedó positiva, se cambia de signo automáticamente. */
  onReasonChange(): void {
    const salida = this.reason === 'MERMA' || this.reason === 'DANO' || this.reason === 'PERDIDA';
    if (salida && this.quantity > 0) this.quantity = -this.quantity;
  }

  loadLedger(): void {
    this.inventario.getLedger().subscribe({
      next: (data) => (this.ledger = data.filter((m: any) => m.movement_type === 'AJUSTE').slice(0, 12)),
      error: () => {},
    });
  }

  // [CU38 - Paso 1] / [DSC038 - Paso 1] +registrarAjuste(datos)
  register(): void {
    this.error = '';
    this.success = '';
    if (!this.branchId || !this.variantId || !this.quantity) {
      this.error = 'Selecciona sucursal, variante y una cantidad distinta de cero.';
      return;
    }
    const payload: InventoryAdjustment = {
      branch_id: Number(this.branchId),
      variant_id: Number(this.variantId),
      quantity: Number(this.quantity),
      reason: this.reason,
      note: this.note || undefined,
    };
    this.saving = true;
    // [CU38 - Paso 2] / [DSC038 - Paso 2] +create_adjustment(datos)
    this.inventario.createAdjustment(payload).subscribe({
      next: (res) => {
        this.saving = false;
        this.success = `Ajuste registrado (${res.reference_id}). Stock resultante: ${res.stock_resultante}.`;
        this.note = '';
        this.loadLedger();
      },
      error: (e) => {
        this.saving = false;
        this.error = e.error?.detail || 'No se pudo registrar el ajuste.';
      },
    });
  }
}
