import { Component, OnInit } from '@angular/core';
import { InventarioService } from '../inventario.service';

export const SUPPLIER_CATEGORIES = [
  'Telas y Textiles',
  'Avíos y Mercería (Cierres, Botones)',
  'Confección y Maquila',
  'Calzados y Cuero',
  'Empaque y Etiquetas',
  'Insumos Generales'
];

@Component({
  selector: 'app-suppliers',
  templateUrl: './suppliers.component.html',
  styleUrls: ['./suppliers.component.css']
})
export class SuppliersComponent implements OnInit {
  suppliers: any[] = [];
  loading = false;
  error = '';
  success = '';
  search = '';
  categoryFilter = '';

  readonly categories = SUPPLIER_CATEGORIES;

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();
  validationErrors: { [key: string]: string } = {};

  constructor(private inventario: InventarioService) {}

  ngOnInit(): void {
    this.load();
  }

  emptyForm() {
    return {
      nit: '',
      name: '',
      category: 'Telas y Textiles',
      contact_name: '',
      email: '',
      phone: '',
      address: '',
      is_active: true
    };
  }

  load(): void {
    this.loading = true;
    this.inventario.getSuppliers().subscribe({
      next: (data) => {
        this.suppliers = data;
        this.loading = false;
      },
      error: () => {
        this.error = 'No se pudieron cargar los proveedores del sistema.';
        this.loading = false;
      },
    });
  }

  get filtered(): any[] {
    const t = this.search.trim().toLowerCase();
    return this.suppliers.filter((s) => {
      const matchesSearch = !t || `${s.name} ${s.nit} ${s.email} ${s.contact_name || ''} ${s.category || ''}`.toLowerCase().includes(t);
      const matchesCat = !this.categoryFilter || (s.category || 'Telas y Textiles') === this.categoryFilter;
      return matchesSearch && matchesCat;
    });
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.validationErrors = {};
    this.error = '';
    this.showForm = true;
  }

  openEdit(s: any): void {
    this.editingId = s.id;
    this.form = {
      nit: s.nit,
      name: s.name,
      category: s.category || 'Telas y Textiles',
      contact_name: s.contact_name || '',
      email: s.email || '',
      phone: s.phone || '',
      address: s.address || '',
      is_active: s.is_active !== undefined ? s.is_active : true
    };
    this.validationErrors = {};
    this.error = '';
    this.showForm = true;
  }

  closeForm(): void {
    this.showForm = false;
    this.validationErrors = {};
  }

  /**
   * Valida exhaustivamente cada campo antes de emitir un movimiento o guardado,
   * informando al usuario la causa y motivo exacto de cualquier inconsistencia.
   */
  validate(): boolean {
    this.validationErrors = {};

    // 1. NIT / RUC
    const nitClean = (this.form.nit || '').trim();
    if (!nitClean) {
      this.validationErrors['nit'] = 'El NIT o documento fiscal es obligatorio para compras y facturas.';
    } else if (nitClean.length < 5) {
      this.validationErrors['nit'] = 'El NIT debe tener al menos 5 caracteres numéricos.';
    } else if (nitClean.length > 20) {
      this.validationErrors['nit'] = 'El NIT no puede tener más de 20 caracteres.';
    }

    // 2. Nombre / Razón Social
    const nameClean = (this.form.name || '').trim();
    if (!nameClean) {
      this.validationErrors['name'] = 'Ingresa el nombre o la razón social de la empresa proveedora.';
    } else if (nameClean.length < 3) {
      this.validationErrors['name'] = 'El nombre debe tener al menos 3 letras.';
    }

    // 3. Categoría de suministro
    if (!this.form.category) {
      this.validationErrors['category'] = 'Selecciona la categoría a la que pertenece este proveedor.';
    }

    // 4. Correo electrónico
    const emailClean = (this.form.email || '').trim();
    if (emailClean) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(emailClean)) {
        this.validationErrors['email'] = 'El correo electrónico no tiene un formato válido (ej: ventas@empresa.com).';
      }
    }

    // 5. Teléfono
    const phoneClean = (this.form.phone || '').trim();
    if (phoneClean) {
      const digitsOnly = phoneClean.replace(/\D/g, '');
      if (digitsOnly.length < 7) {
        this.validationErrors['phone'] = 'El teléfono de contacto debe tener al menos 7 dígitos para garantizar comunicación.';
      }
    }

    return Object.keys(this.validationErrors).length === 0;
  }

  /**
   * [CU08] Guarda un proveedor nuevo o actualizado tras validar datos fiscales
   */
  save(): void {
    this.error = '';
    this.success = '';

    if (!this.validate()) {
      this.error = 'Por favor corrige los campos señalados antes de continuar.';
      return;
    }

    const payload = {
      ...this.form,
      nit: this.form.nit.trim(),
      name: this.form.name.trim(),
      email: this.form.email?.trim() || null,
      phone: this.form.phone?.trim() || null,
      address: this.form.address?.trim() || null,
      contact_name: this.form.contact_name?.trim() || null
    };

    const req = this.editingId
      ? this.inventario.updateSupplier(this.editingId, payload)
      : this.inventario.createSupplier(payload);

    req.subscribe({
      next: () => {
        this.success = this.editingId
          ? 'Proveedor actualizado correctamente en el directorio.'
          : 'Proveedor registrado exitosamente con categoría asignada.';
        this.load();
        this.closeForm();
        setTimeout(() => (this.success = ''), 4000);
      },
      error: (e) => {
        this.error = e.error?.detail || 'Error al procesar el proveedor en la base de datos.';
      },
    });
  }

  /**
   * [CU08] Desactivación lógica (Soft-deactivation):
   * Prohibido eliminar proveedores para no romper la trazabilidad histórica del kárdex ni generar
   * registros huérfanos en compras e ingresos de mercadería pasados.
   */
  toggleStatus(s: any): void {
    const isCurrentlyActive = s.is_active !== false;
    const actionWord = isCurrentlyActive ? 'desactivar' : 'reactivar';
    const reasonMsg = isCurrentlyActive
      ? `¿Deseas desactivar al proveedor "${s.name}"?\n\nℹ️ El proveedor no podrá ser seleccionado en nuevas compras, pero se preservará todo su kárdex y comprobantes históricos para auditoría.`
      : `¿Deseas reactivar al proveedor "${s.name}" para compras de mercadería?`;

    if (!confirm(reasonMsg)) return;

    this.error = '';
    this.inventario.toggleSupplier(s.id).subscribe({
      next: (updated) => {
        s.is_active = updated.is_active;
        this.success = `Proveedor "${s.name}" ${s.is_active ? 'activado' : 'desactivado'} con éxito. Historial y trazabilidad preservados.`;
        setTimeout(() => (this.success = ''), 4000);
      },
      error: (e) => {
        this.error = e.error?.detail || `Error al ${actionWord} el proveedor.`;
      }
    });
  }
}
