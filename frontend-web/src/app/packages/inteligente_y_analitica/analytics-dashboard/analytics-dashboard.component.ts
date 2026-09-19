import { Component, OnInit } from '@angular/core';
import { AnaliticaService, DashboardMetrics } from '../analitica.service';

@Component({
  selector: 'app-analytics-dashboard',
  templateUrl: './analytics-dashboard.component.html',
  styleUrls: ['./analytics-dashboard.component.css']
})
export class AnalyticsDashboardComponent implements OnInit {
  metrics: DashboardMetrics | null = null;
  loading: boolean = false;
  errorMsg: string = '';

  constructor(private analiticaService: AnaliticaService) {}

  ngOnInit(): void {
    this.loadMetrics();
  }

  loadMetrics(): void {
    this.loading = true;
    this.analiticaService.getDashboardMetrics().subscribe({
      next: (data) => {
        this.metrics = data;
        this.loading = false;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'Error al cargar métricas del dashboard.';
        this.loading = false;
      }
    });
  }

  getMaxDailyRevenue(): number {
    if (!this.metrics || !this.metrics.daily_sales_last_7_days) return 100;
    const max = Math.max(...this.metrics.daily_sales_last_7_days.map(d => d.revenue));
    return max > 0 ? max : 100;
  }

  getChannelOnlinePercent(): number {
    if (!this.metrics) return 50;
    const online = this.metrics.sales_by_channel['ONLINE'] || 0;
    const pos = this.metrics.sales_by_channel['POS'] || 0;
    const total = online + pos;
    return total > 0 ? Math.round((online / total) * 100) : 0;
  }

  getChannelPosPercent(): number {
    if (!this.metrics) return 50;
    const online = this.metrics.sales_by_channel['ONLINE'] || 0;
    const pos = this.metrics.sales_by_channel['POS'] || 0;
    const total = online + pos;
    return total > 0 ? Math.round((pos / total) * 100) : 0;
  }
}
