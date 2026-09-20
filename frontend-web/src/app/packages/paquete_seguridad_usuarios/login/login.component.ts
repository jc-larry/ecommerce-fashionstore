import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  email = '';
  password = '';
  rememberMe = false;
  showPassword = false;

  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(private authService: AuthService, private router: Router) {}

  togglePassword() {
    this.showPassword = !this.showPassword;
  }

  quickLogin(email: string) {
    this.email = email;
    this.password = 'Password123!';
    this.errorMessage = '';
  }

  /**
   * [CU01] Iniciar sesión
   * @description Envía las credenciales al backend para autenticar la identidad del usuario.
   * Tras la autenticación exitosa, guarda el JWT y redirige al Dashboard, Portal o Tienda.
   */
  // [CU01 - Paso 1] / [DSC001 - Paso 1] +ingresar(email, password)
  onSubmit(event?: Event) {
    if (event) {
      event.preventDefault();
    }
    // El correo se normaliza (minúsculas + eliminando todos los espacios accidentales).
    const email = (this.email || '').replace(/\s+/g, '').toLowerCase();
    const password = (this.password || '').trim();

    if (!email || !password) {
      this.errorMessage = 'Por favor, ingresa tu correo y contraseña.';
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    // [CU01 - Paso 2] / [DSC001 - Paso 2] +login(email, password)
    this.authService.login({ email, password }).subscribe({
      next: () => {
        this.loading = false;
        this.successMessage = '¡Inicio de sesión correcto! Redirigiendo…';

        // Enrutar según el rol específico del actor
        let destino = '/tienda';
        if (this.authService.hasRole('PROVEEDOR') || this.authService.isProveedorUser()) {
          destino = '/proveedor';
        } else if (this.authService.hasRole('REPARTIDOR') || this.authService.isRepartidorUser()) {
          destino = '/repartidor';
        } else if (this.authService.isAdminUser() || this.authService.hasRole('SUPERADMIN') || this.authService.hasRole('ENCARGADO') || this.authService.hasRole('CAJERO')) {
          destino = '/admin/dashboard';
        }

        // [CU01 - Paso 7] / [DSC001 - Paso 7] +Redirigir
        setTimeout(() => this.router.navigate([destino]), 300);
      },
      error: (err: any) => {
        this.loading = false;
        if (err.status === 0) {
          this.errorMessage =
            'No se pudo conectar con el servidor backend (puerto 8000).';
        } else if (typeof err.error?.detail === 'string') {
          this.errorMessage = err.error.detail;
        } else if (Array.isArray(err.error?.detail)) {
          this.errorMessage = err.error.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
        } else if (err.error?.message) {
          this.errorMessage = err.error.message;
        } else {
          this.errorMessage = 'Credenciales incorrectas. Verifica tu correo y contraseña.';
        }
      }
    });
  }
}
