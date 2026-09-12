import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../seguridad_y_usuarios/auth.service';
import { UsersService } from '../seguridad_y_usuarios/users.service';
import { CatalogoService } from '../catalogo_y_tiendas/catalogo.service';
import { BranchContextService } from '../catalogo_y_tiendas/branches/branch-context.service';
import { InventarioService } from '../inventario_y_proveedores/inventario.service';
import { VentasService } from '../ventas_y_pagos/ventas.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  loading = true;
  activeBranchName = 'Casa Matriz (Consolidado)';
  isCentral = true;
  activeBranchCity = '';

  stats: { label: string; value: string | number; icon: string; subtitle?: string }[] = [];
  recentLogs: any[] = [];

  constructor(
    public auth: AuthService,
    private users: UsersService,
    private catalogo: CatalogoService,
    private inventario: InventarioService,
    private ventas: VentasService,
    public branchContext: BranchContextService,
    private router: Router
  ) {}

  exitBranch(): void {
    if (confirm(`¿Estás seguro de salir de la sucursal ${this.activeBranchName} y volver al módulo de sucursales de Casa Matriz?`)) {
      this.branchContext.setActiveBranchById(null);
      this.router.navigate(['/admin/branches']);
    }
  }

  get userName(): string {
    const u = this.auth.getCurrentUser();
    return u ? u.first_name : 'Administrador';
  }

  ngOnInit(): void {
    this.branchContext.activeBranch$.subscribe((active) => {
      if (!active) {
        this.isCentral = true;
        this.activeBranchName = 'Casa Matriz (Consolidado)';
        this.activeBranchCity = 'Nivel Corporativo';
        this.loadCentralDashboard();
      } else {
        this.isCentral = false;
        this.activeBranchName = active.name;
        this.activeBranchCity = active.city || 'Sucursal';
        this.loadBranchDashboard(active.id);
      }
    });
  }

  loadCentralDashboard(): void {
    this.loading = true;
    forkJoin({
      users: this.users.getUsers().pipe(catchError(() => of([] as any[]))),
      branches: this.catalogo.getBranches().pipe(catchError(() => of([] as any[]))),
      products: this.catalogo.getProducts().pipe(catchError(() => of([] as any[]))),
      valuation: this.inventario.getValuation().pipe(catchError(() => of(null))),
      logs: this.users.getAuditLogs().pipe(catchError(() => of([] as any[]))),
    }).subscribe(({ users, branches, products, valuation, logs }: { users: any[]; branches: any[]; products: any[]; valuation: any; logs: any[] }) => {
      const activeBranches = branches.filter((b: any) => b.is_active);
      const totalStaff = users.filter((u: any) =>
        (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO', 'ADMIN'].includes(r.name))
      );

      this.stats = [
        { label: 'Sucursales Activas', value: activeBranches.length, icon: 'bi-shop', subtitle: 'Puntos físicos' },
        { label: 'Prendas en Catálogo', value: products.length, icon: 'bi-tag', subtitle: 'Modelos registrados' },
        {
          label: 'Capital Consolidado',
          value: valuation ? `Bs. ${Number(valuation.capital_invertido).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Bs. 0.00',
          icon: 'bi-safe2',
          subtitle: `${valuation?.total_unidades || 0} prendas en cadena`
        },
        { label: 'Personal Registrado', value: totalStaff.length, icon: 'bi-people', subtitle: 'Colaboradores' },
      ];
      this.recentLogs = logs.slice(0, 6);
      this.loading = false;
    });
  }

  loadBranchDashboard(branchId: number): void {
    this.loading = true;
    // [Separación por sucursal] /merchandise/valuation es SUPERADMIN+ENCARGADO (expone
    // costo/margen); /audit/logs es SUPERADMIN-only. Evitamos llamarlos cuando el rol
    // actual no tiene permiso, para no mostrar "Bs. 0.00" o "sin actividad" falsos.
    const roles = this.auth.getRoles();
    const canSeeValuation = roles.some((r) => ['SUPERADMIN', 'ENCARGADO'].includes(r));
    const canSeeAuditLogs = this.auth.isCentralUser();

    forkJoin({
      inventory: this.inventario.getInventory(branchId).pipe(catchError(() => of([] as any[]))),
      valuation: canSeeValuation ? this.inventario.getValuation(branchId).pipe(catchError(() => of(null))) : of(null),
      shifts: this.ventas.getCashShifts(branchId).pipe(catchError(() => of([] as any[]))),
      branches: this.catalogo.getBranches().pipe(catchError(() => of([] as any[]))),
      logs: canSeeAuditLogs ? this.users.getAuditLogs().pipe(catchError(() => of([] as any[]))) : of([] as any[]),
    }).subscribe(({ inventory, valuation, shifts, branches, logs }: { inventory: any[]; valuation: any; shifts: any[]; branches: any[]; logs: any[] }) => {
      const targetBranch = branches.find((b: any) => b.id === branchId);
      const employeesCount = targetBranch?.employees?.length || 0;
      const totalUnits = (inventory || []).reduce((acc: number, item: any) => acc + (Number(item.stock_actual) || 0), 0);
      const openShift = shifts.find((s: any) => s.status === 'ABIERTO');

      this.stats = [
        {
          label: 'Stock Físico en Tienda',
          value: `${totalUnits} un.`,
          icon: 'bi-boxes',
          subtitle: `${inventory.length} variantes disponibles`
        },
        canSeeValuation
          ? {
              label: 'Capital en esta Sucursal',
              value: valuation ? `Bs. ${Number(valuation.capital_invertido).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Bs. 0.00',
              icon: 'bi-safe2',
              subtitle: 'Valuación al costo'
            }
          : {
              label: 'Prendas Vendibles',
              value: `${(inventory || []).filter((i: any) => Number(i.stock_actual) > 0).length}`,
              icon: 'bi-tag',
              subtitle: 'Variantes con stock disponible'
            },
        {
          label: 'Estado de Caja',
          value: openShift ? `Abierta (#${openShift.id})` : 'Cerrada',
          icon: openShift ? 'bi-cash-stack text-success' : 'bi-lock-fill text-muted',
          subtitle: openShift ? `Ventas: Bs. ${openShift.total_cash_sales?.toFixed(2) || '0.00'}` : 'Sin turno activo'
        },
        {
          label: 'Personal Asignado',
          value: `${employeesCount} empleados`,
          icon: 'bi-person-badge',
          subtitle: 'Equipo de tienda'
        },
      ];
      this.recentLogs = canSeeAuditLogs ? logs.slice(0, 6) : [];
      this.loading = false;
    });
  }

  getLogMeta(l: any): { title: string; subtitle: string; icon: string; badge: string; badgeClass: string } {
    const act = (l.action || '').toUpperCase();
    const tbl = (l.table_name || '').toLowerCase();

    if (act === 'LOGIN') {
      return {
        title: 'Inicio de sesión exitoso',
        subtitle: `Usuario #${l.user_id || l.row_id || '—'} accedió a la plataforma`,
        icon: 'bi-box-arrow-in-right',
        badge: 'Acceso',
        badgeClass: 'pill-role-cajero'
      };
    }
    if (act === 'LOGOUT') {
      return {
        title: 'Cierre de sesión',
        subtitle: 'Sesión finalizada correctamente',
        icon: 'bi-box-arrow-right',
        badge: 'Sesión',
        badgeClass: 'pill-role-cliente'
      };
    }
    if (tbl.includes('order_return')) {
      return {
        title: 'Devolución de prenda registrada',
        subtitle: `Solicitud de devolución #${l.row_id} procesada`,
        icon: 'bi-arrow-counterclockwise',
        badge: 'Devolución',
        badgeClass: 'pill-role-superadmin'
      };
    }
    if (tbl === 'orders') {
      return {
        title: 'Nueva venta / orden generada',
        subtitle: `Venta registrada #${l.row_id}`,
        icon: 'bi-bag-check-fill',
        badge: 'Venta',
        badgeClass: 'pill-role-encargado'
      };
    }
    if (tbl.includes('inventory') || tbl.includes('merchandise') || tbl.includes('stock')) {
      return {
        title: 'Movimiento de inventario físico',
        subtitle: `${act === 'INSERT' ? 'Ingreso' : 'Ajuste'} en ${l.table_name} #${l.row_id}`,
        icon: 'bi-boxes',
        badge: 'Inventario',
        badgeClass: 'pill-role-encargado'
      };
    }
    if (tbl.includes('coupon') || tbl.includes('promotion')) {
      return {
        title: 'Campaña o cupón promocional',
        subtitle: `Configuración comercial #${l.row_id}`,
        icon: 'bi-ticket-perforated-fill',
        badge: 'Promoción',
        badgeClass: 'badge-category'
      };
    }
    if (tbl.includes('product')) {
      return {
        title: 'Prenda o catálogo actualizado',
        subtitle: `Registro #${l.row_id} en ${l.table_name}`,
        icon: 'bi-tag-fill',
        badge: 'Catálogo',
        badgeClass: 'badge-category'
      };
    }
    return {
      title: `${act} en ${l.table_name}`,
      subtitle: `Registro #${l.row_id}`,
      icon: 'bi-activity',
      badge: act,
      badgeClass: 'pill-role-cliente'
    };
  }
}
