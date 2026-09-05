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
import { AuthGuard, SessionGuard } from './packages/seguridad_y_usuarios/auth.guard';

const routes: Routes = [
  // Autenticación (CU01, CU03, CU04)
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent, title: 'Iniciar sesión' },
  { path: 'register', component: RegisterComponent, title: 'Crear cuenta' },
  { path: 'recover', component: RecoverComponent, title: 'Recuperar contraseña' },

  // Tienda del cliente (CU11 catálogo + CU14 detalle/reseñas/favoritos)
  { path: 'tienda', component: StoreHomeComponent, canActivate: [SessionGuard], title: 'FashionStore' },
  { path: 'tienda/favoritos', component: WishlistComponent, canActivate: [SessionGuard], title: 'Mis favoritos' },
  { path: 'tienda/producto/:id', component: ProductDetailComponent, canActivate: [SessionGuard], title: 'Prenda' },

  // Panel administrativo (protegido por AuthGuard)
  { path: 'admin/dashboard', component: DashboardComponent, canActivate: [AuthGuard], title: 'Dashboard' },
  { path: 'admin/usuarios', component: UsuariosRolesComponent, canActivate: [AuthGuard], title: 'Usuarios y Roles' },
  { path: 'admin/branches', component: BranchesComponent, canActivate: [AuthGuard], title: 'Sucursales' },
  { path: 'admin/products', component: ProductsComponent, canActivate: [AuthGuard], title: 'Catálogo' },
  { path: 'admin/suppliers', component: SuppliersComponent, canActivate: [AuthGuard], title: 'Proveedores' },
  { path: 'admin/purchases', component: MerchandiseComponent, canActivate: [AuthGuard], title: 'Mercadería' },
  { path: 'admin/valuation', component: ValuationComponent, canActivate: [AuthGuard], title: 'Valoración de inventario' },
  { path: 'admin/adjustments', component: AdjustmentsComponent, canActivate: [AuthGuard], title: 'Ajustes de inventario' },
  { path: 'admin/employees', component: EmployeesComponent, canActivate: [AuthGuard], title: 'Empleados' },
  { path: 'admin/audit', component: AuditComponent, canActivate: [AuthGuard], title: 'Auditoría' },

  { path: '**', redirectTo: 'login' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
