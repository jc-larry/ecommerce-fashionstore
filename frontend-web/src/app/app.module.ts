import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
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
import { CartModalComponent } from './packages/ventas_y_pagos/cart/cart-modal.component';
import { SupplierPortalComponent } from './packages/inventario_y_proveedores/supplier-portal/supplier-portal.component';
import { AuthInterceptor } from './packages/seguridad_y_usuarios/auth.interceptor';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    RegisterComponent,
    RecoverComponent,
    BranchesComponent,
    ProductsComponent,
    SuppliersComponent,
    MerchandiseComponent,
    ValuationComponent,
    AdjustmentsComponent,
    UsuariosRolesComponent,
    DashboardComponent,
    EmployeesComponent,
    AuditComponent,
    StoreHomeComponent,
    ProductDetailComponent,
    WishlistComponent,
    PromotionsComponent,
    ReviewsModerationComponent,
    TransfersComponent,
    StockAlertsComponent,
    PosComponent,
    CashShiftComponent,
    QuotationsReturnsComponent,
    CustomerOrdersComponent,
    CartModalComponent,
    SupplierPortalComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    AppRoutingModule
  ],
  providers: [
    provideHttpClient(withInterceptorsFromDi()),
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule {}
