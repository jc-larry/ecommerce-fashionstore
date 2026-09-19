import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface DeliveryZone {
  id: number;
  name: string;
  city: string;
  min_distance_km: number;
  max_distance_km: number;
  base_rate: number;
  estimated_hours: number;
  is_active: boolean;
  created_at: string;
}

export interface ShipmentTrackingEvent {
  id: number;
  status: string;
  location: string;
  description: string;
  photo_url?: string | null;
  created_at: string;
}

export type ShipmentStatus =
  | 'PENDING_DISPATCH' | 'ASSIGNED' | 'PICKED_UP' | 'IN_TRANSIT' | 'OUT_FOR_DELIVERY'
  | 'DELIVERED' | 'FAILED_ATTEMPT' | 'RESCHEDULED' | 'RETURNED_TO_STORE'
  | 'DISPATCHED' | 'FAILED';

export interface DeliveryPersonProfile {
  id: number;
  user_id: number;
  vehicle_type: string;
  vehicle_plate?: string | null;
  coverage_zone?: string | null;
  phone?: string | null;
  is_available: boolean;
  rating: number;
  total_deliveries: number;
}

export interface Shipment {
  id: number;
  tracking_number: string;
  order_id: number;
  zone_id?: number;
  zone_name?: string;
  carrier_name: string;
  carrier_phone?: string;
  delivery_address: string;
  recipient_name: string;
  recipient_phone: string;
  shipping_cost: number;
  status: ShipmentStatus;
  dispatched_at?: string;
  delivered_at?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
  delivery_person_id?: number | null;
  delivery_person_name?: string | null;
  claimed_at?: string | null;
  delivery_date?: string | null;
  delivery_time?: string | null;
  delivery_attempts?: number;
  failed_reason?: string | null;
  delivery_photo_url?: string | null;
  received_by_name?: string | null;
  origin_branch_id?: number | null;
  origin_branch_name?: string | null;
  origin_branch_address?: string | null;
  origin_latitude?: number | null;
  origin_longitude?: number | null;
  events: ShipmentTrackingEvent[];
}

@Injectable({
  providedIn: 'root'
})
export class LogisticaService {
  private baseUrl = `${environment.apiUrl}/logistics`;

  constructor(private http: HttpClient) {}

  // Zonas y Tarifas (CU31)
  getZones(activeOnly: boolean = false): Observable<DeliveryZone[]> {
    return this.http.get<DeliveryZone[]>(`${this.baseUrl}/zones?active_only=${activeOnly}`);
  }

  createZone(data: Partial<DeliveryZone>): Observable<DeliveryZone> {
    return this.http.post<DeliveryZone>(`${this.baseUrl}/zones`, data);
  }

  updateZone(id: number, data: Partial<DeliveryZone>): Observable<DeliveryZone> {
    return this.http.put<DeliveryZone>(`${this.baseUrl}/zones/${id}`, data);
  }

  calculateRate(distanceKm: number, zoneId?: number): Observable<{
    zone_id?: number;
    zone_name: string;
    rate: number;
    estimated_hours: number;
    distance_km: number;
  }> {
    return this.http.post<any>(`${this.baseUrl}/calculate-rate`, {
      distance_km: distanceKm,
      zone_id: zoneId
    });
  }

  // Despachos (CU29)
  createShipment(data: {
    order_id: number;
    zone_id?: number;
    carrier_name: string;
    carrier_phone?: string;
    delivery_address: string;
    recipient_name: string;
    recipient_phone: string;
    shipping_cost?: number;
    notes?: string;
  }): Observable<Shipment> {
    return this.http.post<Shipment>(`${this.baseUrl}/shipments`, data);
  }

  getShipments(statusFilter?: string): Observable<Shipment[]> {
    let params = new HttpParams();
    if (statusFilter) params = params.set('status', statusFilter);
    return this.http.get<Shipment[]>(`${this.baseUrl}/shipments`, { params });
  }

  getShipment(id: number): Observable<Shipment> {
    return this.http.get<Shipment>(`${this.baseUrl}/shipments/${id}`);
  }

  addTrackingEvent(shipmentId: number, data: {
    status: string;
    location: string;
    description: string;
  }): Observable<Shipment> {
    return this.http.post<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/events`, data);
  }

  // ---------- Portal del Repartidor (endpoints con scope del propio repartidor) ----------
  getMyDeliveryProfile(): Observable<DeliveryPersonProfile> {
    return this.http.get<DeliveryPersonProfile>(`${this.baseUrl}/delivery-persons/my`);
  }

  setAvailability(isAvailable: boolean): Observable<DeliveryPersonProfile> {
    const params = new HttpParams().set('is_available', String(isAvailable));
    return this.http.patch<DeliveryPersonProfile>(`${this.baseUrl}/delivery-persons/availability`, {}, { params });
  }

  getAvailableShipments(): Observable<Shipment[]> {
    return this.http.get<Shipment[]>(`${this.baseUrl}/shipments/available`);
  }

  getMyActiveShipments(): Observable<Shipment[]> {
    return this.http.get<Shipment[]>(`${this.baseUrl}/shipments/my-active`);
  }

  getMyDeliveryHistory(): Observable<Shipment[]> {
    return this.http.get<Shipment[]>(`${this.baseUrl}/shipments/my-history`);
  }

  claimShipment(shipmentId: number): Observable<Shipment> {
    return this.http.post<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/claim`, {});
  }

  releaseShipment(shipmentId: number, reason: string): Observable<Shipment> {
    const params = new HttpParams().set('reason', reason);
    return this.http.post<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/release`, {}, { params });
  }

  updateRouteStatus(shipmentId: number, status: 'PICKED_UP' | 'IN_TRANSIT' | 'OUT_FOR_DELIVERY', notes?: string): Observable<Shipment> {
    return this.http.patch<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/route-status`, { status, notes });
  }

  reportFailedDelivery(shipmentId: number, reason: string): Observable<Shipment> {
    return this.http.post<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/failed-delivery`, { reason });
  }

  confirmDelivery(shipmentId: number, data: { photo_data_url: string; received_by_name: string; notes?: string }): Observable<Shipment> {
    return this.http.post<Shipment>(`${this.baseUrl}/shipments/${shipmentId}/confirm-delivery`, data);
  }

  // Tracking Timeline Público (CU30)
  trackByCode(trackingNumber: string): Observable<Shipment> {
    return this.http.get<Shipment>(`${this.baseUrl}/track/${trackingNumber.trim()}`);
  }
}
