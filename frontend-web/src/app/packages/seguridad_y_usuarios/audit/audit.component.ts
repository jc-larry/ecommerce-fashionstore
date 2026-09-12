import { Component, OnInit } from '@angular/core';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-audit',
  templateUrl: './audit.component.html',
  styleUrls: ['./audit.component.css']
})
export class AuditComponent implements OnInit {
  logs: any[] = [];
  loading = false;
  error = '';
  actionFilter = 'TODOS';
  tableFilter = 'TODAS';
  searchQuery = '';
  selectedLog: any = null;

  constructor(private users: UsersService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.users.getAuditLogs().subscribe({
      next: (data) => { 
        this.logs = data; 
        this.loading = false; 
      },
      error: () => { 
        this.error = 'No se pudo cargar la bitácora de auditoría.'; 
        this.loading = false; 
      },
    });
  }

  get actions(): string[] {
    return Array.from(new Set(this.logs.map((l) => l.action))).filter(Boolean);
  }

  get tables(): string[] {
    return Array.from(new Set(this.logs.map((l) => l.table_name))).filter(Boolean);
  }

  get filtered(): any[] {
    return this.logs.filter((l) => {
      const matchAction = this.actionFilter === 'TODOS' || l.action === this.actionFilter;
      const matchTable = this.tableFilter === 'TODAS' || l.table_name === this.tableFilter;
      const q = this.searchQuery.trim().toLowerCase();
      const matchQuery = !q || 
        (l.table_name && l.table_name.toLowerCase().includes(q)) ||
        (l.action && l.action.toLowerCase().includes(q)) ||
        (l.ip_address && l.ip_address.includes(q)) ||
        (l.row_id && String(l.row_id).includes(q)) ||
        (l.user_id && String(l.user_id).includes(q));

      return matchAction && matchTable && matchQuery;
    });
  }

  getActionBadge(action: string): { label: string; badgeClass: string; icon: string } {
    const act = (action || '').toUpperCase();
    if (act === 'LOGIN') {
      return { label: 'Inicio Sesión', badgeClass: 'pill-role-cajero', icon: 'bi-box-arrow-in-right' };
    }
    if (act === 'LOGOUT') {
      return { label: 'Cierre Sesión', badgeClass: 'pill-role-cliente', icon: 'bi-box-arrow-right' };
    }
    if (act === 'INSERT') {
      return { label: 'Creación', badgeClass: 'pill-role-encargado', icon: 'bi-plus-circle' };
    }
    if (act === 'UPDATE') {
      return { label: 'Modificación', badgeClass: 'pill-role-superadmin', icon: 'bi-pencil-square' };
    }
    if (act === 'DELETE') {
      return { label: 'Eliminación', badgeClass: 'pill-off', icon: 'bi-trash' };
    }
    return { label: act, badgeClass: 'pill-role-cliente', icon: 'bi-activity' };
  }

  getTableLabel(tbl: string): string {
    const map: Record<string, string> = {
      'users': 'Usuarios y Cuentas',
      'orders': 'Ventas y Pedidos',
      'order_items': 'Detalle de Ventas',
      'order_returns': 'Devoluciones',
      'inventory': 'Stock en Tienda',
      'inventory_ledger': 'Libro Mayor Kárdex',
      'products': 'Catálogo de Ropa',
      'product_variants': 'Variantes (Talla/Color)',
      'coupons': 'Cupones de Descuento',
      'branches': 'Sucursales Físicas',
      'cash_shifts': 'Arqueo de Turno',
      'stock_transfers': 'Transferencias',
      'session_tokens': 'Tokens de Acceso'
    };
    return map[tbl] || tbl;
  }

  openDetail(l: any): void {
    this.selectedLog = l;
  }

  closeDetail(): void {
    this.selectedLog = null;
  }

  formatJson(val: any): string {
    if (!val) return '—';
    try {
      return typeof val === 'string' ? JSON.stringify(JSON.parse(val), null, 2) : JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  }

  summary(values: any): string {
    if (!values) return '—';
    try {
      const obj = typeof values === 'string' ? JSON.parse(values) : values;
      const keys = Object.keys(obj);
      if (keys.length === 0) return 'Sin cambios';
      return keys.slice(0, 3).map(k => `${k}: ${obj[k]}`).join(' · ');
    } catch {
      return String(values);
    }
  }
}
