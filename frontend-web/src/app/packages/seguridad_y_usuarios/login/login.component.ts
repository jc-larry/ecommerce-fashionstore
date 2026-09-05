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

  /**
   * [CU01] Iniciar sesión
   * @description Envía las credenciales al backend para autenticar la identidad del usuario.
   * Tras la autenticación exitosa, guarda el JWT y redirige al Dashboard o a la Tienda.
   */
  // [CU01 - Paso 1] / [DSC001 - Paso 1] +ingresar(email, password)
  onSubmit(event: Event) {
    event.preventDefault();
    // El correo se normaliza (minúsculas + sin espacios). La contraseña solo se recorta de
    // espacios al inicio/fin (frecuentes con el autocompletado del navegador o al pegar).
    const email = this.email.trim().toLowerCase();
    const password = this.password.trim();

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

        // Enrutar según el rol: panel para el personal, tienda para el cliente
        const destino = this.authService.isAdminUser() ? '/admin/dashboard' : '/tienda';
        // [CU01 - Paso 7] / [DSC001 - Paso 7] +Redirigir a Home
        setTimeout(() => this.router.navigate([destino]), 700);
      },
      error: (err: any) => {
        this.loading = false;
        if (err.status === 0) {
          this.errorMessage =
            'No se pudo conectar con el servidor (¿está corriendo el backend en el puerto 8000?).';
        } else {
          this.errorMessage =
            err.error?.detail || 'Error al iniciar sesión. Verifica tus credenciales.';
        }
      }
    });
  }
}
