import { Component, OnInit, AfterViewInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { LogisticaService, DeliveryZone } from '../logistica.service';
import { CatalogoService } from '../../catalogo_y_tiendas/catalogo.service';

declare let L: any;

@Component({
  selector: 'app-delivery-zones',
  templateUrl: './delivery-zones.component.html',
  styleUrls: ['./delivery-zones.component.css']
})
export class DeliveryZonesComponent implements OnInit, AfterViewInit, OnDestroy {
  zones: DeliveryZone[] = [];
  branches: any[] = [];
  selectedBranchId: number | null = null;
  selectedBranch: any = null;

  loading: boolean = false;
  successMsg: string = '';
  errorMsg: string = '';

  // Modal Nueva/Editar Zona
  showModal: boolean = false;
  editingZoneId: number | null = null;
  formName: string = '';
  formCity: string = 'Santa Cruz';
  formMinKm: number = 0;
  formMaxKm: number = 5;
  formRate: number = 15;
  formHours: number = 24;
  formActive: boolean = true;
  saving: boolean = false;

  // Calculadora interactiva y Mapa
  map: any = null;
  branchMarkers: any[] = [];
  zoneCircles: any[] = [];
  customerMarker: any = null;
  routeLine: any = null;

  customerLat: number = -17.7780;
  customerLng: number = -63.1750;
  customerAddress: string = 'Santa Cruz de la Sierra (Haga clic en el mapa para fijar dirección)';
  geocodingLoading: boolean = false;

  calculatedDistanceKm: number = 0;
  calculatedRate: number = 0;
  matchingZoneName: string = '';
  estimatedHours: number = 24;

  constructor(
    private logisticaService: LogisticaService,
    private catalogoService: CatalogoService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadZones();
    this.loadBranches();
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      this.initMap();
    }, 400);
  }

  ngOnDestroy(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  loadZones(): void {
    this.loading = true;
    this.logisticaService.getZones(false).subscribe({
      next: (data) => {
        this.zones = data;
        this.loading = false;
        this.renderZoneCircles();
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cargar las zonas de entrega.';
        this.loading = false;
      }
    });
  }

  loadBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (bList: any[]) => {
        // Asignar coordenadas por defecto si alguna sucursal no las tiene registradas
        this.branches = bList.map((b, idx) => {
          let lat = b.latitude ? parseFloat(b.latitude) : null;
          let lng = b.longitude ? parseFloat(b.longitude) : null;
          if (!lat || !lng) {
            if (idx === 0) { lat = -17.7650; lng = -63.1950; } // Equipetrol
            else if (idx === 1) { lat = -17.7833; lng = -63.1821; } // Centro
            else { lat = -17.7950; lng = -63.1700; } // Las Brisas / Sur
          }
          return { ...b, latitude: lat, longitude: lng };
        });

        if (this.branches.length > 0) {
          this.selectedBranchId = this.branches[0].id;
          this.selectedBranch = this.branches[0];
        }
        this.updateBranchMarkers();
        this.renderZoneCircles();
        this.recalculateDelivery();
      },
      error: () => {}
    });
  }

  initMap(): void {
    if (typeof L === 'undefined') {
      console.warn('Leaflet no está disponible aún.');
      return;
    }
    const mapContainer = document.getElementById('delivery-map');
    if (!mapContainer) return;

    if (this.map) {
      this.map.remove();
      this.map = null;
    }

    const defaultLat = -17.7833;
    const defaultLng = -63.1821;

    this.map = L.map('delivery-map').setView([defaultLat, defaultLng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap FashionStore Logistics'
    }).addTo(this.map);

    this.updateBranchMarkers();
    this.renderZoneCircles();

    // Marcador del cliente / destino
    const customerIcon = L.divIcon({
      html: '<div style="background:#dc3545; color:white; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 3px 8px rgba(0,0,0,0.4); border:3px solid white;"><i class="bi bi-geo-alt-fill" style="font-size:18px;"></i></div>',
      className: '',
      iconSize: [34, 34],
      iconAnchor: [17, 34]
    });

    this.customerMarker = L.marker([this.customerLat, this.customerLng], {
      icon: customerIcon,
      draggable: true
    }).addTo(this.map);

    this.customerMarker.bindPopup('<b>Punto de Entrega del Cliente</b><br>Arrastre o haga clic para reubicar.').openPopup();

    this.customerMarker.on('dragend', () => {
      const pos = this.customerMarker.getLatLng();
      this.setCustomerLocation(pos.lat, pos.lng);
    });

    this.map.on('click', (e: any) => {
      this.customerMarker.setLatLng(e.latlng);
      this.setCustomerLocation(e.latlng.lat, e.latlng.lng);
    });

    setTimeout(() => {
      if (this.map) this.map.invalidateSize();
    }, 300);

    this.recalculateDelivery();
  }

  onBranchChange(): void {
    const found = this.branches.find(b => b.id === Number(this.selectedBranchId));
    if (found) {
      this.selectedBranch = found;
      this.renderZoneCircles();
      this.recalculateDelivery();
    }
  }

  updateBranchMarkers(): void {
    if (!this.map || typeof L === 'undefined') return;

    this.branchMarkers.forEach(m => this.map.removeLayer(m));
    this.branchMarkers = [];

    const storeIcon = L.divIcon({
      html: '<div style="background:#0d6efd; color:white; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; box-shadow:0 3px 10px rgba(13,110,253,0.5); border:3px solid white;"><i class="bi bi-shop" style="font-size:18px;"></i></div>',
      className: '',
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    this.branches.forEach(b => {
      if (b.latitude && b.longitude) {
        const marker = L.marker([b.latitude, b.longitude], { icon: storeIcon }).addTo(this.map);
        marker.bindPopup(`<b>${b.name}</b><br><small>${b.address}</small><br><span class="badge bg-primary mt-1">Punto de Retiro</span>`);
        this.branchMarkers.push(marker);
      }
    });
  }

  renderZoneCircles(): void {
    if (!this.map || typeof L === 'undefined' || !this.selectedBranch) return;

    this.zoneCircles.forEach(c => this.map.removeLayer(c));
    this.zoneCircles = [];

    const centerLat = this.selectedBranch.latitude || -17.7833;
    const centerLng = this.selectedBranch.longitude || -63.1821;

    const colors = ['#0dcaf0', '#198754', '#ffc107', '#fd7e14', '#6f42c1'];

    this.zones.forEach((z, idx) => {
      if (!z.is_active) return;
      const color = colors[idx % colors.length];
      const circle = L.circle([centerLat, centerLng], {
        color: color,
        fillColor: color,
        fillOpacity: 0.10,
        weight: 2,
        dashArray: '4, 4',
        radius: z.max_distance_km * 1000
      }).addTo(this.map);

      circle.bindTooltip(`<b>${z.name}</b> (Hasta ${z.max_distance_km} km) - Bs. ${z.base_rate}`, {
        permanent: false,
        direction: 'center'
      });

      this.zoneCircles.push(circle);
    });
  }

  setCustomerLocation(lat: number, lng: number): void {
    this.customerLat = lat;
    this.customerLng = lng;
    this.recalculateDelivery();
    this.reverseGeocode(lat, lng);
  }

  useCurrentGPS(): void {
    if (!navigator.geolocation) {
      this.errorMsg = 'Geolocalización no soportada por su navegador.';
      return;
    }
    this.geocodingLoading = true;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.geocodingLoading = false;
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (this.customerMarker) {
          this.customerMarker.setLatLng([lat, lng]);
        }
        if (this.map) {
          this.map.setView([lat, lng], 14);
        }
        this.setCustomerLocation(lat, lng);
      },
      () => {
        this.geocodingLoading = false;
        this.errorMsg = 'No se pudo obtener su ubicación GPS. Por favor haga clic sobre el mapa.';
        setTimeout(() => (this.errorMsg = ''), 4000);
      }
    );
  }

  reverseGeocode(lat: number, lng: number): void {
    this.geocodingLoading = true;
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`;
    this.http.get<any>(url).subscribe({
      next: (res) => {
        this.geocodingLoading = false;
        if (res && res.display_name) {
          const parts = res.display_name.split(',');
          this.customerAddress = parts.slice(0, 3).join(',').trim();
        } else {
          this.customerAddress = `Ubicación: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        }
      },
      error: () => {
        this.geocodingLoading = false;
        this.customerAddress = `Ubicación: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      }
    });
  }

  recalculateDelivery(): void {
    if (!this.selectedBranch) return;

    const bLat = this.selectedBranch.latitude || -17.7833;
    const bLng = this.selectedBranch.longitude || -63.1821;

    // Fórmula Haversine
    this.calculatedDistanceKm = this.haversine(bLat, bLng, this.customerLat, this.customerLng);

    // Trazar línea de ruta en el mapa
    if (this.map && typeof L !== 'undefined') {
      if (this.routeLine) {
        this.map.removeLayer(this.routeLine);
      }
      this.routeLine = L.polyline([[bLat, bLng], [this.customerLat, this.customerLng]], {
        color: '#dc3545',
        weight: 3,
        dashArray: '6, 8',
        opacity: 0.85
      }).addTo(this.map);
    }

    // Identificar zona aplicable y calcular tarifa
    const match = this.zones.find(
      z => z.is_active && this.calculatedDistanceKm >= z.min_distance_km && this.calculatedDistanceKm <= z.max_distance_km
    );

    if (match) {
      this.matchingZoneName = match.name;
      this.estimatedHours = match.estimated_hours;
      // Fórmula oficial: Tarifa Base + (Distancia * Costo/km incremental)
      this.calculatedRate = Math.round((Number(match.base_rate) + (this.calculatedDistanceKm * 1.5)) * 100) / 100;
    } else {
      // Fuera de radio estándar
      this.matchingZoneName = 'Zona Extendida / Radio Periférico';
      this.estimatedHours = 36;
      this.calculatedRate = Math.round((25 + (this.calculatedDistanceKm * 2.5)) * 100) / 100;
    }
  }

  private haversine(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371; // Radio de la tierra en km
    const dLat = (lat2 - lat1) * (Math.PI / 180);
    const dLon = (lon2 - lon1) * (Math.PI / 180);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return Math.round(R * c * 100) / 100;
  }

  // Modales CRUD
  openCreate(): void {
    this.editingZoneId = null;
    this.formName = '';
    this.formCity = 'Santa Cruz';
    this.formMinKm = 0;
    this.formMaxKm = 5;
    this.formRate = 15;
    this.formHours = 24;
    this.formActive = true;
    this.showModal = true;
  }

  openEdit(z: DeliveryZone): void {
    this.editingZoneId = z.id;
    this.formName = z.name;
    this.formCity = z.city;
    this.formMinKm = z.min_distance_km;
    this.formMaxKm = z.max_distance_km;
    this.formRate = z.base_rate;
    this.formHours = z.estimated_hours;
    this.formActive = z.is_active;
    this.showModal = true;
  }

  closeModal(): void {
    this.showModal = false;
  }

  saveZone(): void {
    if (!this.formName) {
      this.errorMsg = 'El nombre de la zona es obligatorio.';
      return;
    }
    this.saving = true;
    const payload = {
      name: this.formName,
      city: this.formCity,
      min_distance_km: this.formMinKm,
      max_distance_km: this.formMaxKm,
      base_rate: this.formRate,
      estimated_hours: this.formHours,
      is_active: this.formActive
    };

    if (this.editingZoneId) {
      this.logisticaService.updateZone(this.editingZoneId, payload).subscribe({
        next: () => {
          this.saving = false;
          this.successMsg = 'Zona de entrega actualizada exitosamente.';
          this.closeModal();
          this.loadZones();
          setTimeout(() => (this.successMsg = ''), 3500);
        },
        error: (err) => {
          this.saving = false;
          this.errorMsg = err.error?.detail || 'Error al actualizar zona.';
          setTimeout(() => (this.errorMsg = ''), 3500);
        }
      });
    } else {
      this.logisticaService.createZone(payload).subscribe({
        next: () => {
          this.saving = false;
          this.successMsg = 'Nueva zona registrada exitosamente.';
          this.closeModal();
          this.loadZones();
          setTimeout(() => (this.successMsg = ''), 3500);
        },
        error: (err) => {
          this.saving = false;
          this.errorMsg = err.error?.detail || 'Error al crear zona.';
          setTimeout(() => (this.errorMsg = ''), 3500);
        }
      });
    }
  }
}
