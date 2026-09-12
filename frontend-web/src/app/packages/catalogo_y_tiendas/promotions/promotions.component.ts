import { Component, OnInit } from '@angular/core';
import { CatalogoService, Coupon, SeasonalPromotion, Category } from '../catalogo.service';

@Component({
  selector: 'app-promotions',
  templateUrl: './promotions.component.html',
  styleUrls: ['./promotions.component.css'],
})
export class PromotionsComponent implements OnInit {
  activeTab: 'coupons' | 'promotions' = 'coupons';
  loading = false;
  successMsg = '';
  errorMsg = '';

  // Cupones
  coupons: Coupon[] = [];
  showCouponModal = false;
  newCoupon: any = {
    code: '',
    discount_type: 'PORCENTAJE',
    discount_value: 10,
    min_purchase_amount: 0,
    valid_from: '',
    valid_until: '',
    max_uses: 100,
    is_active: true,
  };

  // Campañas de Temporada
  promotions: SeasonalPromotion[] = [];
  categories: Category[] = [];
  showPromoModal = false;
  newPromo: any = {
    name: '',
    description: '',
    discount_percent: 15,
    category_id: null,
    start_date: '',
    end_date: '',
    is_active: true,
  };

  constructor(private catalogo: CatalogoService) {}

  ngOnInit(): void {
    this.loadData();
    this.catalogo.getCategories().subscribe({
      next: (cats) => (this.categories = cats || []),
    });
  }

  loadData(): void {
    this.loading = true;
    this.catalogo.getCoupons().subscribe({
      next: (cps) => {
        this.coupons = cps || [];
        this.loading = false;
      },
      error: () => (this.loading = false),
    });

    this.catalogo.getPromotions().subscribe({
      next: (pms) => (this.promotions = pms || []),
    });
  }

  // --- Manejo de Cupones ---
  openCouponModal(): void {
    const today = new Date();
    const nextMonth = new Date();
    nextMonth.setDate(today.getDate() + 30);

    this.newCoupon = {
      code: '',
      discount_type: 'PORCENTAJE',
      discount_value: 15,
      min_purchase_amount: 50,
      valid_from: today.toISOString().slice(0, 16),
      valid_until: nextMonth.toISOString().slice(0, 16),
      max_uses: 100,
      is_active: true,
    };
    this.showCouponModal = true;
    this.errorMsg = '';
  }

  saveCoupon(): void {
    if (!this.newCoupon.code.trim()) {
      this.errorMsg = 'El código del cupón es obligatorio.';
      return;
    }
    this.loading = true;
    this.catalogo.createCoupon(this.newCoupon).subscribe({
      next: () => {
        this.showCouponModal = false;
        this.successMsg = 'Cupón creado exitosamente.';
        setTimeout(() => (this.successMsg = ''), 3000);
        this.loadData();
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err.error?.detail || 'Error al guardar el cupón.';
      },
    });
  }

  toggleCouponActive(c: Coupon): void {
    this.catalogo.updateCoupon(c.id, { is_active: !c.is_active }).subscribe({
      next: (upd) => (c.is_active = upd.is_active),
      error: () => this.loadData(),
    });
  }

  deleteCoupon(id: number): void {
    if (!confirm('¿Seguro que deseas eliminar este cupón?')) return;
    this.catalogo.deleteCoupon(id).subscribe({
      next: () => {
        this.coupons = this.coupons.filter((c) => c.id !== id);
        this.successMsg = 'Cupón eliminado.';
        setTimeout(() => (this.successMsg = ''), 3000);
      },
    });
  }

  // --- Manejo de Campañas ---
  openPromoModal(): void {
    const today = new Date().toISOString().slice(0, 10);
    const nextWeek = new Date();
    nextWeek.setDate(new Date().getDate() + 14);

    this.newPromo = {
      name: '',
      description: '',
      discount_percent: 20,
      category_id: null,
      start_date: today,
      end_date: nextWeek.toISOString().slice(0, 10),
      is_active: true,
    };
    this.showPromoModal = true;
    this.errorMsg = '';
  }

  savePromotion(): void {
    if (!this.newPromo.name.trim()) {
      this.errorMsg = 'El nombre de la campaña es obligatorio.';
      return;
    }
    this.loading = true;
    this.catalogo.createPromotion(this.newPromo).subscribe({
      next: () => {
        this.showPromoModal = false;
        this.successMsg = 'Campaña de temporada creada exitosamente.';
        setTimeout(() => (this.successMsg = ''), 3000);
        this.loadData();
      },
      error: (err) => {
        this.loading = false;
        this.errorMsg = err.error?.detail || 'Error al guardar la campaña.';
      },
    });
  }

  deletePromotion(id: number): void {
    if (!confirm('¿Seguro que deseas eliminar esta campaña?')) return;
    this.catalogo.deletePromotion(id).subscribe({
      next: () => {
        this.promotions = this.promotions.filter((p) => p.id !== id);
        this.successMsg = 'Campaña eliminada.';
        setTimeout(() => (this.successMsg = ''), 3000);
      },
    });
  }

  isExpired(until: string): boolean {
    return new Date(until) < new Date();
  }
}
