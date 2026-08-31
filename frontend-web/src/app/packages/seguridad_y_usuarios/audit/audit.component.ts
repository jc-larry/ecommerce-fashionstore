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

  constructor(private users: UsersService) {}

  ngOnInit(): void {
    this.load();
  }

  /**
   * [CU36] Consultar bitácora de auditoría
   * @description Recupera el registro inmutable de acciones de seguridad y base de datos para supervisión de administradores.
   */
  // [CU36 - Paso 1] / [DSC036 - Paso 1] +verLogs()
  load(): void {
    this.loading = true;
    // [CU36 - Paso 2] / [DSC036 - Paso 2] +get_audit_logs()
    this.users.getAuditLogs().subscribe({
      next: (data) => { 
        this.logs = data; 
        this.loading = false; 
        // [CU36 - Paso 5] / [DSC036 - Paso 5] +Mostrar tabla cronológica (Renderizado de tabla en HTML)
      },
      error: () => { this.error = 'No se pudo cargar la bitácora.'; this.loading = false; },
    });
  }

  get actions(): string[] {
    return Array.from(new Set(this.logs.map((l) => l.action)));
  }

  get filtered(): any[] {
    return this.actionFilter === 'TODOS'
      ? this.logs
      : this.logs.filter((l) => l.action === this.actionFilter);
  }

  summary(values: any): string {
    if (!values) return '—';
    try {
      return typeof values === 'string' ? values : JSON.stringify(values);
    } catch {
      return '—';
    }
  }
}
