import { Component, OnInit } from '@angular/core';
import { CatalogoService, ReviewModerationItem } from '../catalogo.service';

@Component({
  selector: 'app-reviews-moderation',
  templateUrl: './reviews-moderation.component.html',
  styleUrls: ['./reviews-moderation.component.css']
})
export class ReviewsModerationComponent implements OnInit {
  reviews: ReviewModerationItem[] = [];
  loading = false;
  statusFilter = '';
  errorMessage = '';
  successMessage = '';

  constructor(private catalogoService: CatalogoService) {}

  ngOnInit(): void {
    this.loadReviews();
  }

  loadReviews(): void {
    this.loading = true;
    this.errorMessage = '';
    this.catalogoService.getAdminReviews(this.statusFilter || undefined).subscribe({
      next: (res) => {
        this.reviews = res;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al cargar las reseñas para moderación.';
        this.loading = false;
      }
    });
  }

  onFilterChange(status: string): void {
    this.statusFilter = status;
    this.loadReviews();
  }

  moderate(review: ReviewModerationItem, newStatus: 'APPROVED' | 'REJECTED'): void {
    if (!confirm(`¿Deseas cambiar el estado de esta reseña a ${newStatus}?`)) return;

    this.catalogoService.moderateReview(review.id, newStatus).subscribe({
      next: (updated) => {
        review.status = updated.status;
        this.successMessage = `Reseña de ${review.author_name} marcada como ${updated.status}.`;
        setTimeout(() => this.successMessage = '', 3500);
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Error al actualizar moderación.';
        setTimeout(() => this.errorMessage = '', 4000);
      }
    });
  }

  getStarsArray(rating: number): number[] {
    return Array(rating).fill(0);
  }
}
