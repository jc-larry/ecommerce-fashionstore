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
  validationErrors: { [key: string]: string } = {};
  success = '';

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
      role_names: ['CLIENTE'] as string[],
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
        this.error = 'No se pudieron cargar los usuarios del sistema.';
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

  /** Clase de color del badge según el rol principal del usuario. */
  roleClass(u: any): string {
    const main = ((u.roles || [])[0]?.name || '').toUpperCase();
    const map: Record<string, string> = {
      SUPERADMIN: 'pill-role-superadmin',
      ENCARGADO: 'pill-role-encargado',
      CAJERO: 'pill-role-cajero',
      CLIENTE: 'pill-role-cliente',
    };
    return map[main] || 'pill-role';
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.validationErrors = {};
    this.error = '';
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
    this.validationErrors = {};
    this.error = '';
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
    this.validationErrors = {};
  }

  toggleRole(role: string): void {
    const i = this.form.role_names.indexOf(role);
    if (i >= 0) this.form.role_names.splice(i, 1);
    else this.form.role_names.push(role);
  }

  validate(): boolean {
    this.validationErrors = {};

    const fn = (this.form.first_name || '').trim();
    if (!fn) {
      this.validationErrors['first_name'] = 'Ingresa el nombre del usuario.';
    } else if (fn.length < 2) {
      this.validationErrors['first_name'] = 'El nombre debe tener al menos 2 letras.';
    }

    const ln = (this.form.last_name || '').trim();
    if (!ln) {
      this.validationErrors['last_name'] = 'Ingresa el apellido del usuario.';
    } else if (ln.length < 2) {
      this.validationErrors['last_name'] = 'El apellido debe tener al menos 2 letras.';
    }

    const em = (this.form.email || '').trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!em) {
      this.validationErrors['email'] = 'Ingresa el correo electrónico para acceder al sistema.';
    } else if (!emailRegex.test(em)) {
      this.validationErrors['email'] = 'El formato del correo no es válido (ejemplo: usuario@fashionstore.com).';
    }

    if (!this.editingId) {
      const pw = this.form.password || '';
      if (!pw) {
        this.validationErrors['password'] = 'Crea una contraseña para la nueva cuenta.';
      } else if (pw.length < 8) {
        this.validationErrors['password'] = 'La contraseña debe tener al menos 8 caracteres.';
      } else if (!/[A-Z]/.test(pw) || !/[a-z]/.test(pw) || !/[0-9]/.test(pw)) {
        this.validationErrors['password'] = 'La contraseña debe incluir al menos una letra mayúscula, una minúscula y un número.';
      }
    }

    if (!this.form.role_names || this.form.role_names.length === 0) {
      this.validationErrors['roles'] = 'Selecciona al menos un rol para este usuario (ej. Cajero, Encargado o Administrador).';
    }

    return Object.keys(this.validationErrors).length === 0;
  }

  /**
   * [CU05] Gestionar perfiles y roles (Crear / Editar)
   */
  save(): void {
    this.error = '';
    this.success = '';

    if (!this.validate()) {
      this.error = 'Por favor revisa los campos señalados en el formulario antes de guardar.';
      return;
    }

    if (this.editingId) {
      const payload: any = {
        first_name: this.form.first_name.trim(),
        last_name: this.form.last_name.trim(),
        email: this.form.email.trim(),
        phone: this.form.phone?.trim() || null,
        is_active: this.form.is_active,
        role_names: this.form.role_names,
      };
      this.usersService.updateUser(this.editingId, payload).subscribe({
        next: () => {
          this.success = 'Usuario actualizado correctamente.';
          this.loadUsers();
          this.closeForm();
          setTimeout(() => (this.success = ''), 4000);
        },
        error: (e) => (this.error = e.error?.detail || 'Error al actualizar el usuario.'),
      });
    } else {
      this.usersService.createUser({
        ...this.form,
        first_name: this.form.first_name.trim(),
        last_name: this.form.last_name.trim(),
        email: this.form.email.trim(),
        phone: this.form.phone?.trim() || null,
      }).subscribe({
        next: () => {
          this.success = 'Usuario registrado exitosamente en la plataforma.';
          this.loadUsers();
          this.closeForm();
          setTimeout(() => (this.success = ''), 4000);
        },
        error: (e) => (this.error = e.error?.detail || 'Error al crear el usuario.'),
      });
    }
  }

  /**
   * [CU05] Baja lógica de usuario:
   * Prohibido eliminar usuarios para preservar la trazabilidad de ventas, compras y auditoría (CU36).
   */
  deactivate(u: any): void {
    const isCurrentlyActive = u.is_active;
    const action = isCurrentlyActive ? 'desactivar' : 'reactivar';
    const msg = isCurrentlyActive
      ? `¿Deseas desactivar la cuenta de ${u.first_name} ${u.last_name}?\n\nℹ️ El usuario no podrá iniciar sesión en el sistema, pero todas sus operaciones registradas se mantendrán intactas para auditoría.`
      : `¿Deseas reactivar la cuenta de ${u.first_name} ${u.last_name}?`;

    if (!confirm(msg)) return;

    this.error = '';
    if (isCurrentlyActive) {
      this.usersService.deactivateUser(u.id).subscribe({
        next: () => {
          this.success = `Usuario ${u.first_name} ${u.last_name} desactivado. Trazabilidad preservada.`;
          this.loadUsers();
          setTimeout(() => (this.success = ''), 4000);
        },
        error: (e) => (this.error = e.error?.detail || 'Error al desactivar la cuenta.'),
      });
    } else {
      this.usersService.updateUser(u.id, { is_active: true }).subscribe({
        next: () => {
          this.success = `Cuenta de ${u.first_name} ${u.last_name} reactivada con éxito.`;
          this.loadUsers();
          setTimeout(() => (this.success = ''), 4000);
        },
        error: (e) => (this.error = e.error?.detail || 'Error al reactivar la cuenta.'),
      });
    }
  }
}
