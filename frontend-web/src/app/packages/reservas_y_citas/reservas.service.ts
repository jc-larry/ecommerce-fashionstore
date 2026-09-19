import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ReservationItem {
  id: number;
  variant_id: number;
  quantity: number;
  unit_price: number;
  notes?: string;
  product_name?: string;
  size_name?: string;
  color_name?: string;
  sku?: string;
  image_url?: string;
}

export interface Reservation {
  id: number;
  reservation_code: string;
  customer_id: number;
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  branch_id: number;
  branch_name?: string;
  branch_address?: string;
  status: 'PENDING' | 'PREPARING' | 'READY' | 'LATE' | 'NO_SHOW' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED';
  appointment_date?: string;
  appointment_time?: string;
  reschedule_count?: number;
  reserved_at: string;
  expires_at: string;
  notes?: string;
  total_amount?: number;
  deposit_amount?: number;
  balance_due?: number;
  payment_method?: string;
  payment_reference?: string;
  deposit_paid?: boolean;
  completed_sale_id?: number;
  items: ReservationItem[];
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ReservasService {
  private baseUrl = `${environment.apiUrl}/reservations`;

  constructor(private http: HttpClient) {}

  createReservation(data: {
    branch_id: number;
    items: { variant_id: number; quantity: number; notes?: string }[];
    notes?: string;
    appointment_date?: string;
    appointment_time?: string;
    payment_method?: string;
    payment_reference?: string;
    reserved_at?: string;
  }): Observable<Reservation> {
    return this.http.post<Reservation>(this.baseUrl, data);
  }

  getMyReservations(): Observable<Reservation[]> {
    return this.http.get<Reservation[]>(`${this.baseUrl}/my`);
  }

  getReservations(branchId?: number, statusFilter?: string): Observable<Reservation[]> {
    let params = new HttpParams();
    if (branchId) params = params.set('branch_id', branchId.toString());
    if (statusFilter) params = params.set('status', statusFilter);
    return this.http.get<Reservation[]>(this.baseUrl, { params });
  }

  getReservation(id: number): Observable<Reservation> {
    return this.http.get<Reservation>(`${this.baseUrl}/${id}`);
  }

  updateStatus(id: number, status: string): Observable<Reservation> {
    return this.http.patch<Reservation>(`${this.baseUrl}/${id}/status`, { status });
  }

  cancelReservation(id: number): Observable<Reservation> {
    return this.http.post<Reservation>(`${this.baseUrl}/${id}/cancel`, {});
  }

  convertToPos(id: number, data: {
    cash_shift_id: number;
    payment_method: string;
    cash_received?: number | null;
    card_brand?: string | null;
    card_last4?: string | null;
    payment_reference?: string | null;
    nit_ruc?: string;
    business_name?: string;
    selected_item_ids?: number[];
  }): Observable<Reservation> {
    return this.http.post<Reservation>(`${this.baseUrl}/${id}/convert-to-pos`, data);
  }
}
