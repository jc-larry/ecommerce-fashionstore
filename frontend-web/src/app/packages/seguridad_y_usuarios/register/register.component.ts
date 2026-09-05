import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.css']
})
export class RegisterComponent {
  user = {
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  };
  
  acceptTerms = false;
  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(private authService: AuthService, private router: Router) {}

  // Regex para validación estricta de contraseña
  get hasMinLength() { return this.user.password.length >= 8; }
  get hasUppercase() { return /[A-Z]/.test(this.user.password); }
  get hasLowercase() { return /[a-z]/.test(this.user.password); }
  get hasNumber() { return /[0-9]/.test(this.user.password); }
  get hasSpecial() { return /[@$!%*?&]/.test(this.user.password); }
  
  get isPasswordStrong() {
    return this.hasMinLength && this.hasUppercase && this.hasLowercase && this.hasNumber && this.hasSpecial;
  }

  /**
   * [CU04] Auto-registro de cliente
   * @description Envía los datos del formulario al backend para crear una nueva cuenta de usuario.
   * El sistema asignará automáticamente el rol de CLIENTE.
   */
  // [CU04 - Paso 1] / [DSC004 - Paso 1] +llenarFormulario(datos)
  onSubmit() {
    this.errorMessage = '';
    this.successMessage = '';

    if (!this.user.firstName || !this.user.lastName || !this.user.email || !this.user.password || !this.user.confirmPassword) {
      this.errorMessage = 'Por favor, completa todos los campos requeridos.';
      return;
    }

    if (!this.isPasswordStrong) {
      this.errorMessage = 'La contraseña no cumple con todos los requisitos de seguridad.';
      return;
    }

    if (this.user.password !== this.user.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden.';
      return;
    }

    if (!this.acceptTerms) {
      this.errorMessage = 'Debes aceptar los términos y condiciones.';
      return;
    }

    this.loading = true;
    
    // Adaptar campos al esquema de la API (UserCreate / UserRegister).
    // El correo se normaliza; la contraseña se recorta de espacios al inicio/fin para que
    // coincida con lo que luego se escribe al iniciar sesión.
    const payload = {
      first_name: this.user.firstName.trim(),
      last_name: this.user.lastName.trim(),
      email: this.user.email.trim().toLowerCase(),
      phone: this.user.phone.trim(),
      password: this.user.password.trim()
    };

    // [CU04 - Paso 2] / [DSC004 - Paso 2] +register(datos)
    this.authService.registerClient(payload).subscribe({
      next: () => {
        this.loading = false;
        // [CU04 - Paso 7] / [DSC004 - Paso 7] +Notificar éxito
        this.successMessage = 'Cuenta creada con éxito. Redirigiendo al inicio de sesión…';
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (err: any) => {
        this.loading = false;
        if (err.status === 0) {
          this.errorMessage = 'No se pudo conectar con el servidor (¿está corriendo el backend en el puerto 8000?).';
        } else {
          this.errorMessage = err.error?.detail || `Ocurrió un error al crear la cuenta (código ${err.status}).`;
        }
      }
    });
  }
}
