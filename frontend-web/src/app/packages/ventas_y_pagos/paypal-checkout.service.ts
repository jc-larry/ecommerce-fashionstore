import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, firstValueFrom, shareReplay } from 'rxjs';
import { environment } from '../../../environments/environment';
import { VentasService } from './ventas.service';

/** Configuración pública que expone el backend en GET /payments/paypal/config. */
export interface PayPalConfig {
  client_id: string | null;
  mode: 'sandbox' | 'live' | string;
  currency: string;
  exchange_rate_bob_usd: number;
  /** true = no hay credenciales en el backend y se usa el simulador local. */
  simulated: boolean;
}

/** Respuesta de POST /payments/paypal/capture-order. */
export interface PayPalCaptureResult {
  id: string;
  status: string;
  capture_id: string;
  gateway_reference: string;
  simulated: boolean;
  payer?: {
    payer_id?: string;
    email_address?: string | null;
    name?: { given_name?: string; surname?: string };
  };
}

export interface PayPalButtonsOptions {
  amountBob: number;
  description: string;
  onApproved: (capture: PayPalCaptureResult) => void;
  onError: (message: string) => void;
  onCancel?: () => void;
}

/** Subconjunto tipado del objeto global `paypal` que inyecta el SDK JS. */
interface PayPalButtonsInstance {
  render(container: HTMLElement): Promise<void>;
  close?(): Promise<void>;
}
interface PayPalNamespace {
  Buttons(options: {
    style?: Record<string, string | number>;
    createOrder: () => Promise<string>;
    onApprove: (data: { orderID: string }) => Promise<void>;
    onCancel?: () => void;
    onError?: (err: unknown) => void;
  }): PayPalButtonsInstance;
}

const SDK_SCRIPT_ID = 'paypal-js-sdk';

/**
 * Integración real con PayPal Checkout (Smart Payment Buttons).
 *
 * Flujo: el SDK abre la ventana oficial de PayPal → `createOrder` pide al backend que cree la
 * orden (REST v2) → el comprador inicia sesión con su cuenta sandbox y aprueba → `onApprove`
 * pide al backend capturar los fondos. El Secret nunca llega al navegador.
 */
@Injectable({ providedIn: 'root' })
export class PayPalCheckoutService {
  private readonly configUrl = `${environment.apiUrl}/payments/paypal/config`;
  private config$?: Observable<PayPalConfig>;
  private sdkPromise?: Promise<PayPalNamespace>;

  constructor(
    private http: HttpClient,
    private ventasService: VentasService,
    private zone: NgZone
  ) {}

  /** Configuración pública (cacheada durante la sesión). */
  getConfig(): Observable<PayPalConfig> {
    if (!this.config$) {
      this.config$ = this.http.get<PayPalConfig>(this.configUrl).pipe(shareReplay(1));
    }
    return this.config$;
  }

  /** Dibuja los botones oficiales de PayPal dentro de `container`. */
  async renderButtons(container: HTMLElement, opts: PayPalButtonsOptions): Promise<void> {
    const config = await firstValueFrom(this.getConfig());
    if (config.simulated || !config.client_id) {
      throw new Error('PayPal está en modo simulación (sin credenciales en el backend).');
    }
    const paypal = await this.loadSdk(config.client_id, config.currency);
    container.innerHTML = '';

    await paypal.Buttons({
      style: { layout: 'vertical', color: 'gold', shape: 'pill', label: 'pay', height: 42 },
      createOrder: async () => {
        try {
          const order = await firstValueFrom(
            this.ventasService.createPayPalOrder(opts.amountBob, opts.description)
          );
          return order.id as string;
        } catch (e) {
          this.zone.run(() => opts.onError(this.errorDetail(e, 'No se pudo crear la orden en PayPal.')));
          throw e;
        }
      },
      onApprove: async (data) => {
        try {
          const capture = await firstValueFrom(this.ventasService.capturePayPalOrder(data.orderID));
          this.zone.run(() => opts.onApproved(capture as PayPalCaptureResult));
        } catch (e) {
          this.zone.run(() => opts.onError(this.errorDetail(e, 'PayPal no confirmó el pago. No se realizó ningún cobro.')));
        }
      },
      onCancel: () => this.zone.run(() => opts.onCancel?.()),
      onError: () => this.zone.run(() => opts.onError('Ocurrió un error en la ventana de PayPal. Intenta nuevamente.')),
    }).render(container);
  }

  /** Carga una sola vez el SDK JS de PayPal con el Client ID configurado en el backend. */
  private loadSdk(clientId: string, currency: string): Promise<PayPalNamespace> {
    const w = window as unknown as { paypal?: PayPalNamespace };
    if (w.paypal) return Promise.resolve(w.paypal);
    if (this.sdkPromise) return this.sdkPromise;

    this.sdkPromise = new Promise<PayPalNamespace>((resolve, reject) => {
      const script = document.createElement('script');
      script.id = SDK_SCRIPT_ID;
      script.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}`
        + `&currency=${encodeURIComponent(currency)}&intent=capture&components=buttons`;
      script.async = true;
      script.onload = () => (w.paypal ? resolve(w.paypal) : reject(new Error('SDK de PayPal no disponible.')));
      script.onerror = () => {
        this.sdkPromise = undefined;
        script.remove();
        reject(new Error('No se pudo cargar el SDK de PayPal. Revisa tu conexión a internet.'));
      };
      document.head.appendChild(script);
    });
    return this.sdkPromise;
  }

  private errorDetail(e: unknown, fallback: string): string {
    const detail = (e as { error?: { detail?: unknown } })?.error?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }
}
