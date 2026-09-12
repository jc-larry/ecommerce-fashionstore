import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { map, tap, switchMap, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

/**
 * [CU01–CU04] Servicio único de autenticación del panel administrativo.
 * Consume el paquete `seguridad_y_usuarios` del backend FastAPI.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly authUrl = `${environment.apiUrl}/auth`;

  private currentUserSubject = new BehaviorSubject<any>(this.readStoredUser());
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {}

  private readStoredUser(): any {
    const saved = localStorage.getItem('currentUser');
    return saved ? JSON.parse(saved) : null;
  }

  // [CU01] Iniciar sesión
  login(credentials: { email: string; password: string }): Observable<any> {
    return this.http.post<any>(`${this.authUrl}/login`, credentials).pipe(
      tap((response) => {
        if (response?.access_token) {
          localStorage.setItem('token', response.access_token);
          localStorage.setItem('currentUser', JSON.stringify(response.user));
          localStorage.setItem('roles', JSON.stringify(response.roles || []));
          this.currentUserSubject.next(response.user);
        }
      }),
      // [Separación por sucursal] Enriquece la sesión con branch_id/branch_name/is_central.
      // Si /auth/me falla por cualquier motivo, el login básico ya realizado no se ve afectado.
      switchMap((response) =>
        this.http.get<any>(`${this.authUrl}/me`).pipe(
          tap((me) => {
            if (me) {
              localStorage.setItem('currentUser', JSON.stringify(me));
              this.currentUserSubject.next(me);
            }
          }),
          map(() => response),
          catchError(() => of(response))
        )
      )
    );
  }

  // [CU02] Cerrar sesión (revoca el token en el backend)
  logout(): Observable<any> {
    return this.http.post<any>(`${this.authUrl}/logout`, {}).pipe(
      map((response) => {
        this.clearSession();
        return response;
      })
    );
  }

  // [CU03] Solicitar enlace/token de recuperación
  recoverCredentials(email: string): Observable<any> {
    return this.http.post<any>(`${this.authUrl}/recover`, { email });
  }

  // [CU03] Restablecer contraseña con token (válido 5 minutos)
  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.http.post<any>(`${this.authUrl}/reset-password`, {
      token,
      new_password: newPassword,
    });
  }

  // [CU04] Auto-registro de cliente
  registerClient(clientData: any): Observable<any> {
    return this.http.post<any>(`${this.authUrl}/register`, clientData);
  }

  // [CU02] Limpieza local de sesión (inactividad o error de sesión)
  clearSession(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('roles');
    this.currentUserSubject.next(null);
  }

  /** Alias mantenido por compatibilidad con el temporizador de inactividad. */
  forceLogout(): void {
    this.clearSession();
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getRoles(): string[] {
    const roles = localStorage.getItem('roles');
    return roles ? JSON.parse(roles) : [];
  }

  getCurrentUser(): any {
    return this.currentUserSubject.value ?? this.readStoredUser();
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  /** True si el usuario tiene un rol con acceso al panel administrativo. */
  isAdminUser(): boolean {
    const roles = this.getRoles();
    return roles.some((r) => ['SUPERADMIN', 'ENCARGADO', 'CAJERO'].includes(r));
  }

  /**
   * [Separación por sucursal] True solo para SUPERADMIN (Casa Matriz / vista consolidada).
   * ENCARGADO y CAJERO quedan siempre atados a su propia sucursal.
   */
  isCentralUser(): boolean {
    return this.getRoles().includes('SUPERADMIN');
  }
}
