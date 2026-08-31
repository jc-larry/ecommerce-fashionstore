import { Component, OnInit } from '@angular/core';
import { InventarioService } from '../inventario.service';

@Component({
  selector: 'app-suppliers',
  templateUrl: './suppliers.component.html',
  styleUrls: ['./suppliers.component.css']
})
export class SuppliersComponent implements OnInit {
  suppliers: any[] = [];
  loading = false;
  error = '';
  search = '';

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();

  constructor(private inventario: InventarioService) {}

  ngOnInit(): void {
    this.load();
  }

  emptyForm() {
    return { nit: '', name: '', email: '', phone: '', address: '' };
  }

  load(): void {
    this.loading = true;
    this.inventario.getSuppliers().subscribe({
      next: (data) => { this.suppliers = data; this.loading = false; },
      error: () => { this.error = 'No se pudieron cargar los proveedores.'; this.loading = false; },
    });
  }

  get filtered(): any[] {
    const t = this.search.trim().toLowerCase();
    if (!t) return this.suppliers;
    return this.suppliers.filter((s) => `${s.name} ${s.nit} ${s.email}`.toLowerCase().includes(t));
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.showForm = true;
  }

  openEdit(s: any): void {
    this.editingId = s.id;
    this.form = { nit: s.nit, name: s.name, email: s.email || '', phone: s.phone || '', address: s.address || '' };
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
  }

  /**
   * [CU08] Gestionar proveedores
   * @description Crea un nuevo registro de un proveedor corporativo o actualiza los datos de contacto de uno existente.
   */
  // [CU08 - Paso 1] / [DSC008 - Paso 1] +registrar(datos)
  save(): void {
    this.error = '';
    const req = this.editingId
      ? this.inventario.updateSupplier(this.editingId, this.form)
      : this.inventario.createSupplier(this.form); // [CU08 - Paso 2] / [DSC008 - Paso 2] +create_supplier(datos)
    req.subscribe({
      next: () => { 
        // [CU08 - Paso 7] / [DSC008 - Paso 7] +Actualizar lista
        this.load(); 
        this.closeForm(); 
      },
      error: (e) => (this.error = e.error?.detail || 'Error al guardar el proveedor.'),
    });
  }

  /**
   * [CU08] Gestionar proveedores
   * @description Elimina lógicamente a un proveedor del directorio (si no tiene dependencias).
   */
  remove(s: any): void {
    if (!confirm(`¿Eliminar al proveedor ${s.name}?`)) return;
    this.inventario.deleteSupplier(s.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al eliminar.'),
    });
  }
}
