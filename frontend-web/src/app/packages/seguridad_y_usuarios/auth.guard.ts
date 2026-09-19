import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivate, Router, UrlTree } from '@angular/router';
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
    // [Rol REPARTIDOR] portal propio de repartidor
    if (this.auth.isRepartidorUser()) {
      return this.router.createUrlTree(['/repartidor']);
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
    if (this.auth.isRepartidorUser()) {
      return this.router.createUrlTree(['/repartidor']);
    }
    if (this.auth.isAdminUser()) {
      return this.router.createUrlTree(['/admin/dashboard']);
    }
    return this.router.createUrlTree(['/tienda']);
  }
}

/**
 * [Rol REPARTIDOR] Protege el portal de rutas y despachos (/repartidor):
 * exige sesión activa y rol REPARTIDOR o personal administrativo.
 */
@Injectable({ providedIn: 'root' })
export class RepartidorGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(): boolean | UrlTree {
    if (!this.auth.isLoggedIn()) {
      return this.router.createUrlTree(['/login']);
    }
    if (this.auth.isRepartidorUser() || this.auth.isAdminUser()) {
      return true;
    }
    if (this.auth.isProveedorUser()) {
      return this.router.createUrlTree(['/proveedor']);
    }
    return this.router.createUrlTree(['/tienda']);
  }
}

/**
 * Control de acceso por rol a nivel de ruta: los roles permitidos se declaran en
 * `data.roles`. Si el usuario no tiene ninguno, vuelve a su dashboard (SUPERADMIN siempre pasa).
 */
@Injectable({ providedIn: 'root' })
export class RoleGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean | UrlTree {
    if (!this.auth.isLoggedIn()) {
      return this.router.createUrlTree(['/login']);
    }
    const allowed: string[] = route.data?.['roles'] ?? [];
    if (this.auth.isCentralUser() || allowed.length === 0 || allowed.some((r) => this.auth.hasRole(r))) {
      return true;
    }
    return this.router.createUrlTree(['/admin/dashboard']);
  }
}
