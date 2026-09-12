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
import { DashboardComponent } from './packages/dashboard/dashboard.component';
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
import { AuthGuard, SessionGuard, CentralOnlyGuard } from './packages/seguridad_y_usuarios/auth.guard';

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

  // Panel administrativo (protegido por AuthGuard; los módulos exclusivos de Casa Matriz
  // además exigen CentralOnlyGuard, que redirige a /admin/dashboard si no es SUPERADMIN)
  { path: 'admin/dashboard', component: DashboardComponent, canActivate: [AuthGuard], title: 'Dashboard' },
  { path: 'admin/usuarios', component: UsuariosRolesComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Usuarios y Roles' },
  { path: 'admin/branches', component: BranchesComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Sucursales' },
  { path: 'admin/products', component: ProductsComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Catálogo' },
  { path: 'admin/promotions', component: PromotionsComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Promociones y Cupones' },
  { path: 'admin/reviews', component: ReviewsModerationComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Moderación de Reseñas' },
  { path: 'admin/suppliers', component: SuppliersComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Proveedores' },
  { path: 'admin/purchases', component: MerchandiseComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Mercadería' },
  { path: 'admin/transfers', component: TransfersComponent, canActivate: [AuthGuard], title: 'Transferencias' },
  { path: 'admin/alerts', component: StockAlertsComponent, canActivate: [AuthGuard], title: 'Alertas de Stock' },
  { path: 'admin/valuation', component: ValuationComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Valoración de inventario' },
  { path: 'admin/adjustments', component: AdjustmentsComponent, canActivate: [AuthGuard], title: 'Ajustes de inventario' },
  { path: 'admin/pos', component: PosComponent, canActivate: [AuthGuard], title: 'Punto de Venta POS' },
  { path: 'admin/shifts', component: CashShiftComponent, canActivate: [AuthGuard], title: 'Arqueo de Caja' },
  { path: 'admin/quotations-returns', component: QuotationsReturnsComponent, canActivate: [AuthGuard], title: 'Cotizaciones y Devoluciones' },
  { path: 'admin/employees', component: EmployeesComponent, canActivate: [AuthGuard], title: 'Empleados' },
  { path: 'admin/audit', component: AuditComponent, canActivate: [AuthGuard, CentralOnlyGuard], title: 'Auditoría' },

  { path: '**', redirectTo: 'login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
