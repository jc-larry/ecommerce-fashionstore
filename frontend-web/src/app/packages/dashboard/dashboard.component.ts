import { Component, OnInit } from '@angular/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../seguridad_y_usuarios/auth.service';
import { UsersService } from '../seguridad_y_usuarios/users.service';
import { CatalogoService } from '../catalogo_y_tiendas/catalogo.service';
import { InventarioService } from '../inventario_y_proveedores/inventario.service';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  loading = true;

  stats = [
    { label: 'Usuarios registrados', value: 0, icon: 'bi-people' },
    { label: 'Sucursales activas', value: 0, icon: 'bi-shop' },
    { label: 'Prendas en catálogo', value: 0, icon: 'bi-tag' },
    { label: 'Proveedores', value: 0, icon: 'bi-truck' },
  ];

  recentLogs: any[] = [];

  constructor(
    private auth: AuthService,
    private users: UsersService,
    private catalogo: CatalogoService,
    private inventario: InventarioService
  ) {}

  get userName(): string {
    const u = this.auth.getCurrentUser();
    return u ? u.first_name : 'Administrador';
  }

  ngOnInit(): void {
    forkJoin({
      users: this.users.getUsers().pipe(catchError(() => of([]))),
      branches: this.catalogo.getBranches().pipe(catchError(() => of([]))),
      products: this.catalogo.getProducts().pipe(catchError(() => of([]))),
      suppliers: this.inventario.getSuppliers().pipe(catchError(() => of([]))),
      logs: this.users.getAuditLogs().pipe(catchError(() => of([]))),
    }).subscribe(({ users, branches, products, suppliers, logs }) => {
      this.stats[0].value = users.length;
      this.stats[1].value = branches.filter((b: any) => b.is_active).length;
      this.stats[2].value = products.length;
      this.stats[3].value = suppliers.length;
      this.recentLogs = logs.slice(0, 6);
      this.loading = false;
    });
  }
}
