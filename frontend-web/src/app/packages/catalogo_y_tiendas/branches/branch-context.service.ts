import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { CatalogoService, BranchOption } from '../catalogo.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

const STORAGE_KEY = 'fashionstore_active_branch_id';

@Injectable({
  providedIn: 'root'
})
export class BranchContextService {
  private branchesSubject = new BehaviorSubject<BranchOption[]>([]);
  public branches$ = this.branchesSubject.asObservable();

  // null = Casa Matriz (Central / Consolidado)
  private activeBranchSubject = new BehaviorSubject<BranchOption | null>(null);
  public activeBranch$ = this.activeBranchSubject.asObservable();

  constructor(private catalogoService: CatalogoService, private authService: AuthService) {
    // El servicio nace antes del login: se recalcula la sucursal cada vez que cambia el
    // usuario de la sesión, para que un cajero/encargado entre directo a su sucursal asignada.
    let lastUserKey: string | null = null;
    this.authService.currentUser$.subscribe((user) => {
      const key = user ? `${user.id}:${user.branch_id ?? ''}` : '';
      if (key === lastUserKey) return;
      lastUserKey = key;
      this.initBranches();
    });
  }

  public initBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (branches: any[]) => {
        const formatted: BranchOption[] = branches.map(b => ({
          id: b.id,
          name: b.name,
          code: b.code || null,
          city: b.city || null,
          is_active: b.is_active,
          is_temporarily_closed: !!b.is_temporarily_closed,
          closure_reason: b.closure_reason || null,
          opening_time: b.opening_time,
          closing_time: b.closing_time,
          days_open: b.days_open,
          has_fitting_room: b.has_fitting_room,
          pickup_enabled: b.pickup_enabled,
        }));
        this.branchesSubject.next(formatted);

        // [Separación por sucursal] ENCARGADO/CAJERO quedan siempre fijos a su propia
        // sucursal (resuelta por el backend en /auth/me) — no pueden elegir otra ni "Casa Matriz".
        if (!this.authService.isCentralUser()) {
          const own = this.authService.getCurrentUser()?.branch_id;
          const found = own != null ? formatted.find(b => b.id === own) : undefined;
          this.activeBranchSubject.next(found ?? null);
          return;
        }

        // Restaurar sucursal guardada si existe en localStorage (solo SUPERADMIN)
        const savedId = localStorage.getItem(STORAGE_KEY);
        if (savedId && savedId !== 'central') {
          const found = formatted.find(b => b.id === Number(savedId));
          if (found) {
            this.activeBranchSubject.next(found);
          } else {
            this.activeBranchSubject.next(null);
          }
        } else {
          this.activeBranchSubject.next(null);
        }
      },
      error: () => {
        this.branchesSubject.next([]);
      }
    });
  }

  public setActiveBranch(branch: BranchOption | null): void {
    if (!this.authService.isCentralUser()) {
      // Defensa de UX: la barrera real de seguridad es el backend, esto solo evita
      // que la interfaz cambie de sucursal para personal que no es de Casa Matriz.
      console.warn('[BranchContext] Cambio de sucursal ignorado: el usuario no es central.');
      return;
    }
    this.activeBranchSubject.next(branch);
    if (branch) {
      localStorage.setItem(STORAGE_KEY, branch.id.toString());
    } else {
      localStorage.setItem(STORAGE_KEY, 'central');
    }
  }

  public getActiveBranch(): BranchOption | null {
    return this.activeBranchSubject.getValue();
  }

  public getActiveBranchId(): number | null {
    const b = this.getActiveBranch();
    return b ? b.id : null;
  }

  /** Solo SUPERADMIN puede estar en modo Casa Matriz; el personal de sucursal nunca, aunque aún no tenga sucursal asignada. */
  public isCentral(): boolean {
    return this.authService.isCentralUser() && this.activeBranchSubject.getValue() === null;
  }

  /** Personal de sucursal (ENCARGADO/CAJERO) sin sucursal asignada por el administrador. */
  public hasNoAssignedBranch(): boolean {
    return !this.authService.isCentralUser() && this.authService.getCurrentUser()?.branch_id == null;
  }

  public getBranches(): BranchOption[] {
    return this.branchesSubject.getValue();
  }

  public setActiveBranchById(id: number | null): void {
    if (!this.authService.isCentralUser()) {
      console.warn('[BranchContext] Cambio de sucursal ignorado: el usuario no es central.');
      return;
    }
    if (id === null) {
      this.setActiveBranch(null);
      return;
    }
    const currentList = this.branchesSubject.getValue();
    const found = currentList.find(b => b.id === id);
    if (found) {
      this.setActiveBranch(found);
    } else {
      localStorage.setItem(STORAGE_KEY, id.toString());
      this.catalogoService.getBranches().subscribe({
        next: (branches: any[]) => {
          const b = branches.find((item: any) => item.id === id);
          if (b) {
            this.setActiveBranch({
              id: b.id,
              name: b.name,
              code: b.code || null,
              city: b.city || null,
            });
          }
        }
      });
    }
  }
}
