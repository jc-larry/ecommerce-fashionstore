import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './packages/seguridad_y_usuarios/login/login.component';
import { RegisterComponent } from './packages/seguridad_y_usuarios/register/register.component';
import { RecoverComponent } from './packages/seguridad_y_usuarios/recover/recover.component';
import { BranchesComponent } from './packages/catalogo_y_tiendas/branches/branches.component';
import { ProductsComponent } from './packages/catalogo_y_tiendas/products/products.component';
import { SuppliersComponent } from './packages/inventario_y_proveedores/suppliers/suppliers.component';
import { MerchandiseComponent } from './packages/inventario_y_proveedores/merchandise/merchandise.component';
import { ValuationComponent } from './packages/inventario_y_proveedores/valuation/valuation.component';
import { AdjustmentsComponent } from './packages/inventario_y_proveedores/adjustments/adjustments.component';
import { UsuariosRolesComponent } from './packages/seguridad_y_usuarios/usuarios_roles/usuarios-roles.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { EmployeesComponent } from './packages/catalogo_y_tiendas/employees/employees.component';
import { AuditComponent } from './packages/seguridad_y_usuarios/audit/audit.component';
import { StoreHomeComponent } from './packages/catalogo_y_tiendas/store/store-home.component';
import { ProductDetailComponent } from './packages/catalogo_y_tiendas/store/product-detail.component';
import { WishlistComponent } from './packages/catalogo_y_tiendas/store/wishlist.component';
import { PromotionsComponent } from './packages/catalogo_y_tiendas/promotions/promotions.component';
import { ReviewsModerationComponent } from './packages/catalogo_y_tiendas/reviews-moderation/reviews-moderation.component';
import { TransfersComponent } from './packages/inventario_y_proveedores/transfers/transfers.component';
import { StockAlertsComponent } from './packages/inventario_y_proveedores/stock-alerts/stock-alerts.component';
import { PosComponent } from './packages/ventas_y_pagos/pos/pos.component';
import { CashShiftComponent } from './packages/ventas_y_pagos/cash-shift/cash-shift.component';
import { QuotationsReturnsComponent } from './packages/ventas_y_pagos/quotations-returns/quotations-returns.component';
import { CustomerOrdersComponent } from './packages/ventas_y_pagos/orders/customer-orders.component';
import { SupplierPortalComponent } from './packages/inventario_y_proveedores/supplier-portal/supplier-portal.component';
import { SupplierRequestsComponent } from './packages/inventario_y_proveedores/supplier-requests/supplier-requests.component';
import { AuthGuard, SessionGuard, CentralOnlyGuard, ProveedorGuard, RepartidorGuard, RoleGuard } from './packages/seguridad_y_usuarios/auth.guard';

// Ciclo 3 Components
import { ReservationsBoardComponent } from './packages/reservas_y_citas/reservations-board/reservations-board.component';
import { CustomerReservationsComponent } from './packages/reservas_y_citas/customer-reservations/customer-reservations.component';
import { ShipmentsComponent } from './packages/envios_y_logistica/shipments/shipments.component';
import { DeliveryZonesComponent } from './packages/envios_y_logistica/delivery-zones/delivery-zones.component';
import { TrackingViewComponent } from './packages/envios_y_logistica/tracking-view/tracking-view.component';
import { DeliveryPortalComponent } from './packages/envios_y_logistica/delivery-portal/delivery-portal.component';
import { VirtualTryonComponent } from './packages/inteligente_y_analitica/virtual-tryon/virtual-tryon.component';
import { ManagerReportsComponent } from './packages/inteligente_y_analitica/manager-reports/manager-reports.component';
import { AnalyticsDashboardComponent } from './packages/inteligente_y_analitica/analytics-dashboard/analytics-dashboard.component';

// Roles permitidos por ruta (RoleGuard). SUPERADMIN siempre tiene acceso.
const BRANCH_STAFF = { roles: ['SUPERADMIN', 'ENCARGADO', 'CAJERO'] };
const BRANCH_MANAGER = { roles: ['SUPERADMIN', 'ENCARGADO'] };
const CENTRAL_ONLY = { roles: ['SUPERADMIN'] };

const routes: Routes = [
  // Autenticación (CU01, CU03, CU04)
  { path: '', redirectTo: 'tienda', pathMatch: 'full' },
  { path: 'login', component: LoginComponent, title: 'Iniciar sesión' },
  { path: 'register', component: RegisterComponent, title: 'Crear cuenta' },
  { path: 'recover', component: RecoverComponent, title: 'Recuperar contraseña' },

  // Tienda del cliente (CU11 catálogo + CU14 detalle/reseñas/favoritos + CU24 historial pedidos)
  // El catálogo y el detalle de prenda son de libre acceso público (sin requerir login inicial)
  { path: 'tienda', component: StoreHomeComponent, title: 'FashionStore' },
  { path: 'tienda/favoritos', component: WishlistComponent, canActivate: [SessionGuard], title: 'Mis favoritos' },
  { path: 'tienda/pedidos', component: CustomerOrdersComponent, canActivate: [SessionGuard], title: 'Mis Pedidos' },
  { path: 'tienda/producto/:id', component: ProductDetailComponent, title: 'Prenda' },

  // Ciclo 3 Cliente: Reservas (CU26), Tracking (CU30), Vestidor Virtual RA (CU32)
  { path: 'tienda/reservas', component: CustomerReservationsComponent, canActivate: [SessionGuard], title: 'Mis Reservas de Probador' },
  { path: 'tienda/rastreo', component: TrackingViewComponent, title: 'Rastreo Satelital de Envíos' },
  { path: 'tienda/vestidor', component: VirtualTryonComponent, title: 'Vestidor Virtual (RA)' },

  // Panel administrativo (protegido por AuthGuard; los módulos exclusivos de Casa Matriz
  // además exigen CentralOnlyGuard, que redirige a /admin/dashboard si no es SUPERADMIN)
  { path: 'admin/dashboard', component: DashboardComponent, canActivate: [AuthGuard], title: 'Dashboard' },
  { path: 'admin/analytics-dashboard', component: AnalyticsDashboardComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Dashboard Analítico BI' },
  { path: 'admin/reservations', component: ReservationsBoardComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Bandeja Kanban de Reservas' },
  { path: 'admin/shipments', component: ShipmentsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Gestión de Despachos' },
  { path: 'admin/delivery-zones', component: DeliveryZonesComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Zonas y Tarifas de Entrega' },
  { path: 'admin/reports', component: ManagerReportsComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Reportes Gerenciales y Voz' },
  { path: 'admin/usuarios', component: UsuariosRolesComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Usuarios y Roles' },
  { path: 'admin/branches', component: BranchesComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Sucursales' },
  { path: 'admin/products', component: ProductsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_STAFF, title: 'Catálogo' },
  { path: 'admin/promotions', component: PromotionsComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Promociones y Cupones' },
  { path: 'admin/reviews', component: ReviewsModerationComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Moderación de Reseñas' },
  { path: 'admin/suppliers', component: SuppliersComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Proveedores' },
  { path: 'admin/supplier-requests', component: SupplierRequestsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Pedidos a Proveedores' },
  { path: 'admin/purchases', component: MerchandiseComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Mercadería' },
  { path: 'admin/transfers', component: TransfersComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Transferencias' },
  { path: 'admin/alerts', component: StockAlertsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Alertas de Stock' },
  { path: 'admin/valuation', component: ValuationComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Valoración de inventario' },
  { path: 'admin/adjustments', component: AdjustmentsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Ajustes de inventario' },
  { path: 'admin/pos', component: PosComponent, canActivate: [AuthGuard], title: 'Punto de Venta POS' },
  { path: 'admin/shifts', component: CashShiftComponent, canActivate: [AuthGuard], title: 'Arqueo de Caja' },
  { path: 'admin/quotations-returns', component: QuotationsReturnsComponent, canActivate: [AuthGuard, RoleGuard], data: BRANCH_MANAGER, title: 'Cotizaciones y Devoluciones' },
  { path: 'admin/employees', component: EmployeesComponent, canActivate: [AuthGuard, RoleGuard], data: CENTRAL_ONLY, title: 'Empleados' },
  { path: 'admin/audit', component: AuditComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Auditoría' },

  // [Rol PROVEEDOR] Portal de autoservicio, fuera del panel admin y de la tienda
  { path: 'proveedor', component: SupplierPortalComponent, canActivate: [ProveedorGuard], title: 'Portal de Proveedor' },

  // [Actor REPARTIDOR / DELIVERY] Portal de rutas y despachos para el conductor
  { path: 'repartidor', component: DeliveryPortalComponent, canActivate: [RepartidorGuard], title: 'Portal de Repartidor' },

  { path: '**', redirectTo: 'login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
