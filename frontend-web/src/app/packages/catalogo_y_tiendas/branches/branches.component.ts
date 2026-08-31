import { Component, OnInit } from '@angular/core';
import { CatalogoService } from '../catalogo.service';
import { UsersService } from '../../seguridad_y_usuarios/users.service';

@Component({
  selector: 'app-branches',
  templateUrl: './branches.component.html',
  styleUrls: ['./branches.component.css']
})
export class BranchesComponent implements OnInit {
  branches: any[] = [];
  staff: any[] = []; // usuarios ENCARGADO / CAJERO
  loading = false;
  error = '';

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();

  // Asignación de empleados
  assignBranch: any = null;
  assignUserId: number | null = null;

  constructor(private catalogo: CatalogoService, private users: UsersService) {}

  ngOnInit(): void {
    this.load();
    this.loadStaff();
  }

  emptyForm() {
    return { name: '', address: '', phone: '', latitude: null as number | null, longitude: null as number | null, is_active: true };
  }

  load(): void {
    this.loading = true;
    this.catalogo.getBranches().subscribe({
      next: (data) => { this.branches = data; this.loading = false; },
      error: () => { this.error = 'No se pudieron cargar las sucursales.'; this.loading = false; },
    });
  }

  loadStaff(): void {
    this.users.getUsers().subscribe({
      next: (data) => {
        this.staff = data.filter((u: any) =>
          (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO'].includes(r.name)));
      },
      error: () => {},
    });
  }

  managerOf(branch: any): string {
    const enc = (branch.employees || []).find((e: any) => (e.roles || []).some((r: any) => r.name === 'ENCARGADO'));
    const any = (branch.employees || [])[0];
    const u = enc || any;
    return u ? `${u.first_name} ${u.last_name}` : 'Sin asignar';
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.showForm = true;
  }

  openEdit(b: any): void {
    this.editingId = b.id;
    this.form = {
      name: b.name, address: b.address, phone: b.phone || '',
      latitude: b.latitude ?? null, longitude: b.longitude ?? null, is_active: b.is_active,
    };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  /**
   * [CU06] Gestionar sucursales
   * @description Registra una nueva sucursal física de la cadena o actualiza los datos de una existente.
   */
  // [CU06 - Paso 1] / [DSC006 - Paso 1] +registrar(datos)
  save(): void {
    this.error = '';
    const req = this.editingId
      ? this.catalogo.updateBranch(this.editingId, this.form)
      : this.catalogo.createBranch(this.form); // [CU06 - Paso 2] / [DSC006 - Paso 2] +create_branch(datos)
    req.subscribe({
      next: () => { 
        // [CU06 - Paso 7] / [DSC006 - Paso 7] +Actualizar lista
        this.load(); 
        this.closeForm(); 
      },
      error: (e) => (this.error = e.error?.detail || 'Error al guardar la sucursal.'),
    });
  }

  /**
   * [CU06] Gestionar sucursales
   * @description Desactiva una sucursal para que deje de estar operativa en el sistema.
   */
  deactivate(b: any): void {
    if (!confirm(`¿Desactivar la sucursal ${b.name}?`)) return;
    this.catalogo.deactivateBranch(b.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al desactivar.'),
    });
  }

  openAssign(b: any): void {
    this.assignBranch = b;
    this.assignUserId = null;
  }

  closeAssign(): void {
    this.assignBranch = null;
  }

  /**
   * [CU09] Gestionar empleados
   * @description Vincula a un usuario con perfil de Encargado o Cajero a una Sucursal específica.
   */
  // [CU09 - Paso 1] / [DSC009 - Paso 1] +asignarSucursal(empleado, sucursal)
  confirmAssign(): void {
    if (!this.assignBranch || !this.assignUserId) return;
    // [CU09 - Paso 2] / [DSC009 - Paso 2] +assign_employee(sucursal_id, usuario_id)
    this.catalogo.assignEmployee(this.assignBranch.id, Number(this.assignUserId)).subscribe({
      next: () => { 
        // [CU09 - Paso 7] / [DSC009 - Paso 7] +Actualizar UI
        this.load(); 
        this.closeAssign(); 
      },
      error: (e) => (this.error = e.error?.detail || 'Error al asignar el empleado.'),
    });
  }

  removeEmployee(branch: any, user: any): void {
    if (!confirm(`¿Quitar a ${user.first_name} ${user.last_name} de ${branch.name}?`)) return;
    this.catalogo.removeEmployee(branch.id, user.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al quitar el empleado.'),
    });
  }
}
