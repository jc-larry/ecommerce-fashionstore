import { Component, OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { UsersService } from '../../seguridad_y_usuarios/users.service';
import { CatalogoService } from '../catalogo.service';

@Component({
  selector: 'app-employees',
  templateUrl: './employees.component.html',
  styleUrls: ['./employees.component.css']
})
export class EmployeesComponent implements OnInit {
  employees: any[] = [];
  branches: any[] = [];
  loading = false;
  error = '';

  showForm = false;
  form = this.emptyForm();

  constructor(private users: UsersService, private catalogo: CatalogoService) {}

  ngOnInit(): void {
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
      branch_id: null as number | null,
    };
  }

  load(): void {
    this.loading = true;
    this.error = '';
    forkJoin({
      users: this.users.getUsers(),
      branches: this.catalogo.getBranches(),
    }).subscribe({
      next: ({ users, branches }) => {
        this.branches = branches;
        this.employees = users
          .filter((u: any) => (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO'].includes(r.name)))
          .map((u: any) => ({
            ...u,
            role: (u.roles || []).map((r: any) => r.name).find((n: string) => ['ENCARGADO', 'CAJERO'].includes(n)),
            branch: branches.find((b: any) => (b.employees || []).some((e: any) => e.id === u.id)),
          }));
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
