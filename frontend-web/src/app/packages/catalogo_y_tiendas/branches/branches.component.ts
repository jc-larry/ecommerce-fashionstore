import { Component, OnInit } from '@angular/core';
import { CatalogoService } from '../catalogo.service';
import { UsersService } from '../../seguridad_y_usuarios/users.service';

declare let L: any;

@Component({
  selector: 'app-branches',
  templateUrl: './branches.component.html',
  styleUrls: ['./branches.component.css']
})
export class BranchesComponent implements OnInit {
  branches: any[] = [];
  staff: any[] = []; // usuarios ENCARGADO / CAJERO
  loading = false;
  error = '';

  showForm = false;
  editingId: number | null = null;
  form = this.emptyForm();
  activeTab: 'info' | 'map' | 'ops' = 'info';

  // Mapa interactivo Leaflet
  private map: any = null;
  private marker: any = null;
  gettingLocation = false;
  geoError = '';
  uploadingImage = false;

  // Asignación de empleados
  assignBranch: any = null;
  assignUserId: number | null = null;

  constructor(private catalogo: CatalogoService, private users: UsersService) {}

  ngOnInit(): void {
    this.load();
    this.loadStaff();
  }

  emptyForm() {
    return {
      name: '',
      code: '',
      city: 'Santa Cruz',
      zone: '',
      address: '',
      reference: '',
      phone: '',
      whatsapp: '',
      opening_time: '09:00',
      closing_time: '21:00',
      days_open: 'Lunes a Sábado',
      has_fitting_room: true,
      pickup_enabled: true,
      image_url: '',
      latitude: -17.7833 as number | null,
      longitude: -63.1821 as number | null,
      is_active: true
    };
  }

  load(): void {
    this.loading = true;
    this.catalogo.getBranches().subscribe({
      next: (data) => { this.branches = data; this.loading = false; },
      error: () => { this.error = 'No se pudieron cargar las sucursales.'; this.loading = false; },
    });
  }

  loadStaff(): void {
    this.users.getUsers().subscribe({
      next: (data) => {
        this.staff = data.filter((u: any) =>
          (u.roles || []).some((r: any) => ['ENCARGADO', 'CAJERO'].includes(r.name)));
      },
      error: () => {},
    });
  }

  managerOf(branch: any): string {
    const enc = (branch.employees || []).find((e: any) => (e.roles || []).some((r: any) => r.name === 'ENCARGADO'));
    const any = (branch.employees || [])[0];
    const u = enc || any;
    return u ? `${u.first_name} ${u.last_name}` : 'Sin asignar';
  }

  setTab(tab: 'info' | 'map' | 'ops'): void {
    this.activeTab = tab;
    if (tab === 'map') {
      setTimeout(() => {
        if (!this.map) {
          this.initMap();
        } else {
          this.map.invalidateSize();
        }
      }, 150);
    }
  }

  openNew(): void {
    this.editingId = null;
    this.form = this.emptyForm();
    this.activeTab = 'info';
    this.geoError = '';
    this.showForm = true;
  }

  openEdit(b: any): void {
    this.editingId = b.id;
    this.form = {
      name: b.name,
      code: b.code || '',
      city: b.city || 'Santa Cruz',
      zone: b.zone || '',
      address: b.address,
      reference: b.reference || '',
      phone: b.phone || '',
      whatsapp: b.whatsapp || '',
      opening_time: b.opening_time || '09:00',
      closing_time: b.closing_time || '21:00',
      days_open: b.days_open || 'Lunes a Sábado',
      has_fitting_room: b.has_fitting_room ?? true,
      pickup_enabled: b.pickup_enabled ?? true,
      image_url: b.image_url || '',
      latitude: b.latitude ? Number(b.latitude) : -17.7833,
      longitude: b.longitude ? Number(b.longitude) : -63.1821,
      is_active: b.is_active,
    };
    this.activeTab = 'info';
    this.geoError = '';
    this.showForm = true;
  }

  closeForm(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
      this.marker = null;
    }
    this.showForm = false;
  }

  initMap(): void {
    if (typeof L === 'undefined') {
      console.warn('Leaflet aún no está cargado');
      return;
    }
    const el = document.getElementById('branch-map');
    if (!el) return;

    if (this.map) {
      this.map.remove();
      this.map = null;
      this.marker = null;
    }

    const lat = this.form.latitude || -17.7833;
    const lng = this.form.longitude || -63.1821;
    const hasCustomCoords = !!(this.form.latitude && this.form.longitude);

    this.map = L.map('branch-map').setView([lat, lng], hasCustomCoords ? 15 : 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(this.map);

    this.marker = L.marker([lat, lng], { draggable: true }).addTo(this.map);

    this.marker.on('dragend', () => {
      const pos = this.marker.getLatLng();
      this.updateCoords(pos.lat, pos.lng);
    });

    this.map.on('click', (e: any) => {
      this.marker.setLatLng(e.latlng);
      this.updateCoords(e.latlng.lat, e.latlng.lng);
    });

    setTimeout(() => {
      if (this.map) this.map.invalidateSize();
    }, 200);
  }

  updateCoords(lat: number, lng: number): void {
    this.form.latitude = Number(lat.toFixed(6));
    this.form.longitude = Number(lng.toFixed(6));
  }

  useCurrentLocation(): void {
    if (!navigator.geolocation) {
      this.geoError = 'La geolocalización no está soportada en tu navegador.';
      return;
    }
    this.gettingLocation = true;
    this.geoError = '';
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        this.updateCoords(lat, lng);
        if (this.map && this.marker) {
          this.marker.setLatLng([lat, lng]);
          this.map.setView([lat, lng], 16);
        }
        this.gettingLocation = false;
      },
      (err) => {
        this.geoError = `No se pudo obtener la ubicación GPS (${err.message}). Haz clic en el mapa para marcarla.`;
        this.gettingLocation = false;
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  onFileSelected(event: any): void {
    const file = event.target?.files?.[0];
    if (!file) return;
    this.uploadingImage = true;
    this.catalogo.uploadImage(file).subscribe({
      next: (res) => {
        this.form.image_url = res.image_url;
        this.uploadingImage = false;
      },
      error: (err) => {
        this.error = err.error?.detail || 'Error al subir la foto de la fachada.';
        this.uploadingImage = false;
      }
    });
  }

  resolveImg(url?: string | null): string {
    return this.catalogo.resolveImageUrl(url);
  }

  save(): void {
    this.error = '';
    const req = this.editingId
      ? this.catalogo.updateBranch(this.editingId, this.form)
      : this.catalogo.createBranch(this.form);
    req.subscribe({
      next: () => {
        this.load();
        this.closeForm();
      },
      error: (e) => (this.error = e.error?.detail || 'Error al guardar la sucursal.'),
    });
  }

  deactivate(b: any): void {
    if (!confirm(`¿Desactivar la sucursal ${b.name}?`)) return;
    this.catalogo.deactivateBranch(b.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al desactivar.'),
    });
  }

  openAssign(b: any): void {
    this.assignBranch = b;
    this.assignUserId = null;
  }

  closeAssign(): void {
    this.assignBranch = null;
  }

  confirmAssign(): void {
    if (!this.assignBranch || !this.assignUserId) return;
    this.catalogo.assignEmployee(this.assignBranch.id, Number(this.assignUserId)).subscribe({
      next: () => {
        this.load();
        this.closeAssign();
      },
      error: (e) => (this.error = e.error?.detail || 'Error al asignar el empleado.'),
    });
  }

  removeEmployee(branch: any, user: any): void {
    if (!confirm(`¿Quitar a ${user.first_name} ${user.last_name} de ${branch.name}?`)) return;
    this.catalogo.removeEmployee(branch.id, user.id).subscribe({
      next: () => this.load(),
      error: (e) => (this.error = e.error?.detail || 'Error al quitar el empleado.'),
    });
  }
}
