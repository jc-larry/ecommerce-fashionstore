import { Component, OnInit } from '@angular/core';
import { NotificacionesService, InAppNotification } from '../notificaciones.service';
import { AuthService } from '../../seguridad_y_usuarios/auth.service';

@Component({
  selector: 'app-notifications-dropdown',
  templateUrl: './notifications-dropdown.component.html',
  styleUrls: ['./notifications-dropdown.component.css']
})
export class NotificationsDropdownComponent implements OnInit {
  notifications: InAppNotification[] = [];
  unreadCount: number = 0;
  isOpen: boolean = false;
  loading: boolean = false;

  constructor(
    public notificacionesService: NotificacionesService,
    public authService: AuthService
  ) {}

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.notificacionesService.unreadCount$.subscribe(c => (this.unreadCount = c));
      this.notificacionesService.fetchUnreadCount();
    }
  }

  toggleDropdown(): void {
    this.isOpen = !this.isOpen;
    if (this.isOpen) {
      this.loadNotifications();
    }
  }

  loadNotifications(): void {
    this.loading = true;
    this.notificacionesService.getMyNotifications().subscribe({
      next: (res) => {
        this.notifications = res.notifications;
        this.unreadCount = res.unread_count;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  markRead(n: InAppNotification, event: Event): void {
    event.stopPropagation();
    if (n.is_read) return;
    this.notificacionesService.markAsRead(n.id).subscribe({
      next: () => {
        n.is_read = true;
      }
    });
  }

  markAllRead(): void {
    this.notificacionesService.markAllAsRead().subscribe({
      next: () => {
        this.notifications.forEach(n => (n.is_read = true));
        this.unreadCount = 0;
      }
    });
  }

  getIcon(type: string): string {
    switch (type) {
      case 'RESERVATION': return 'bi-door-open-fill text-warning';
      case 'SHIPMENT': return 'bi-truck text-primary';
      case 'ORDER': return 'bi-bag-check-fill text-success';
      case 'PROMOTION': return 'bi-percent text-danger';
      default: return 'bi-bell-fill text-secondary';
    }
  }
}
