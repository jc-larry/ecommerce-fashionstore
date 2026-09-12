import { Component, OnInit } from '@angular/core';
import { InventarioService, StockAlertItem } from '../inventario.service';
import { CatalogoService, BranchOption } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

@Component({
  selector: 'app-stock-alerts',
  templateUrl: './stock-alerts.component.html',
  styleUrls: ['./stock-alerts.component.css']
})
export class StockAlertsComponent implements OnInit {
  alerts: StockAlertItem[] = [];
  branches: BranchOption[] = [];
  branchFilter: number | null = null;
  loading = false;
  errorMessage = '';
  successMessage = '';

  // Modal para editar umbrales de stock
  selectedAlert: StockAlertItem | null = null;
  editStockMin = 5;
  editStockMax = 100;

  constructor(
    private inventarioService: InventarioService,
    private catalogoService: CatalogoService,
    public branchContext: BranchContextService,
    public authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadBranches();
    this.branchContext.activeBranch$.subscribe((active) => {
      this.branchFilter = active ? active.id : null;
      this.loadAlerts();
    });
  }

  loadBranches(): void {
    this.catalogoService.getFilterOptions().subscribe({
      next: (opts) => {
        this.branches = opts.branches;
      }
    });
  }

  onLocalBranchChange(): void {
    this.branchContext.setActiveBranchById(this.branchFilter);
    this.loadAlerts();
  }

  loadAlerts(): void {
    this.loading = true;
    this.errorMessage = '';
    this.inventarioService.getStockAlerts(this.branchFilter || undefined).subscribe({
      next: (data) => {
        this.alerts = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al cargar alertas de inventario.';
        this.loading = false;
      }
    });
  }

  modalError = '';

  openThresholdModal(alert: StockAlertItem): void {
    this.selectedAlert = alert;
    this.editStockMin = alert.stock_minimo;
    this.editStockMax = alert.stock_maximo;
    this.modalError = '';
  }

  saveThresholds(): void {
    if (!this.selectedAlert) return;
    this.modalError = '';

    if (this.editStockMin < 0) {
      this.modalError = 'El stock mínimo no puede ser un número negativo.';
      return;
    }

    if (this.editStockMax <= 0) {
      this.modalError = 'El stock máximo debe ser mayor a 0 unidades.';
      return;
    }

    if (this.editStockMin >= this.editStockMax) {
      this.modalError = 'El stock mínimo debe ser menor al stock máximo para que las alertas funcionen adecuadamente.';
      return;
    }

    this.inventarioService.updateStockThresholds(
      this.selectedAlert.branch_id,
      this.selectedAlert.variant_id,
      this.editStockMin,
      this.editStockMax
    ).subscribe({
      next: () => {
        this.successMessage = `Umbrales actualizados correctamente para ${this.selectedAlert!.product_name}.`;
        this.selectedAlert = null;
        this.loadAlerts();
        setTimeout(() => this.successMessage = '', 4000);
      },
      error: (err) => {
        this.modalError = err.error?.detail || 'No se pudieron guardar los umbrales. Inténtalo de nuevo.';
      }
    });
  }
}
