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
