import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin, of, Subscription } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { DeliveryPersonProfile, LogisticaService, Shipment } from '../logistica.service';
import { AuthService } from '../../paquete_seguridad_usuarios/auth.service';

declare let L: any;

type DriverTab = 'disponibles' | 'activos' | 'historial';
const DRIVER_TABS: DriverTab[] = ['disponibles', 'activos', 'historial'];

/** Lado mayor (px) y calidad JPEG de la foto de evidencia antes de enviarla. */
const EVIDENCE_MAX_SIDE = 1024;
const EVIDENCE_JPEG_QUALITY = 0.7;

/**
 * [CU29 / CU30] Portal del Repartidor.
 * Bolsa de pedidos disponibles, entregas en curso del propio repartidor (con avance de ruta,
 * intento fallido y confirmación con foto de evidencia) e historial con tiempos reales.
 * Todos los datos vienen de endpoints con scope del repartidor autenticado.
 */
@Component({
  selector: 'app-delivery-portal',
  templateUrl: './delivery-portal.component.html',
  styleUrls: ['./delivery-portal.component.css']
})
export class DeliveryPortalComponent implements OnInit, OnDestroy {
  activeTab: DriverTab = 'activos';

  profile: DeliveryPersonProfile | null = null;
  profileMissing = false;
  driverName = '';

  available: Shipment[] = [];
  active: Shipment[] = [];
  history: Shipment[] = [];
  selected: Shipment | null = null;

  loading = false;
  processing = false;
  successMsg = '';
  errorMsg = '';

  // Confirmación de entrega con evidencia
  showEvidenceForm = false;
  evidencePhoto: string | null = null;
  evidenceReceivedBy = '';
  evidenceNotes = '';
  compressingPhoto = false;

  // Visor de foto ampliada
  photoPreview: string | null = null;

  private map: any = null;
  private routeSub?: Subscription;
  private originMarker: any = null;

  readonly statusLabels: Record<string, string> = {
    PENDING_DISPATCH: 'Disponible',
    ASSIGNED: 'Por recoger en tienda',
    PICKED_UP: 'Recogido',
    IN_TRANSIT: 'En camino',
    OUT_FOR_DELIVERY: 'Llegando al destino',
    DELIVERED: 'Entregado',
    FAILED_ATTEMPT: 'Intento fallido',
    RESCHEDULED: 'Reprogramado',
    RETURNED_TO_STORE: 'Devuelto a tienda',
  };

  constructor(
    private logistica: LogisticaService,
    public authService: AuthService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    const u = this.authService.getCurrentUser();
    this.driverName = u ? `${u.first_name || ''} ${u.last_name || ''}`.trim() : 'Repartidor';
    this.logistica.getMyDeliveryProfile().subscribe({
      next: (p) => (this.profile = p),
      error: () => (this.profileMissing = true),
    });
    this.loadAll();
    // La pestaña activa vive en ?tab= para que el menú lateral del portal la abra.
    this.routeSub = this.route.queryParamMap.subscribe((params) => {
      const tab = params.get('tab') as DriverTab | null;
      this.activeTab = tab && DRIVER_TABS.includes(tab) ? tab : 'activos';
      this.select(null);
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
    this.destroyMap();
  }

  // ---------- Carga de datos ----------
  loadAll(): void {
    this.loading = true;
    forkJoin({
      available: this.logistica.getAvailableShipments().pipe(catchError(() => of([] as Shipment[]))),
      active: this.logistica.getMyActiveShipments().pipe(catchError(() => of([] as Shipment[]))),
      history: this.logistica.getMyDeliveryHistory().pipe(catchError(() => of([] as Shipment[]))),
    }).subscribe(({ available, active, history }) => {
      this.available = available;
      this.active = active;
      this.history = history;
      this.loading = false;
      if (this.selected) {
        const refreshed = [...active, ...available, ...history].find((s) => s.id === this.selected!.id) || null;
        this.select(refreshed);
      }
    });
  }

  setTab(tab: DriverTab): void {
    this.router.navigate([], { relativeTo: this.route, queryParams: { tab }, queryParamsHandling: 'merge' });
  }

  get currentList(): Shipment[] {
    if (this.activeTab === 'disponibles') return this.available;
    if (this.activeTab === 'activos') return this.active;
    return this.history;
  }

  select(s: Shipment | null): void {
    this.selected = s;
    this.showEvidenceForm = false;
    this.evidencePhoto = null;
    setTimeout(() => this.renderMap(), 50);
  }

  // ---------- Métricas reales (calculadas del historial del propio repartidor) ----------
  private isToday(iso?: string | null): boolean {
    if (!iso) return false;
    const d = new Date(iso);
    const now = new Date();
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  }

  get deliveredToday(): Shipment[] {
    return this.history.filter((s) => s.status === 'DELIVERED' && this.isToday(s.delivered_at));
  }

  get freightToday(): number {
    return this.deliveredToday.reduce((acc, s) => acc + Number(s.shipping_cost || 0), 0);
  }

  /** Minutos entre que el repartidor tomó el pedido y lo entregó. */
  durationMinutes(s: Shipment): number | null {
    if (!s.claimed_at || !s.delivered_at) return null;
    const ms = new Date(s.delivered_at).getTime() - new Date(s.claimed_at).getTime();
    return ms >= 0 ? Math.round(ms / 60000) : null;
  }

  get averageDeliveryMinutes(): number | null {
    const values = this.history.map((s) => this.durationMinutes(s)).filter((m): m is number => m !== null);
    if (values.length === 0) return null;
    return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
  }

  formatDuration(minutes: number | null): string {
    if (minutes === null) return '—';
    if (minutes < 60) return `${minutes} min`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  }

  // ---------- Acciones ----------
  toggleAvailability(): void {
    if (!this.profile) return;
    this.logistica.setAvailability(!this.profile.is_available).subscribe({
      next: (p) => (this.profile = p),
      error: (e) => this.fail(e, 'No se pudo cambiar tu disponibilidad.'),
    });
  }

  claim(s: Shipment): void {
    this.run(this.logistica.claimShipment(s.id), `Tomaste el pedido ${s.tracking_number}. Recógelo en ${s.origin_branch_name || 'la sucursal'}.`, () => {
      this.setTab('activos');
    });
  }

  advance(status: 'PICKED_UP' | 'IN_TRANSIT' | 'OUT_FOR_DELIVERY'): void {
    if (!this.selected) return;
    this.run(this.logistica.updateRouteStatus(this.selected.id, status), `Estado actualizado: ${this.statusLabels[status]}.`);
  }

  release(): void {
    if (!this.selected) return;
    const reason = prompt('¿Por qué liberas este pedido?', 'Inconveniente con el repartidor');
    if (reason === null) return;
    this.run(this.logistica.releaseShipment(this.selected.id, reason || 'Sin motivo'), 'Pedido devuelto a la bolsa de disponibles.', () => this.select(null));
  }

  reportFailed(): void {
    if (!this.selected) return;
    const reason = prompt('Motivo del intento fallido', 'Cliente ausente');
    if (!reason || reason.trim().length < 3) return;
    this.run(this.logistica.reportFailedDelivery(this.selected.id, reason.trim()), 'Intento fallido registrado.');
  }

  canConfirmDelivery(s: Shipment): boolean {
    return ['PICKED_UP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'FAILED_ATTEMPT'].includes(s.status);
  }

  openEvidenceForm(): void {
    this.showEvidenceForm = true;
    this.evidencePhoto = null;
    this.evidenceReceivedBy = this.selected?.recipient_name || '';
    this.evidenceNotes = '';
  }

  onEvidenceFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      this.errorMsg = 'El archivo debe ser una foto.';
      return;
    }
    this.compressingPhoto = true;
    this.compressImage(file)
      .then((dataUrl) => (this.evidencePhoto = dataUrl))
      .catch(() => (this.errorMsg = 'No se pudo procesar la foto. Intenta tomarla de nuevo.'))
      .finally(() => (this.compressingPhoto = false));
  }

  confirmDelivery(): void {
    if (!this.selected) return;
    if (!this.evidencePhoto) {
      this.errorMsg = 'Toma una foto de la entrega como evidencia.';
      return;
    }
    if (this.evidenceReceivedBy.trim().length < 2) {
      this.errorMsg = 'Indica el nombre de la persona que recibió el pedido.';
      return;
    }
    this.run(
      this.logistica.confirmDelivery(this.selected.id, {
        photo_data_url: this.evidencePhoto,
        received_by_name: this.evidenceReceivedBy.trim(),
        notes: this.evidenceNotes.trim() || undefined,
      }),
      `Entrega de ${this.selected.tracking_number} confirmada con evidencia.`,
      () => {
        this.showEvidenceForm = false;
        this.setTab('historial');
      },
    );
  }

  openGoogleMaps(): void {
    if (!this.selected) return;
    const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(this.selected.delivery_address + ', Bolivia')}`;
    window.open(url, '_blank');
  }

  // ---------- Utilidades ----------
  private run(obs: any, okMessage: string, after?: () => void): void {
    this.processing = true;
    this.errorMsg = '';
    obs.subscribe({
      next: (updated: Shipment) => {
        this.processing = false;
        this.successMsg = okMessage;
        this.selected = updated;
        if (after) after();
        this.loadAll();
        setTimeout(() => (this.successMsg = ''), 4000);
      },
      error: (e: any) => {
        this.processing = false;
        this.fail(e, 'No se pudo completar la acción.');
      },
    });
  }

  private fail(e: any, fallback: string): void {
    this.errorMsg = e?.error?.detail || fallback;
  }

  /** Redimensiona y comprime la foto en el navegador para no enviar imágenes de varios MB. */
  private compressImage(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = () => {
        const img = new Image();
        img.onerror = reject;
        img.onload = () => {
          const scale = Math.min(1, EVIDENCE_MAX_SIDE / Math.max(img.width, img.height));
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(img.width * scale);
          canvas.height = Math.round(img.height * scale);
          const ctx = canvas.getContext('2d');
          if (!ctx) return reject(new Error('canvas'));
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', EVIDENCE_JPEG_QUALITY));
        };
        img.src = reader.result as string;
      };
      reader.readAsDataURL(file);
    });
  }

  private destroyMap(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  /** Solo se dibuja la sucursal de recojo con sus coordenadas reales; el destino se abre en Google Maps. */
  private renderMap(): void {
    this.destroyMap();
    const s = this.selected;
    const container = document.getElementById('driver-map');
    if (!s || !container || typeof L === 'undefined') return;
    if (s.origin_latitude == null || s.origin_longitude == null) return;

    this.map = L.map('driver-map').setView([s.origin_latitude, s.origin_longitude], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.map);
    const icon = L.divIcon({
      html: '<div style="background:#C66F5C;color:white;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);"><i class="bi bi-shop" style="font-size:16px;"></i></div>',
      className: '',
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });
    this.originMarker = L.marker([s.origin_latitude, s.origin_longitude], { icon }).addTo(this.map);
    this.originMarker.bindPopup(`<b>Recoger en</b><br>${s.origin_branch_name || 'Sucursal'}<br><small>${s.origin_branch_address || ''}</small>`).openPopup();
  }
}
