import { Component, OnInit } from '@angular/core';
import { InventarioService, InventoryValuation, InventoryValuationItem } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';

/**
 * [CU37] Consultar valoración de inventario / capital invertido.
 * Presenta el estado patrimonial del inventario valorado al Costo Promedio Ponderado (CPP),
 * junto con su valor de realización comercial y margen bruto comercial proyectado.
 */
@Component({
  selector: 'app-valuation',
  templateUrl: './valuation.component.html',
  styleUrls: ['./valuation.component.css'],
})
export class ValuationComponent implements OnInit {
  branches: any[] = [];
  branchId: number | null = null;
  data: InventoryValuation | null = null;
  searchTerm = '';
  loading = false;
  error = '';

  constructor(
    private inventario: InventarioService,
    private catalogo: CatalogoService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.catalogo.getBranches().subscribe({
      next: (b) => (this.branches = b),
      error: () => {},
    });
    this.branchContext.activeBranch$.subscribe((active) => {
      this.branchId = active ? active.id : null;
      this.load();
    });
  }

  onLocalBranchChange(): void {
    this.branchContext.setActiveBranchById(this.branchId);
    this.load();
  }

  // [CU37 - Paso 1] / [DSC037 - Paso 1] +consultarValoracion(sucursal?)
  load(): void {
    this.loading = true;
    this.error = '';
    // [CU37 - Paso 2] / [DSC037 - Paso 2] +get_valuation(branch?)
    this.inventario.getValuation(this.branchId ? Number(this.branchId) : undefined).subscribe({
      next: (d) => {
        this.data = d;
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudo obtener la valoración del inventario.';
        this.loading = false;
      },
    });
  }

  resolveImg(url?: string | null): string {
    return this.catalogo.resolveImageUrl(url);
  }

  get filteredItems(): InventoryValuationItem[] {
    if (!this.data?.items) return [];
    if (!this.searchTerm.trim()) return this.data.items;
    const term = this.searchTerm.toLowerCase();
    return this.data.items.filter(
      (it) =>
        (it.product_name && it.product_name.toLowerCase().includes(term)) ||
        (it.sku && it.sku.toLowerCase().includes(term)) ||
        (it.color_name && it.color_name.toLowerCase().includes(term)) ||
        (it.size_name && it.size_name.toLowerCase().includes(term)) ||
        (it.branch_name && it.branch_name.toLowerCase().includes(term))
    );
  }

  /** Unidades físicas totales en existencia */
  get totalUnits(): number {
    return this.data?.total_unidades ?? (this.data?.items || []).reduce((acc, it) => acc + (it.stock_actual || 0), 0);
  }

  /** Nº de variantes con existencias */
  get variantsWithStock(): number {
    return (this.data?.items || []).filter((it) => (it.stock_actual || 0) > 0).length;
  }

  /** Sucursales con inventario */
  get branchesWithStock(): number {
    if (this.branchId) return 1;
    return new Set((this.data?.items || []).map((it) => it.branch_id)).size;
  }
}
