import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { VentasService, CashShiftResponse } from '../ventas.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';

@Component({
  selector: 'app-cash-shift',
  templateUrl: './cash-shift.component.html',
  styleUrls: ['./cash-shift.component.css']
})
export class CashShiftComponent implements OnInit, OnDestroy {
  currentShift: CashShiftResponse | null = null;
  shiftsHistory: CashShiftResponse[] = [];
  branches: any[] = [];
  selectedBranchId: number | null = null;
  activeBranchName: string = 'Casa Matriz (Consolidado)';
  isCentral: boolean = false;

  private branchSub!: Subscription;

  // Formulario de apertura
  openingAmount: number = 100;
  
  // Formulario de cierre ciego
  closingDeclared: number = 0;
  closingNotes: string = '';

  // Último arqueo cerrado con balance
  lastClosedShift: CashShiftResponse | null = null;

  loading: boolean = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;

  constructor(
    private ventasService: VentasService,
    private catalogoService: CatalogoService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.branchSub = this.branchContext.activeBranch$.subscribe((activeBranch) => {
      if (!activeBranch) {
        this.isCentral = true;
        this.selectedBranchId = null;
        this.activeBranchName = 'Casa Matriz (Consolidado)';
        this.currentShift = null;
        this.loadShiftsHistory(); // Todos los turnos de la cadena
      } else {
        this.isCentral = false;
        this.selectedBranchId = activeBranch.id;
        this.activeBranchName = activeBranch.name;
        this.loadCurrentShift(activeBranch.id);
        this.loadShiftsHistory(activeBranch.id);
      }
    });

    this.catalogoService.getBranches().subscribe({
      next: (data: any[]) => {
        this.branches = data;
      }
    });
  }

  ngOnDestroy(): void {
    if (this.branchSub) {
      this.branchSub.unsubscribe();
    }
  }

  selectBranch(branch: any): void {
    this.branchContext.setActiveBranch({
      id: branch.id,
      name: branch.name,
      code: branch.code,
      city: branch.city
    });
  }

  otherBranchShift: CashShiftResponse | null = null;

  loadCurrentShift(branchId?: number): void {
    this.loading = true;
    this.otherBranchShift = null;
    this.ventasService.getCurrentShift(branchId).subscribe({
      next: (shift) => {
        this.currentShift = shift;
        if (shift) {
          this.selectedBranchId = shift.branch_id;
          this.loading = false;
        } else if (branchId) {
          // Consultar si el cajero tiene un turno abierto en otra sucursal
          this.ventasService.getCurrentShift().subscribe({
            next: (globalShift) => {
              if (globalShift && globalShift.branch_id !== branchId) {
                this.otherBranchShift = globalShift;
              }
              this.loading = false;
            },
            error: () => {
              this.loading = false;
            }
          });
        } else {
          this.loading = false;
        }
      },
      error: () => {
        this.currentShift = null;
        this.loading = false;
      }
    });
  }

  switchToOtherBranch(): void {
    if (!this.otherBranchShift) return;
    const target = this.branches.find(b => b.id === this.otherBranchShift?.branch_id);
    if (target) {
      this.selectBranch(target);
    } else {
      this.branchContext.setActiveBranch({
        id: this.otherBranchShift.branch_id,
        name: this.otherBranchShift.branch_name,
        code: null,
        city: 'Santa Cruz'
      });
    }
  }

  loadShiftsHistory(branchId?: number): void {
    const targetBranch = branchId !== undefined ? branchId : (this.selectedBranchId || undefined);
    this.ventasService.getCashShifts(targetBranch).subscribe({
      next: (shifts) => {
        if (targetBranch) {
          this.shiftsHistory = (shifts || []).filter((s) => s.branch_id === targetBranch);
        } else {
          this.shiftsHistory = shifts || [];
        }
      },
      error: () => {
        this.shiftsHistory = [];
      }
    });
  }

  onOpenShift(): void {
    if (!this.selectedBranchId) {
      this.errorMessage = 'Debes seleccionar una sucursal para la apertura.';
      return;
    }
    this.errorMessage = null;
    this.successMessage = null;
    this.loading = true;

    this.ventasService.openShift(this.selectedBranchId, this.openingAmount).subscribe({
      next: (shift) => {
        this.currentShift = shift;
        this.successMessage = `Turno #${shift.id} abierto exitosamente con fondo inicial de Bs. ${shift.opening_amount.toFixed(2)} en ${shift.branch_name}.`;
        this.loading = false;
        this.loadShiftsHistory(this.selectedBranchId || undefined);
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al abrir turno de caja.';
        this.loading = false;
      }
    });
  }

  onCloseShift(): void {
    if (!this.currentShift) return;
    this.errorMessage = null;
    this.successMessage = null;
    this.loading = true;

    this.ventasService.closeShift(this.currentShift.id, this.closingDeclared, this.closingNotes).subscribe({
      next: (shift) => {
        this.lastClosedShift = shift;
        this.currentShift = null;
        this.successMessage = `Turno #${shift.id} cerrado correctamente en ${shift.branch_name}. Arqueo completado con diferencia de Bs. ${(shift.difference || 0).toFixed(2)}.`;
        this.loading = false;
        this.loadShiftsHistory(this.selectedBranchId || undefined);
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al cerrar el turno de caja.';
        this.loading = false;
      }
    });
  }
}
