import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/**
 * [CU05 / CU36] Gestión de usuarios, roles y bitácora de auditoría.
 */
@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly api = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // --- Usuarios y roles (CU05) ---
  getUsers(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/users`);
  }

  createUser(user: any): Observable<any> {
    return this.http.post<any>(`${this.api}/users`, user);
  }

  updateUser(id: number, user: any): Observable<any> {
    return this.http.put<any>(`${this.api}/users/${id}`, user);
  }

  deactivateUser(id: number): Observable<any> {
    return this.http.delete<any>(`${this.api}/users/${id}`);
  }

  // --- Bitácora de auditoría (CU36) ---
  getAuditLogs(): Observable<any[]> {
    return this.http.get<any[]>(`${this.api}/audit/logs`);
  }
}
