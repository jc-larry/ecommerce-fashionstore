import { Component, OnInit } from '@angular/core';
import { InventarioService } from '../inventario.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

/**
 * [Rol PROVEEDOR] Portal de autoservicio: ficha de contacto propia (editable),
 * disponibilidad de las prendas que ha suministrado (solo lectura, sin costos)
 * y su propio historial de compras. Todo scoped en el backend vía get_supplier_scope.
 */
@Component({
  selector: 'app-supplier-portal',
  templateUrl: './supplier-portal.component.html',
  styleUrls: ['./supplier-portal.component.css'],
})
export class SupplierPortalComponent implements OnInit {
  activeTab: 'perfil' | 'productos' | 'compras' = 'perfil';

  loading = false;
  error = '';
  success = '';

  profile: any = null;
  contactForm = { contact_name: '', email: '', phone: '', address: '' };

  products: any[] = [];
  purchaseOrders: any[] = [];

  constructor(
    private inventario: InventarioService,
    public authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.loadProfile();
  }

  setTab(tab: 'perfil' | 'productos' | 'compras'): void {
    this.activeTab = tab;
    if (tab === 'productos' && this.products.length === 0) {
      this.loadProducts();
    }
    if (tab === 'compras' && this.purchaseOrders.length === 0) {
      this.loadPurchaseOrders();
    }
  }

  loadProfile(): void {
    this.loading = true;
    this.error = '';
    this.inventario.getMySupplierProfile().subscribe({
      next: (data) => {
        this.profile = data;
        this.contactForm = {
          contact_name: data.contact_name || '',
          email: data.email || '',
          phone: data.phone || '',
          address: data.address || '',
        };
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudo cargar tu ficha de proveedor.';
        this.loading = false;
      },
    });
  }

  saveContact(): void {
    this.error = '';
    this.success = '';
    this.inventario.updateMySupplierProfile(this.contactForm).subscribe({
      next: (data) => {
        this.profile = data;
        this.success = 'Datos de contacto actualizados correctamente.';
      },
      error: (e) => (this.error = e.error?.detail || 'No se pudo actualizar tu ficha.'),
    });
  }

  loadProducts(): void {
    this.loading = true;
    this.inventario.getMySuppliedProducts().subscribe({
      next: (data) => {
        this.products = data;
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudieron cargar tus productos.';
        this.loading = false;
      },
    });
  }

  loadPurchaseOrders(): void {
    this.loading = true;
    this.inventario.getPurchaseOrders().subscribe({
      next: (data) => {
        this.purchaseOrders = data;
        this.loading = false;
      },
      error: (e) => {
        this.error = e.error?.detail || 'No se pudo cargar tu historial de compras.';
        this.loading = false;
      },
    });
  }

  onLogout(): void {
    this.authService.logout().subscribe({
      next: () => (window.location.href = '/login'),
      error: () => {
        this.authService.clearSession();
        window.location.href = '/login';
      },
    });
  }
}
