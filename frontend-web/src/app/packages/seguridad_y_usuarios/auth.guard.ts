import { Injectable } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Protege las rutas /admin/*: exige sesión activa y un rol con acceso al panel
 * administrativo (SUPERADMIN, ENCARGADO o CAJERO). Un cliente es enviado a la tienda.
 */
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree {
    if (!this.auth.isLoggedIn()) {
      return this.router.createUrlTree(['/login']);
    }
    if (this.auth.isAdminUser()) {
      return true;
    }
    // [Rol PROVEEDOR] no pertenece al panel admin ni a la tienda: tiene su propio portal
    if (this.auth.isProveedorUser()) {
      return this.router.createUrlTree(['/proveedor']);
    }
    // Sesión válida pero sin rol de panel → es cliente
    return this.router.createUrlTree(['/tienda']);
  }
}

/**
 * Protege la tienda del cliente (/tienda): solo exige sesión activa.
 */
@Injectable({ providedIn: 'root' })
export class SessionGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree {
    if (this.auth.isLoggedIn()) {
      return true;
    }
    return this.router.createUrlTree(['/login']);
  }
}

/**
 * [Separación por sucursal] Protege las rutas exclusivas de Casa Matriz (SUPERADMIN):
 * un ENCARGADO/CAJERO que navegue directo a la URL es redirigido a su propio dashboard.
 */
@Injectable({ providedIn: 'root' })
export class CentralOnlyGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree {
    if (this.auth.isCentralUser()) {
      return true;
    }
    return this.router.createUrlTree(['/admin/dashboard']);
  }
}

/**
 * [Rol PROVEEDOR] Protege el portal de autoservicio del proveedor (/proveedor):
 * exige sesión activa y rol PROVEEDOR. Un admin o cliente son redirigidos a su propio panel.
 */
@Injectable({ providedIn: 'root' })
export class ProveedorGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree {
    if (!this.auth.isLoggedIn()) {
      return this.router.createUrlTree(['/login']);
    }
    if (this.auth.isProveedorUser()) {
      return true;
    }
    if (this.auth.isAdminUser()) {
      return this.router.createUrlTree(['/admin/dashboard']);
    }
    return this.router.createUrlTree(['/tienda']);
  }
}
