import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface VirtualTryonResult {
  id: number;
  product_id: number;
  product_name: string;
  recommended_size: string;
  fit_scale_factor?: number;
  confidence_score: number;
  simulation_image_url: string;
  fit_assessment: string;
  style_advice: string;
  body_shape?: string;
  chest_fit?: string;
  waist_fit?: string;
  hip_fit?: string;
  user_photo_processed?: boolean;
  garment_landmarks?: { [key: string]: any };
  body_landmarks?: { [key: string]: any };
  created_at: string;
}

export interface RemoveBackgroundResult {
  processed_image_url: string;
  processing_time_sec: number;
  model_used: string;
  mask_confidence: number;
  mask_reliable: boolean;
  mask_source: string;
  mask_bbox?: number[];
  pose_confidence: number;
  pose_valid: boolean;
  pose_source: string;
  pose_landmarks?: { [key: string]: any };
}

export interface TryonSession {
  id: number;
  session_token: string;
  channel: string;
  status: string;
  started_at: string;
  items_count: number;
}

export interface TryonItem {
  id: number;
  session_id: number;
  product_id: number;
  product_name: string;
  variant_id?: number;
  color_name?: string;
  color_hex?: string;
  image_url?: string;
  tested_size?: string;
  fit_feedback?: string;
  tested_at: string;
}

export interface VTONGenerateResult {
  capture_id: number;
  product_id: number;
  product_name: string;
  result_image_url: string;
  original_photo_url?: string;
  generation_model: string;
  processing_time_sec: number;
  status: string;
  style_advice: string;
  mask_confidence?: number;
  mask_reliable?: boolean;
  mask_source?: string;
  pose_confidence?: number;
  pose_valid?: boolean;
  pose_source?: string;
  pose_landmarks?: { [key: string]: any };
}

export interface ChatbotResponse {
  reply: string;
  session_token: string;
  detected_intent: string;
  suggested_products: any[];
  suggested_actions: string[];
}

export interface VoiceNLPResult {
  original_query: string;
  extracted_entities: {
    color?: string;
    garment?: string;
    gender?: string;
    max_price?: number;
  };
  matched_products_count: number;
  products: any[];
}

export interface KardexItem {
  id: number;
  date: string;
  branch_name: string;
  product_name: string;
  sku: string;
  movement_type: string;
  quantity: number;
  unit_cost: number;
  total_cost: number;
  reference_id?: string;
}

export interface TopSellingItem {
  product_id: number;
  product_name: string;
  category_name: string;
  total_units_sold: number;
  total_revenue: number;
  image_url?: string;
}

export interface DashboardMetrics {
  total_sales_revenue: number;
  total_orders_count: number;
  average_ticket: number;
  low_stock_items_count: number;
  sales_by_channel: { [key: string]: number };
  sales_by_category: { name: string; value: number }[];
  sales_by_branch: { name: string; value: number }[];
  daily_sales_last_7_days: { date: string; revenue: number }[];
}

@Injectable({
  providedIn: 'root'
})
export class AnaliticaService {
  private baseUrl = `${environment.apiUrl}/analytics`;

  constructor(private http: HttpClient) {}

  // ===================================================================
  // CU32: VESTIDOR VIRTUAL (SESIONES, PRENDAS PROBADAS, IA Y BIOMETRÍA)
  // ===================================================================

  startTryonSession(channel: string = 'WEB'): Observable<TryonSession> {
    return this.http.post<TryonSession>(`${this.baseUrl}/tryon/sessions`, { channel });
  }

  removeBackground(imageBase64: string): Observable<RemoveBackgroundResult> {
    return this.http.post<RemoveBackgroundResult>(`${this.baseUrl}/tryon/remove-background`, {
      image_base64: imageBase64
    });
  }

  logTestedItem(data: {
    session_token: string;
    product_id: number;
    variant_id?: number;
    tested_size?: string;
    fit_feedback?: string;
  }): Observable<TryonItem> {
    return this.http.post<TryonItem>(`${this.baseUrl}/tryon/items`, data);
  }

  getSessionTestedItems(sessionToken: string): Observable<TryonItem[]> {
    return this.http.get<TryonItem[]>(`${this.baseUrl}/tryon/sessions/${sessionToken}/items`);
  }

  simulateTryon(data: {
    session_token?: string;
    product_id: number;
    variant_id?: number;
    photo_url?: string;
    photo_base64?: string;
    user_height_cm?: number;
    user_weight_kg?: number;
    chest_cm?: number;
    waist_cm?: number;
    hip_cm?: number;
  }): Observable<VirtualTryonResult> {
    return this.http.post<VirtualTryonResult>(`${this.baseUrl}/tryon/simulate`, data);
  }

  generateVTON(data: {
    session_token?: string;
    product_id: number;
    variant_id?: number;
    person_image: string;
    garment_image?: string;
    category?: string;
    model_choice?: string;
    recommended_size?: string;
  }): Observable<VTONGenerateResult> {
    return this.http.post<VTONGenerateResult>(`${this.baseUrl}/tryon/generate-vton`, data);
  }

  saveCapture(data: {
    session_token?: string;
    product_id: number;
    variant_id?: number;
    photo_url: string;
    original_photo_url?: string;
    generation_model?: string;
    recommended_size?: string;
    measurements_json?: string;
  }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/tryon/captures`, data);
  }

  // ===================================================================
  // CU33: CHATBOT ASISTENTE & ESTILISTA IA
  // ===================================================================
  sendChatMessage(message: string, sessionToken?: string): Observable<ChatbotResponse> {
    return this.http.post<ChatbotResponse>(`${this.baseUrl}/chatbot/message`, {
      message,
      session_token: sessionToken
    });
  }

  // ===================================================================
  // CU34: VOICE SEARCH NLP
  // ===================================================================
  searchByVoiceNLP(queryText: string): Observable<VoiceNLPResult> {
    return this.http.post<VoiceNLPResult>(`${this.baseUrl}/search/voice-nlp`, {
      query_text: queryText
    });
  }

  // ===================================================================
  // CU35: REPORTES GERENCIALES Y KARDEX
  // ===================================================================
  getKardex(branchId?: number): Observable<KardexItem[]> {
    let params = new HttpParams();
    if (branchId) params = params.set('branch_id', branchId.toString());
    return this.http.get<KardexItem[]>(`${this.baseUrl}/reports/kardex`, { params });
  }

  exportKardexCsvUrl(branchId?: number): string {
    return `${this.baseUrl}/reports/kardex/export-csv${branchId ? '?branch_id=' + branchId : ''}`;
  }

  getTopSelling(limit: number = 10): Observable<TopSellingItem[]> {
    return this.http.get<TopSellingItem[]>(`${this.baseUrl}/reports/top-selling?limit=${limit}`);
  }

  getExecutiveSummaryVoice(): Observable<{
    summary_text: string;
    total_revenue: number;
    total_orders: number;
    active_reservations: number;
    pending_shipments: number;
  }> {
    return this.http.get<any>(`${this.baseUrl}/reports/executive-summary`);
  }

  // ===================================================================
  // CU39: DASHBOARD
  // ===================================================================
  getDashboardMetrics(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>(`${this.baseUrl}/dashboard`);
  }
}
