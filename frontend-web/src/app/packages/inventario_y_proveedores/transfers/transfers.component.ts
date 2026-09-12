import { Component, OnInit } from '@angular/core';
import { InventarioService, StockTransfer, StockTransferCreate } from '../inventario.service';
import { CatalogoService, BranchOption } from '../../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';

@Component({
  selector: 'app-transfers',
  templateUrl: './transfers.component.html',
  styleUrls: ['./transfers.component.css']
})
export class TransfersComponent implements OnInit {
  transfers: StockTransfer[] = [];
  branches: BranchOption[] = [];
  loading = false;
  statusFilter = '';
  branchFilter: number | null = null;
  errorMessage = '';
  successMessage = '';

  // Modal para nueva transferencia
  showCreateModal = false;
  originBranchId: number | null = null;
  destinationBranchId: number | null = null;
  transferNotes = '';
  transferItems: { variant_id: number; quantity: number }[] = [
    { variant_id: 1, quantity: 1 }
  ];

  constructor(
    private inventarioService: InventarioService,
    private catalogoService: CatalogoService,
    public branchContext: BranchContextService
  ) {}

  ngOnInit(): void {
    this.loadBranches();
    this.branchContext.activeBranch$.subscribe((active) => {
      this.branchFilter = active ? active.id : null;
      if (active) {
        this.originBranchId = active.id;
      }
      this.loadTransfers();
    });
  }

  loadBranches(): void {
    this.catalogoService.getFilterOptions().subscribe({
      next: (opts) => {
        this.branches = opts.branches;
        if (this.branches.length >= 2) {
          this.originBranchId = this.branches[0].id;
          this.destinationBranchId = this.branches[1].id;
        }
      }
    });
  }

  loadTransfers(): void {
    this.loading = true;
    this.errorMessage = '';
    this.inventarioService.getTransfers(this.branchFilter || undefined, this.statusFilter || undefined).subscribe({
      next: (data) => {
        this.transfers = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al cargar transferencias.';
        this.loading = false;
      }
    });
  }

  addItemRow(): void {
    this.transferItems.push({ variant_id: 1, quantity: 1 });
  }

  removeItemRow(index: number): void {
    if (this.transferItems.length > 1) {
      this.transferItems.splice(index, 1);
    }
  }

  createTransfer(): void {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.originBranchId) {
      this.errorMessage = 'Selecciona la sucursal de origen (desde dónde se enviarán las prendas).';
      return;
    }

    if (!this.destinationBranchId) {
      this.errorMessage = 'Selecciona la sucursal de destino (la tienda que recibirá la mercadería).';
      return;
    }

    if (Number(this.originBranchId) === Number(this.destinationBranchId)) {
      this.errorMessage = 'Las sucursales deben ser diferentes: La tienda de destino debe ser distinta a la de origen.';
      return;
    }

    if (!this.transferItems || this.transferItems.length === 0) {
      this.errorMessage = 'Agrega al menos una prenda para realizar la transferencia.';
      return;
    }

    for (let i = 0; i < this.transferItems.length; i++) {
      const it = this.transferItems[i];
      if (!it.variant_id) {
        this.errorMessage = `En la fila #${i + 1}: Selecciona la prenda que deseas transferir.`;
        return;
      }
      const q = Number(it.quantity);
      if (isNaN(q) || q <= 0) {
        this.errorMessage = `En la fila #${i + 1}: Ingresa una cantidad válida a enviar (al menos 1 unidad).`;
        return;
      }
    }

    const payload: StockTransferCreate = {
      origin_branch_id: Number(this.originBranchId),
      destination_branch_id: Number(this.destinationBranchId),
      notes: this.transferNotes.trim() || undefined,
      details: this.transferItems.map(i => ({ variant_id: Number(i.variant_id), quantity: Number(i.quantity) }))
    };

    this.inventarioService.createTransfer(payload).subscribe({
      next: (created) => {
        this.successMessage = `Transferencia ${created.transfer_number} solicitada con éxito.`;
        this.showCreateModal = false;
        this.transferNotes = '';
        this.transferItems = [{ variant_id: 1, quantity: 1 }];
        this.loadTransfers();
        setTimeout(() => this.successMessage = '', 4000);
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al crear transferencia.';
      }
    });
  }

  changeStatus(transfer: StockTransfer, newStatus: string): void {
    const actionLabel = newStatus === 'EN_TRANSITO' ? 'despachar (en tránsito)' : (newStatus === 'COMPLETADA' ? 'recibir (completar)' : 'cancelar');
    if (!confirm(`¿Confirmas ${actionLabel} la transferencia ${transfer.transfer_number}?`)) return;

    this.inventarioService.updateTransferStatus(transfer.id, newStatus).subscribe({
      next: (updated) => {
        transfer.status = updated.status;
        transfer.completed_at = updated.completed_at;
        this.successMessage = `Transferencia ${transfer.transfer_number} actualizada a ${updated.status}.`;
        this.loadTransfers();
        setTimeout(() => this.successMessage = '', 4000);
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al cambiar estado de transferencia.';
        setTimeout(() => this.errorMessage = '', 5000);
      }
    });
  }
}
