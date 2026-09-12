import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { InventarioService, PurchaseOrderCreate } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';

export interface IntakeRow {
  variant_id: number | null;
  quantity: number;
  unit_cost: number;
}

export interface VariantDisplay {
  id: number;
  sku: string;
  label: string;
  productName: string;
  colorName: string;
  colorHex: string;
  sizeName: string;
  salePrice: number;
  imageUrl: string | null;
}

@Component({
  selector: 'app-merchandise',
  templateUrl: './merchandise.component.html',
  styleUrls: ['./merchandise.component.css']
})
export class MerchandiseComponent implements OnInit {
  suppliers: any[] = [];
  branches: any[] = [];
  variants: VariantDisplay[] = [];
  recentEntries: any[] = [];
  inventoryMap: Record<number, { stock: number; avg_cost: number }> = {};

  loading = false;
  saving = false;
  loadingInventory = false;
  error = '';
  success = '';

  supplierId: number | null = null;
  branchId: number | null = null;
  invoiceNumber = '';
  shippingCost = 0;
  notes = '';
  rows: IntakeRow[] = [this.emptyRow()];

  constructor(
    private inventario: InventarioService,
    private catalogo: CatalogoService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.loading = true;
    forkJoin({
      suppliers: this.inventario.getSuppliers(),
      branches: this.catalogo.getBranches(),
      products: this.catalogo.getProducts(),
    }).subscribe({
      next: ({ suppliers, branches, products }) => {
        this.suppliers = suppliers;
        this.branches = branches;
        this.variants = [];

        for (const p of products) {
          const pPrice = Number(p.base_price) || 0;
          for (const v of p.variants || []) {
            const colorImg = (p.images || []).find((i: any) => i.color_id === v.color_id);
            const primaryImg = (p.images || []).find((i: any) => i.is_primary) || (p.images || [])[0];
            const rawUrl = colorImg?.image_url || primaryImg?.image_url || null;
            const imageUrl = rawUrl ? this.catalogo.resolveImageUrl(rawUrl) : null;

            const salePrice = (v as any).price_override ? Number((v as any).price_override) : pPrice;
            const colorName = v.color?.name || 'Estándar';
            const colorHex = v.color?.hex_code || '#999999';
            const sizeName = v.size?.name || 'Única';

            this.variants.push({
              id: v.id,
              sku: v.sku,
              label: `${p.name} · ${colorName} / ${sizeName} · SKU: ${v.sku}`,
              productName: p.name,
              colorName,
              colorHex,
              sizeName,
              salePrice,
              imageUrl,
            });
          }
        }
        this.loading = false;

        // Sincronizar automáticamente con la sucursal activa
        this.branchContext.activeBranch$.subscribe((active) => {
          if (active) {
            this.branchId = active.id;
          } else {
            this.branchId = null;
          }
          this.onBranchChange();
          this.loadLedger(this.branchId || undefined);
        });
      },
      error: () => {
        this.error = 'No se pudieron cargar los datos de mercadería.';
        this.loading = false;
      },
    });
  }

  onBranchChange(): void {
    if (!this.branchId) {
      this.inventoryMap = {};
      return;
    }
    this.loadingInventory = true;
    this.inventario.getInventory(this.branchId).subscribe({
      next: (items) => {
        this.inventoryMap = {};
        for (const item of items) {
          this.inventoryMap[item.variant_id] = {
            stock: item.stock_actual,
            avg_cost: Number(item.avg_cost) || 0,
          };
        }
        this.loadingInventory = false;
      },
      error: () => {
        this.loadingInventory = false;
      }
    });
  }

  getVariant(id: number | null): VariantDisplay | undefined {
    return this.variants.find((v) => v.id === id);
  }

  getCurrentStock(variantId: number | null): number {
    if (!variantId || !this.inventoryMap[variantId]) return 0;
    return this.inventoryMap[variantId].stock;
  }

  getCurrentAvgCost(variantId: number | null): number {
    if (!variantId || !this.inventoryMap[variantId]) return 0;
    return this.inventoryMap[variantId].avg_cost;
  }

  emptyRow(): IntakeRow {
    return { variant_id: null, quantity: 1, unit_cost: 0 };
  }

  addRow(): void {
    this.rows.push(this.emptyRow());
  }

  removeRow(i: number): void {
    this.rows.splice(i, 1);
    if (this.rows.length === 0) this.rows.push(this.emptyRow());
  }

  // --- CÁLCULOS CONTABLES EN TIEMPO REAL ---
  get subtotalRaw(): number {
    return this.rows.reduce((acc, r) => acc + (Number(r.quantity) || 0) * (Number(r.unit_cost) || 0), 0);
  }

  get safeShippingCost(): number {
    return Math.max(0, Number(this.shippingCost) || 0);
  }

  get freightFactor(): number {
    const raw = this.subtotalRaw;
    if (raw <= 0 || this.safeShippingCost <= 0) return 0;
    return this.safeShippingCost / raw;
  }

  get totalWithShipping(): number {
    return this.subtotalRaw + this.safeShippingCost;
  }

  get totalPieces(): number {
    return this.rows.reduce((acc, r) => acc + (Number(r.quantity) || 0), 0);
  }

  getLandedCost(r: IntakeRow): number {
    const base = Number(r.unit_cost) || 0;
    return base * (1 + this.freightFactor);
  }

  getRowSubtotalLanded(r: IntakeRow): number {
    return (Number(r.quantity) || 0) * this.getLandedCost(r);
  }

  /** Simulación del nuevo Costo Promedio Ponderado para una variante */
  getSimulatedNewCpp(r: IntakeRow): number {
    const qty = Number(r.quantity) || 0;
    const landed = this.getLandedCost(r);
    const stockPrev = this.getCurrentStock(r.variant_id);
    const cppPrev = this.getCurrentAvgCost(r.variant_id);

    const totalStock = stockPrev + qty;
    if (totalStock <= 0) return landed;
    return (stockPrev * cppPrev + qty * landed) / totalStock;
  }

  /** Margen bruto comercial proyectado: (PVP - NuevoCPP) / PVP */
  getProjectedMarginPercent(r: IntakeRow): number {
    const v = this.getVariant(r.variant_id);
    if (!v || v.salePrice <= 0) return 0;
    const newCpp = this.getSimulatedNewCpp(r);
    return ((v.salePrice - newCpp) / v.salePrice) * 100;
  }

  loadLedger(branchId?: number): void {
    const targetBranchId = branchId !== undefined ? branchId : (this.branchId || undefined);
    this.inventario.getLedger(targetBranchId).subscribe({
      next: (data) => {
        const groups: Record<string, any> = {};
        for (const m of data.filter((x: any) => x.movement_type === 'INGRESO')) {
          const key = m.reference_id || `mov-${m.id}`;
          groups[key] ??= { ref: key, date: m.created_at, total: 0, items: 0 };
          groups[key].total += m.quantity * m.unit_cost;
          groups[key].items += 1;
        }
        this.recentEntries = Object.values(groups)
          .sort((a: any, b: any) => (a.date < b.date ? 1 : -1))
          .slice(0, 8);
      },
      error: () => {},
    });
  }

  /**
   * [CU10] Registrar compras/ingresos de mercadería con costeo landed y CPP
   */
  register(): void {
    this.error = '';
    this.success = '';

    const validDetails = this.rows
      .filter((r) => r.variant_id && Number(r.quantity) > 0 && Number(r.unit_cost) > 0)
      .map((r) => ({
        variant_id: Number(r.variant_id),
        quantity: Number(r.quantity),
        unit_cost: Number(r.unit_cost),
      }));

    if (!this.supplierId) {
      this.error = 'Por favor, selecciona el proveedor al que se le realizó la compra.';
      return;
    }

    if (!this.branchId) {
      this.error = 'Por favor, selecciona la sucursal de destino que recibirá la mercadería.';
      return;
    }

    if (this.shippingCost && Number(this.shippingCost) < 0) {
      this.error = 'El costo de transporte o flete no puede ser un valor negativo.';
      return;
    }

    if (this.rows.length === 0) {
      this.error = 'Debes incluir al menos una prenda en la lista para registrar el ingreso.';
      return;
    }

    for (let i = 0; i < this.rows.length; i++) {
      const r = this.rows[i];
      if (!r.variant_id) {
        this.error = `Por favor, selecciona la prenda en la fila #${i + 1} o elimina esa fila si no la necesitas.`;
        return;
      }
      const q = Number(r.quantity);
      if (isNaN(q) || q <= 0) {
        this.error = `En la fila #${i + 1}, ingresa una cantidad válida de prendas (debe ser mayor a 0).`;
        return;
      }
      const c = Number(r.unit_cost);
      if (isNaN(c) || c <= 0) {
        this.error = `En la fila #${i + 1}, el costo unitario debe ser mayor a Bs. 0.00.`;
        return;
      }
    }

    this.saving = true;

    const payload: PurchaseOrderCreate = {
      supplier_id: Number(this.supplierId),
      branch_id: Number(this.branchId),
      invoice_number: this.invoiceNumber.trim() || undefined,
      shipping_cost: this.safeShippingCost,
      notes: this.notes.trim() || undefined,
      details: validDetails,
    };

    this.inventario.registerIntake(payload).subscribe({
      next: (res) => {
        this.saving = false;
        const refName = res.invoice_number ? `Factura ${res.invoice_number}` : `Orden Nº ${res.id}`;
        this.success = `¡Mercadería ingresada con éxito (${refName})! El inventario de la sucursal y los costos promedio han sido actualizados.`;
        this.rows = [this.emptyRow()];
        this.invoiceNumber = '';
        this.shippingCost = 0;
        this.notes = '';
        this.onBranchChange();
        this.loadLedger();
      },
      error: (e) => {
        this.saving = false;
        this.error = e.error?.detail || 'No se pudo registrar el ingreso. Verifica los datos e intenta nuevamente.';
      },
    });
  }
}
