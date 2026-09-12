import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { UsersService } from '../../seguridad_y_usuarios/users.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';
import { CatalogoService } from '../catalogo.service';
import { BranchContextService } from '../branches/branch-context.service';

@Component({
  selector: 'app-employees',
  templateUrl: './employees.component.html',
  styleUrls: ['./employees.component.css']
})
export class EmployeesComponent implements OnInit {
  employees: any[] = [];
  allEmployees: any[] = [];
  branches: any[] = [];
  loading = false;
  error = '';
  activeBranchName = 'Casa Matriz (Todas las Sucursales)';
  isCentral = true;

  showForm = false;
  form = this.emptyForm();

  constructor(
    private users: UsersService,
    private catalogo: CatalogoService,
    public branchContext: BranchContextService,
    public authService: AuthService
  ) {}

  ngOnInit(): void {
    this.branchContext.activeBranch$.subscribe((active) => {
      this.isCentral = !active;
      this.activeBranchName = active ? active.name : 'Casa Matriz (Todas las Sucursales)';
      this.applyFilter();
    });
    this.load();
  }

  emptyForm() {
    return {
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      password: '',
      role: 'CAJERO',
      branch_id: this.branchContext.getActiveBranchId() || (null as number | null),
    };
  }

  applyFilter(): void {
    const activeId = this.branchContext.getActiveBranchId();
    if (!activeId) {
      this.employees = [...this.allEmployees];
    } else {
      this.employees = this.allEmployees.filter((e: any) => e.branch?.id === activeId);
    }
  }

  load(): void {
    this.loading = true;
    this.error = '';

    // [Separación por sucursal] GET /users es exclusivo de SUPERADMIN en el backend.
    // ENCARGADO/CAJERO ven, en modo solo lectura, únicamente el personal de su propia
    // sucursal, derivado de la lista pública de sucursales (branches[].employees).
    if (!this.authService.isCentralUser()) {
      this.catalogo.getBranches().subscribe({
        next: (branches: any[]) => {
          this.branches = branches;
          const own = branches.find((b: any) => b.id === this.branchContext.getActiveBranchId());
          this.allEmployees = ((own?.employees) || [])
            .filter((u: any) => (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO'].includes(r.name)))
            .map((u: any) => ({
              ...u,
              role: (u.roles || []).map((r: any) => r.name).find((n: string) => ['ENCARGADO', 'CAJERO'].includes(n)),
              branch: own,
            }));
          this.applyFilter();
          this.loading = false;
        },
        error: () => { this.error = 'No se pudieron cargar los empleados.'; this.loading = false; },
      });
      return;
    }

    forkJoin({
      users: this.users.getUsers(),
      branches: this.catalogo.getBranches(),
    }).subscribe({
      next: ({ users, branches }) => {
        this.branches = branches;
        this.allEmployees = users
          .filter((u: any) => (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO'].includes(r.name)))
          .map((u: any) => ({
            ...u,
            role: (u.roles || []).map((r: any) => r.name).find((n: string) => ['ENCARGADO', 'CAJERO'].includes(n)),
            branch: branches.find((b: any) => (b.employees || []).some((e: any) => e.id === u.id)),
          }));
        this.applyFilter();
        this.loading = false;
      },
      error: () => { this.error = 'No se pudieron cargar los empleados.'; this.loading = false; },
    });
  }

  openNew(): void {
    this.form = this.emptyForm();
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  /**
   * [CU09] Gestionar empleados
   * @description Crea un usuario administrativo y opcionalmente lo asigna de inmediato a una sucursal.
   */
  save(): void {
    this.error = '';
    const payload = {
      first_name: this.form.first_name,
      last_name: this.form.last_name,
      email: this.form.email,
      phone: this.form.phone,
      password: this.form.password,
      role_names: [this.form.role],
    };
    this.users.createUser(payload).subscribe({
      next: (created) => {
        if (this.form.branch_id) {
          this.catalogo.assignEmployee(Number(this.form.branch_id), created.id).subscribe({
            next: () => { this.load(); this.closeForm(); },
            error: (e) => (this.error = e.error?.detail || 'Empleado creado, pero falló la asignación de sucursal.'),
          });
        } else {
          this.load();
          this.closeForm();
        }
      },
      error: (e) => (this.error = e.error?.detail || 'Error al crear el empleado.'),
    });
  }

  /**
   * [CU09] Gestionar empleados
   * @description Da de baja a un empleado de manera lógica.
   */
  deactivate(emp: any): void {
    if (!confirm(`¿Desactivar al empleado ${emp.first_name} ${emp.last_name}?`)) return;
    this.users.deactivateUser(emp.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al desactivar.'),
    });
  }
}
