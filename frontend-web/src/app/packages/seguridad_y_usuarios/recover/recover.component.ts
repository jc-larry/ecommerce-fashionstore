import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-recover',
  templateUrl: './recover.component.html',
  styleUrls: ['./recover.component.css']
})
export class RecoverComponent implements OnInit {
  email = '';
  newPassword = '';
  confirmPassword = '';

  loading = false;

  /**
   * step 1 = pedir el enlace por correo.
   * step 2 = definir la nueva contraseña (SOLO se llega abriendo el enlace del correo).
   */
  step = 1;
  requested = false;   // ya se envió el correo (paso 1 completado)
  private token = '';  // viene únicamente de la URL (?token=...)

  errorMessage = '';
  successMessage = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (token) {
      this.token = token;
      this.step = 2;
    }
  }

  // Validación de fortaleza de la nueva contraseña
  get hasMinLength() { return this.newPassword.length >= 8; }
  get hasUppercase() { return /[A-Z]/.test(this.newPassword); }
  get hasLowercase() { return /[a-z]/.test(this.newPassword); }
  get hasNumber() { return /[0-9]/.test(this.newPassword); }
  get hasSpecial() { return /[@$!%*?&]/.test(this.newPassword); }

  get isPasswordStrong() {
    return this.hasMinLength && this.hasUppercase && this.hasLowercase && this.hasNumber && this.hasSpecial;
  }

  /**
   * [CU03 · Paso 1] Solicita el enlace de recuperación. NO muestra ningún campo de
   * token: la pantalla de "nueva contraseña" solo se abre desde el enlace del correo.
   */
  onRequestLink() {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.email) {
      this.errorMessage = 'Por favor, ingresa tu correo electrónico.';
      return;
    }

    this.loading = true;
    this.authService.recoverCredentials(this.email).subscribe({
      next: () => {
        this.loading = false;
        this.requested = true;
      },
      error: (err: any) => {
        this.loading = false;
        if (err.status === 0) {
          this.errorMessage = 'No se pudo conectar con el servidor (¿está corriendo el backend en el puerto 8000?).';
        } else {
          this.errorMessage = 'No se pudo procesar la solicitud. Inténtalo de nuevo en unos minutos.';
        }
      }
    });
  }

  /**
   * [CU03 · Paso 2] Define la nueva contraseña usando el token de la URL.
   */
  onResetPassword() {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.newPassword || !this.confirmPassword) {
      this.errorMessage = 'Por favor, completa los dos campos de contraseña.';
      return;
    }
    if (!this.isPasswordStrong) {
      this.errorMessage = 'La contraseña no cumple con todos los requisitos de seguridad.';
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden.';
      return;
    }

    this.loading = true;
    this.authService.resetPassword(this.token, this.newPassword).subscribe({
      next: () => {
        this.loading = false;
        this.successMessage = 'Tu contraseña ha sido restablecida con éxito. Redirigiendo al inicio de sesión…';
        setTimeout(() => this.router.navigate(['/login']), 2000);
      },
      error: (err: any) => {
        this.loading = false;
        this.errorMessage =
          err.error?.detail || 'El enlace es inválido o expiró (5 minutos). Solicita uno nuevo.';
      }
    });
  }
}
