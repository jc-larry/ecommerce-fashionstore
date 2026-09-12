import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { InventarioService, InventoryAdjustment } from '../inventario.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

import { BranchContextService } from '../../catalogo_y_tiendas/branches/branch-context.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

export interface AdjustmentReasonOption {
  value: string;
  label: string;
  category: 'MERMA' | 'SOBRANTE';
  description: string;
  icon: string;
}

@Component({
  selector: 'app-adjustments',
  templateUrl: './adjustments.component.html',
  styleUrls: ['./adjustments.component.css'],
})
export class AdjustmentsComponent implements OnInit {
  branches: any[] = [];
  variants: any[] = [];
  ledger: any[] = [];
  inventoryMap: Record<number, { stock: number; avg_cost: number }> = {};

  branchId: number | null = null;
  variantId: number | null = null;
  
  // Tipo principal: 'MERMA' (baja/pérdida) o 'SOBRANTE' (excedente)
  adjustmentType: 'MERMA' | 'SOBRANTE' = 'MERMA';
  selectedReason = 'MERMA_DEFECTO_FABRICA';
  unitsCount = 1;
  note = '';

  loading = false;
  loadingInventory = false;
  saving = false;
  error = '';
  success = '';

  readonly reasonOptions: AdjustmentReasonOption[] = [
    {
      value: 'MERMA_DEFECTO_FABRICA',
      label: 'Tara / Defecto Textil',
      category: 'MERMA',
      description: 'Prenda con falla de costura, mancha de tinte o tara de fábrica.',
      icon: 'bi-scissors',
    },
    {
      value: 'MERMA_DANIO_TIENDA',
      label: 'Daño en Tienda / Probador',
      category: 'MERMA',
      description: 'Deterioro ocurrido durante la exhibición comercial o en probadores.',
      icon: 'bi-exclamation-octagon',
    },
    {
      value: 'MERMA_OBSOLESCENCIA',
      label: 'Obsolescencia de Temporada',
      category: 'MERMA',
      description: 'Prenda no comercializable por cambio de estación o descontinuación.',
      icon: 'bi-calendar-x',
    },
    {
      value: 'FALTANTE_INVENTARIO',
      label: 'Faltante de Conteo Físico',
      category: 'MERMA',
      description: 'Diferencia negativa detectada en auditoría física periódica.',
      icon: 'bi-search',
    },
    {
      value: 'SOBRANTE_INVENTARIO',
      label: 'Sobrante / Excedente de Conteo',
      category: 'SOBRANTE',
      description: 'Unidad adicional detectada en auditoría física de estantería.',
      icon: 'bi-plus-circle',
    },
    {
      value: 'REGULARIZACION_STOCK',
      label: 'Regularización Técnica',
      category: 'SOBRANTE',
      description: 'Corrección manual autorizada de existencias contables.',
      icon: 'bi-arrow-left-right',
    },
  ];

  constructor(
    private inventario: InventarioService,
    private catalogo: CatalogoService,
    public branchContext: BranchContextService,
    public authService: AuthService
  ) {}

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
              sku: v.sku,
              label: `${p.name} - ${v.color?.name || 'Color'} (${v.size?.name || 'Talla'})`,
              productName: p.name,
              colorName: v.color?.name || 'Estándar',
              colorHex: v.color?.hex_code || '#999999',
              sizeName: v.size?.name || 'Única',
              imageUrl: rawUrl ? this.catalogo.resolveImageUrl(rawUrl) : null,
            });
          }
        }
        this.loading = false;

        // Sincronizar con la sucursal activa actual
        this.branchContext.activeBranch$.subscribe((active) => {
          if (active) {
            this.branchId = active.id;
          }
          this.onBranchChange();
          this.loadLedger();
        });
      },
      error: () => {
        this.error = 'No se pudieron cargar los datos.';
        this.loading = false;
      },
    });
  }

  get availableVariants(): any[] {
    if (!this.branchId) return this.variants;
    if (this.adjustmentType === 'MERMA') {
      // Para mermas, solo prendas que tengan stock registrado en esta sucursal
      const inStock = this.variants.filter(v => (this.inventoryMap[v.id]?.stock || 0) > 0);
      return inStock.length > 0 ? inStock : this.variants;
    }
    return this.variants;
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
        for (const it of items) {
          this.inventoryMap[it.variant_id] = {
            stock: it.stock_actual,
            avg_cost: Number(it.avg_cost) || 0,
          };
        }
        this.loadingInventory = false;
      },
      error: () => {
        this.loadingInventory = false;
      },
    });
  }

  get filteredReasons(): AdjustmentReasonOption[] {
    return this.reasonOptions.filter((r) => r.category === this.adjustmentType);
  }

  setAdjustmentType(type: 'MERMA' | 'SOBRANTE'): void {
    this.adjustmentType = type;
    const available = this.filteredReasons;
    if (available.length > 0) {
      this.selectedReason = available[0].value;
    }
  }

  get selectedVariant(): any {
    return this.variants.find((v) => v.id === this.variantId);
  }

  getCurrentStock(): number {
    if (!this.variantId || !this.inventoryMap[this.variantId]) return 0;
    return this.inventoryMap[this.variantId].stock;
  }

  getCurrentAvgCost(): number {
    if (!this.variantId || !this.inventoryMap[this.variantId]) return 0;
    return this.inventoryMap[this.variantId].avg_cost;
  }

  /** Cantidad matemática con signo para el backend */
  get signedQuantity(): number {
    const qty = Math.max(1, Math.abs(Number(this.unitsCount) || 1));
    return this.adjustmentType === 'MERMA' ? -qty : qty;
  }

  /** Impacto financiero total en Bs. */
  get estimatedFinancialImpact(): number {
    const qty = Math.abs(this.signedQuantity);
    const cost = this.getCurrentAvgCost();
    return qty * cost;
  }

  loadLedger(): void {
    const targetBranchId = this.branchId || undefined;
    this.inventario.getLedger(targetBranchId).subscribe({
      next: (data) => {
        this.ledger = data
          .filter((m: any) => m.movement_type === 'AJUSTE')
          .sort((a: any, b: any) => (a.created_at < b.created_at ? 1 : -1))
          .slice(0, 15);
      },
      error: () => {},
    });
  }

  getReasonLabel(reasonCode: string): string {
    const found = this.reasonOptions.find((r) => r.value === reasonCode);
    if (found) return found.label;
    if (reasonCode === 'MERMA') return 'Merma / Baja';
    if (reasonCode === 'DANO') return 'Daño en Tienda';
    if (reasonCode === 'PERDIDA') return 'Pérdida / Faltante';
    if (reasonCode === 'CONTEO') return 'Conteo Físico';
    return reasonCode;
  }

  getAbsImpact(m: any): number {
    return Math.abs((Number(m.quantity) || 0) * (Number(m.unit_cost) || 0));
  }

  // Métricas rápidas de mermas
  get totalShrinkageUnits(): number {
    return this.ledger
      .filter((m: any) => m.quantity < 0)
      .reduce((acc, m) => acc + Math.abs(m.quantity), 0);
  }

  get totalShrinkageValue(): number {
    return this.ledger
      .filter((m: any) => m.quantity < 0)
      .reduce((acc, m) => acc + Math.abs(m.quantity) * Number(m.unit_cost || 0), 0);
  }

  /**
   * [CU38] Registrar ajuste / merma con valoración en Kárdex
   */
  register(): void {
    this.error = '';
    this.success = '';

    if (!this.branchId) {
      this.error = 'Por favor selecciona la sucursal donde se encuentra la prenda.';
      return;
    }

    if (!this.variantId) {
      this.error = 'Por favor selecciona la prenda específica que deseas ajustar.';
      return;
    }

    const qty = Number(this.unitsCount);
    if (isNaN(qty) || qty <= 0) {
      this.error = 'Ingresa una cantidad válida de prendas (debe ser al menos 1 unidad).';
      return;
    }

    const currentStock = this.getCurrentStock();
    if (this.adjustmentType === 'MERMA' && qty > currentStock) {
      this.error = `No es posible dar de baja ${qty} prenda(s) porque en esta tienda solo se cuenta con ${currentStock} unidad(es) disponible(s). Por favor verifica el conteo físico.`;
      return;
    }

    const payload: InventoryAdjustment = {
      branch_id: Number(this.branchId),
      variant_id: Number(this.variantId),
      quantity: this.signedQuantity,
      reason: this.selectedReason,
      note: this.note.trim() || undefined,
    };

    this.saving = true;
    this.inventario.createAdjustment(payload).subscribe({
      next: (res) => {
        this.saving = false;
        const impactStr = `Bs. ${Number(res.financial_impact || 0).toFixed(2)}`;
        this.success = `¡Ajuste ${res.reference_id} asentado con éxito! Tipo: ${res.reason_label || res.reason}. Impacto financiero: ${impactStr}. Stock resultante: ${res.stock_resultante} unid.`;
        this.note = '';
        this.unitsCount = 1;
        this.onBranchChange();
        this.loadLedger();
      },
      error: (e) => {
        this.saving = false;
        this.error = e.error?.detail || 'No se pudo registrar el ajuste de inventario.';
      },
    });
  }
}
