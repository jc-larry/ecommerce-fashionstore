import { Component, OnInit } from '@angular/core';
import { VentasService, OrderResponse, CustomerReturn } from '../ventas.service';

@Component({
  selector: 'app-customer-orders',
  templateUrl: './customer-orders.component.html',
  styleUrls: ['./customer-orders.component.css']
})
export class CustomerOrdersComponent implements OnInit {
  orders: OrderResponse[] = [];
  returns: CustomerReturn[] = [];
  activeTab: 'PEDIDOS' | 'DEVOLUCIONES' = 'PEDIDOS';
  selectedOrder: OrderResponse | null = null;
  loading: boolean = true;
  errorMessage: string | null = null;

  constructor(private ventasService: VentasService) {}

  ngOnInit(): void {
    this.loadOrders();
    this.loadReturns();
  }

  /** [CU22] Devoluciones y cambios que la sucursal registró sobre mis compras. */
  loadReturns(): void {
    this.ventasService.getMyReturns().subscribe({
      next: (data) => (this.returns = data),
      error: () => (this.returns = []),
    });
  }

  loadOrders(): void {
    this.loading = true;
    this.ventasService.getMyOrders().subscribe({
      next: (data) => {
        this.orders = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Error al cargar el historial de compras.';
        this.loading = false;
      }
    });
  }

  viewDetails(order: OrderResponse): void {
    this.selectedOrder = order;
  }
}
