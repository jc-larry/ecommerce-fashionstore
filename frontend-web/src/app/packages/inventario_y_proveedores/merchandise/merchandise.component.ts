import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { InventarioService } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

interface IntakeRow {
  variant_id: number | null;
  quantity: number;
  unit_cost: number;
}

@Component({
  selector: 'app-merchandise',
  templateUrl: './merchandise.component.html',
  styleUrls: ['./merchandise.component.css']
})
export class MerchandiseComponent implements OnInit {
  suppliers: any[] = [];
  branches: any[] = [];
  variants: any[] = []; // { id, sku, label }
  recentEntries: any[] = [];

  loading = false;
  saving = false;
  error = '';
  success = '';

  supplierId: number | null = null;
  branchId: number | null = null;
  rows: IntakeRow[] = [this.emptyRow()];

  constructor(private inventario: InventarioService, private catalogo: CatalogoService) {}

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
          for (const v of p.variants || []) {
            this.variants.push({
              id: v.id,
              sku: v.sku,
              label: `${p.name} · ${v.color?.name || ''} ${v.size?.name || ''} · ${v.sku}`,
            });
          }
        }
        this.loading = false;
      },
      error: () => { this.error = 'No se pudieron cargar los datos de mercadería.'; this.loading = false; },
    });
    this.loadLedger();
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

  subtotal(r: IntakeRow): number {
    return (Number(r.quantity) || 0) * (Number(r.unit_cost) || 0);
  }

  get total(): number {
    return this.rows.reduce((acc, r) => acc + this.subtotal(r), 0);
  }

  loadLedger(): void {
    this.inventario.getLedger().subscribe({
      next: (data) => {
        // Agrupar movimientos de INGRESO por documento de referencia (OC-x)
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
   * [CU10] Registrar compras/ingresos de mercadería
   * @description Registra un lote de prendas provenientes de un proveedor, incrementando automáticamente
   * el stock físico de la sucursal y generando un registro histórico en el libro diario de inventario.
   */
  // [CU10 - Paso 1] / [DSC010 - Paso 1] +registrar(datos)
  register(): void {
    this.error = '';
    this.success = '';

    const details = this.rows
      .filter((r) => r.variant_id && r.quantity > 0 && r.unit_cost > 0)
      .map((r) => ({ variant_id: Number(r.variant_id), quantity: Number(r.quantity), unit_cost: Number(r.unit_cost) }));

    if (!this.supplierId || !this.branchId || details.length === 0) {
      this.error = 'Selecciona proveedor, sucursal y al menos una prenda con cantidad y costo.';
      return;
    }

    this.saving = true;
    // [CU10 - Paso 2] / [DSC010 - Paso 2] +register_intake(datos)
    this.inventario
      .registerIntake({ supplier_id: Number(this.supplierId), branch_id: Number(this.branchId), details })
      .subscribe({
        next: () => {
          this.saving = false;
          // [CU10 - Paso 7] / [DSC010 - Paso 7] +Notificar éxito
          this.success = 'Ingreso de mercadería registrado y stock actualizado.';
          this.rows = [this.emptyRow()];
          this.loadLedger();
        },
        error: (e) => {
          this.saving = false;
          this.error = e.error?.detail || 'Error al registrar el ingreso.';
        },
      });
  }
}
