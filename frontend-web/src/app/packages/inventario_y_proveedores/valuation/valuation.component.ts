import { Component, OnInit } from '@angular/core';
import { InventarioService, InventoryValuation } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

/**
 * [CU37] Consultar valoración de inventario / capital invertido.
 * El capital invertido se calcula con el COSTO PROMEDIO PONDERADO (Σ stock · avg_cost),
 * nunca con el último costo unitario.
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
  loading = false;
  error = '';

  constructor(private inventario: InventarioService, private catalogo: CatalogoService) {}

  ngOnInit(): void {
    this.catalogo.getBranches().subscribe({
      next: (b) => (this.branches = b),
      error: () => {},
    });
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
}
