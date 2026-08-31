import { Component, OnInit } from '@angular/core';
import { UsersService } from '../users.service';

const ALL_ROLES = ['SUPERADMIN', 'ENCARGADO', 'CAJERO', 'CLIENTE'];

@Component({
  selector: 'app-usuarios-roles',
  templateUrl: './usuarios-roles.component.html',
  styleUrls: ['./usuarios-roles.component.css']
})
export class UsuariosRolesComponent implements OnInit {
  users: any[] = [];
  loading = false;
  error = '';

  search = '';
  roleFilter = 'TODOS';
  readonly roles = ALL_ROLES;

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();

  constructor(private usersService: UsersService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  emptyForm() {
    return {
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      password: '',
      role_names: [] as string[],
      is_active: true,
    };
  }

  loadUsers(): void {
    this.loading = true;
    this.usersService.getUsers().subscribe({
      next: (data) => {
        this.users = data;
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudieron cargar los usuarios.';
        this.loading = false;
      },
    });
  }

  get filteredUsers(): any[] {
    const term = this.search.trim().toLowerCase();
    return this.users.filter((u) => {
      const names = `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase();
      const matchesTerm = !term || names.includes(term);
      const roleNames = (u.roles || []).map((r: any) => r.name);
      const matchesRole = this.roleFilter === 'TODOS' || roleNames.includes(this.roleFilter);
      return matchesTerm && matchesRole;
    });
  }

  rolesLabel(u: any): string {
    return (u.roles || []).map((r: any) => r.name).join(', ') || '—';
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.showForm = true;
  }

  openEdit(u: any): void {
    this.editingId = u.id;
    this.form = {
      first_name: u.first_name,
      last_name: u.last_name,
      email: u.email,
      phone: u.phone || '',
      password: '',
      role_names: (u.roles || []).map((r: any) => r.name),
      is_active: u.is_active,
    };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  toggleRole(role: string): void {
    const i = this.form.role_names.indexOf(role);
    if (i >= 0) this.form.role_names.splice(i, 1);
    else this.form.role_names.push(role);
  }

  /**
   * [CU05] Gestionar perfiles y roles (Crear / Editar)
   * @description Registra un nuevo empleado o actualiza sus datos y roles asignados.
   */
  // [CU05 - Paso 1] / [DSC005 - Paso 1] +crearUsuario(datos, roles)
  save(): void {
    this.error = '';
    if (this.editingId) {
      const payload: any = {
        first_name: this.form.first_name,
        last_name: this.form.last_name,
        email: this.form.email,
        phone: this.form.phone,
        is_active: this.form.is_active,
        role_names: this.form.role_names,
      };
      this.usersService.updateUser(this.editingId, payload).subscribe({
        next: () => { this.loadUsers(); this.closeForm(); },
        error: (e) => (this.error = e.error?.detail || 'Error al actualizar.'),
      });
    } else {
      // [CU05 - Paso 2] / [DSC005 - Paso 2] +create_user(datos, roles)
      this.usersService.createUser({ ...this.form }).subscribe({
        next: () => { 
          // [CU05 - Paso 7] / [DSC005 - Paso 7] +Actualizar lista
          this.loadUsers(); 
          this.closeForm(); 
        },
        error: (e) => (this.error = e.error?.detail || 'Error al crear el usuario.'),
      });
    }
  }

  /**
   * [CU05] Gestionar perfiles y roles (Dar de baja)
   * @description Realiza una baja lógica del empleado, impidiendo su acceso futuro al ERP.
   */
  deactivate(u: any): void {
    if (!confirm(`¿Desactivar al usuario ${u.first_name} ${u.last_name}?`)) return;
    this.usersService.deactivateUser(u.id).subscribe({
      next: () => this.loadUsers(),
      error: (e) => (this.error = e.error?.detail || 'Error al desactivar.'),
    });
  }
}
