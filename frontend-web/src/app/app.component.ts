import { Component, HostListener, OnInit, OnDestroy } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from './packages/seguridad_y_usuarios/auth.service';
import { BranchContextService } from './packages/catalogo_y_tiendas/branches/branch-context.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit, OnDestroy {
  title = 'FashionStore';
  routeTitle = 'Panel Administrativo';

  private timeoutId: any;
  private readonly TIMEOUT_MS = 15 * 60 * 1000; // 15 minutos de inactividad

  private readonly routeTitles: Record<string, string> = {
    '/admin/dashboard': 'Dashboard',
    '/admin/usuarios': 'Usuarios y Roles',
    '/admin/branches': 'Sucursales',
    '/admin/products': 'Catálogo de Prendas',
    '/admin/suppliers': 'Gestión de Proveedores',
    '/admin/employees': 'Gestión de Empleados',
    '/admin/purchases': 'Registro de Mercadería',
    '/admin/audit': 'Bitácora de Auditoría',
  };

  activeBranchKey: string = 'central';

  constructor(
    public authService: AuthService,
    public branchContext: BranchContextService,
    private router: Router
  ) {}

  onBranchKeyChange(val: string): void {
    this.activeBranchKey = val;
    if (val === 'central') {
      this.branchContext.setActiveBranchById(null);
    } else {
      this.branchContext.setActiveBranchById(Number(val));
    }
  }

  onBranchChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.onBranchKeyChange(select.value);
  }

  showExitModal: boolean = false;

  openExitModal(): void {
    this.showExitModal = true;
  }

  cancelExitModal(): void {
    this.showExitModal = false;
  }

  confirmExitBranch(): void {
    this.showExitModal = false;
    this.branchContext.setActiveBranchById(null);
    this.router.navigate(['/admin/branches']);
  }

  ngOnInit() {
    this.branchContext.activeBranch$.subscribe((b) => {
      this.activeBranchKey = b ? b.id.toString() : 'central';
    });
    this.resetTimer();
    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => {
        this.routeTitle = this.routeTitles[e.urlAfterRedirects] ?? 'Panel Administrativo';
      });
  }

  ngOnDestroy() {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }
  }

  get userName(): string {
    const u = this.authService.getCurrentUser();
    return u ? `${u.first_name} ${u.last_name}` : 'Usuario';
  }

  get userRole(): string {
    return this.authService.getRoles()[0] ?? '';
  }

  get userInitials(): string {
    const u = this.authService.getCurrentUser();
    if (!u) return 'U';
    return `${(u.first_name || '?')[0]}${(u.last_name || '')[0] || ''}`.toUpperCase();
  }

  // [CU02 - Paso 1] / [DSC002 - Paso 1] +clicLogout()
  onLogout() {
    // [CU02 - Paso 2] / [DSC002 - Paso 2] +logout(token)
    this.authService.logout().subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => {
        this.authService.clearSession();
        this.router.navigate(['/login']);
      },
    });
  }

  @HostListener('window:mousemove')
  @HostListener('window:keydown')
  @HostListener('window:click')
  @HostListener('window:scroll')
  resetTimer() {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }
    if (this.authService.isLoggedIn()) {
      this.timeoutId = setTimeout(() => this.logoutUserDueToInactivity(), this.TIMEOUT_MS);
    }
  }

  private logoutUserDueToInactivity() {
    this.authService.clearSession();
    alert('Tu sesión ha expirado por inactividad (15 minutos).');
    this.router.navigate(['/login']);
  }
}
