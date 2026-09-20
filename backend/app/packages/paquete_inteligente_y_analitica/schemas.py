"""Schemas Pydantic para el paquete Inteligente y Analítica."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# CU32: SEGMENTACIÓN Y REMOCIÓN DE FONDO CON IA
# -------------------------------------------------------------------

class RemoveBackgroundRequest(BaseModel):
    """Solicitud de remoción de fondo con IA (rembg u2net)."""
    image_base64: str = Field(..., description="Imagen en base64 data URI (data:image/...;base64,...)")


class RemoveBackgroundResponse(BaseModel):
    """Resultado de la segmentación corporal y remoción de fondo."""
    processed_image_url: str = Field(..., description="Imagen con fondo blanco puro en base64 data URI")
    processing_time_sec: float = 0.0
    model_used: str = "rembg (mask)"
    mask_confidence: float = Field(0.0, ge=0.0, le=1.0)
    mask_reliable: bool = False
    mask_source: str = "none"
    mask_bbox: Optional[List[int]] = None
    pose_confidence: float = Field(0.0, ge=0.0, le=1.0)
    pose_valid: bool = False
    pose_source: str = "none"
    pose_landmarks: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------------
# CU32: SESIONES Y REGISTRO DE PRENDAS DEL VESTIDOR VIRTUAL
# -------------------------------------------------------------------

class TryonSessionCreate(BaseModel):
    channel: str = Field("WEB", description="Canal de origen: 'WEB' | 'MOBILE'")


class TryonSessionResponse(BaseModel):
    id: int
    session_token: str
    channel: str
    status: str
    started_at: datetime
    items_count: int = 0


class TryonItemCreate(BaseModel):
    session_token: str
    product_id: int
    variant_id: Optional[int] = None
    tested_size: Optional[str] = None
    fit_feedback: Optional[str] = None


class TryonItemResponse(BaseModel):
    id: int
    session_id: int
    product_id: int
    product_name: str
    variant_id: Optional[int] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    image_url: Optional[str] = None
    tested_size: Optional[str] = None
    fit_feedback: Optional[str] = None
    tested_at: datetime


class VTONGenerateRequest(BaseModel):
    """Solicitud de inferencia con modelo generativo de difusión (IDM-VTON / Fashn.ai)."""
    session_token: Optional[str] = None
    product_id: int
    variant_id: Optional[int] = None
    person_image: str = Field(..., description="URL o Base64 de la foto de la persona / silueta")
    garment_image: Optional[str] = Field(None, description="URL o Base64 de la prenda aislada")
    category: str = Field("tops", description="'tops' | 'bottoms' | 'one-pieces'")
    model_choice: str = Field("IDM-VTON", description="'IDM-VTON' | 'FASHN_AI'")
    recommended_size: Optional[str] = Field("M", description="Talla biométrica recomendada (XS, S, M, L, XL, XXL)")


class VTONGenerateResponse(BaseModel):
    """Resultado fotorrealista de la prueba textil con IA generativa."""
    capture_id: int
    product_id: int
    product_name: str
    result_image_url: str
    original_photo_url: Optional[str] = None
    generation_model: str
    processing_time_sec: float
    status: str
    style_advice: str
    mask_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    mask_reliable: Optional[bool] = None
    mask_source: Optional[str] = None
    pose_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    pose_valid: Optional[bool] = None
    pose_source: Optional[str] = None
    pose_landmarks: Optional[Dict[str, Any]] = None
    # 'anatomical-warp' = la prenda se amoldo al torso detectado;
    # 'fallback-paste'  = no hubo pose utilizable y se coloco de forma conservadora.
    fit_mode: Optional[str] = None


class TryonCaptureCreate(BaseModel):
    session_token: Optional[str] = None
    product_id: int
    variant_id: Optional[int] = None
    photo_url: str
    original_photo_url: Optional[str] = None
    generation_model: str = "IDM-VTON"
    recommended_size: Optional[str] = None
    measurements_json: Optional[str] = None


class TryonCaptureResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    variant_id: Optional[int] = None
    photo_url: str
    original_photo_url: Optional[str] = None
    generation_model: str
    recommended_size: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime


class VirtualTryonRequest(BaseModel):
    """Solicitud de simulación biométrica de tallas y ajuste corporal."""
    session_token: Optional[str] = None
    product_id: int
    variant_id: Optional[int] = None
    photo_url: Optional[str] = None
    photo_base64: Optional[str] = None
    user_height_cm: Optional[float] = Field(None, ge=100, le=250)
    user_weight_kg: Optional[float] = Field(None, ge=30, le=250)
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None


class VirtualTryonResponse(BaseModel):
    """Diagnóstico anatómico y recomendación de patronaje."""
    id: int
    product_id: int
    product_name: str
    recommended_size: str
    fit_scale_factor: Optional[float] = 1.0
    confidence_score: float
    simulation_image_url: str
    fit_assessment: str
    style_advice: str
    body_shape: Optional[str] = "Reloj de Arena"
    chest_fit: Optional[str] = "Ajuste Óptimo"
    waist_fit: Optional[str] = "Ajuste Cómodo"
    hip_fit: Optional[str] = "Caída Natural"
    user_photo_processed: bool = False
    # Landmarks anatómicos para posicionamiento preciso en el vestidor
    garment_landmarks: Optional[Dict[str, Any]] = None
    body_landmarks: Optional[Dict[str, Any]] = None
    created_at: datetime


# -------------------------------------------------------------------
# CU33: CHATBOT ASISTENTE & ESTILISTA IA
# -------------------------------------------------------------------

class ChatbotMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_token: Optional[str] = None
    current_page: Optional[str] = None


class ChatbotMessageResponse(BaseModel):
    reply: str
    session_token: str
    detected_intent: str
    suggested_products: List[Dict[str, Any]] = []
    suggested_actions: List[str] = []


# -------------------------------------------------------------------
# CU34: BÚSQUEDA POR VOZ Y PROCESAMIENTO NLP
# -------------------------------------------------------------------

class VoiceSearchNLPRequest(BaseModel):
    query_text: str = Field(..., description="Texto transcrito por reconocimiento de voz del cliente")


class VoiceSearchNLPResponse(BaseModel):
    original_query: str
    extracted_entities: Dict[str, Any]
    matched_products_count: int
    products: List[Dict[str, Any]]


# -------------------------------------------------------------------
# CU35 & CU39: REPORTES GERENCIALES Y DASHBOARD ANALÍTICO
# -------------------------------------------------------------------

class ManagerReportTopSellingItem(BaseModel):
    product_id: int
    product_name: str
    category_name: str
    total_units_sold: int
    total_revenue: float
    image_url: Optional[str] = None


class ManagerReportKardexItem(BaseModel):
    id: int
    date: datetime
    branch_name: str
    product_name: str
    sku: str
    movement_type: str
    quantity: int
    unit_cost: float
    total_cost: float
    reference_id: Optional[str] = None


class AnalyticsDashboardResponse(BaseModel):
    total_sales_revenue: float
    total_orders_count: int
    average_ticket: float
    low_stock_items_count: int
    sales_by_channel: Dict[str, float]
    sales_by_category: List[Dict[str, Any]]
    sales_by_branch: List[Dict[str, Any]]
    daily_sales_last_7_days: List[Dict[str, Any]]


class SalesTimelinePoint(BaseModel):
    period: str
    date_label: str
    units_sold: int
    revenue: float


class VariantSalesStock(BaseModel):
    variant_id: int
    sku: str
    size: str
    color: str
    color_hex: str
    current_stock: int
    units_sold: int


class BranchStockItem(BaseModel):
    branch_id: int
    branch_name: str
    stock: int


class ProductSalesTrendResponse(BaseModel):
    product_id: int
    product_name: str
    category_name: str
    base_price: float
    image_url: Optional[str] = None
    total_units_sold: int
    total_revenue: float
    current_total_stock: int
    weekly_velocity: float
    days_of_stock_left: float
    reorder_decision: str
    reorder_label: str
    reorder_badge_class: str
    reorder_recommendation: str
    suggested_reorder_units: int
    timeline: List[SalesTimelinePoint]
    variants_breakdown: List[VariantSalesStock]
    branches_stock: List[BranchStockItem]
