import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface InAppNotification {
  id: number;
  title: string;
  message: string;
  notification_type: 'RESERVATION' | 'SHIPMENT' | 'ORDER' | 'SYSTEM' | 'PROMOTION';
  reference_id?: number;
  reference_type?: string;
  is_read: boolean;
  created_at: string;
}

export interface NotificationSummary {
  unread_count: number;
  notifications: InAppNotification[];
}

@Injectable({
  providedIn: 'root'
})
export class NotificacionesService {
  private baseUrl = `${environment.apiUrl}/notifications`;

  private unreadCountSubject = new BehaviorSubject<number>(0);
  public unreadCount$ = this.unreadCountSubject.asObservable();

  constructor(private http: HttpClient) {}

  getMyNotifications(unreadOnly: boolean = false): Observable<NotificationSummary> {
    return this.http.get<NotificationSummary>(`${this.baseUrl}/my?unread_only=${unreadOnly}`).pipe(
      tap(res => this.unreadCountSubject.next(res.unread_count))
    );
  }

  fetchUnreadCount(): void {
    this.http.get<{ unread_count: number }>(`${this.baseUrl}/unread-count`).subscribe({
      next: res => this.unreadCountSubject.next(res.unread_count),
      error: () => {}
    });
  }

  markAsRead(id: number): Observable<InAppNotification> {
    return this.http.patch<InAppNotification>(`${this.baseUrl}/${id}/read`, {}).pipe(
      tap(() => {
        const curr = this.unreadCountSubject.value;
        if (curr > 0) this.unreadCountSubject.next(curr - 1);
      })
    );
  }

  markAllAsRead(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/mark-all-read`, {}).pipe(
      tap(() => this.unreadCountSubject.next(0))
    );
  }
}
