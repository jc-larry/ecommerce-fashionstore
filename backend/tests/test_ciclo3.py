"""Tests integrales para los 13 Casos de Uso del Ciclo 3 en FashionStore:
- CU25: Conversión de reserva en venta POS con Factura IVA 13%
- CU26: Agendar reserva en probador con bloqueo de stock (HOLD 48h)
- CU27: Bandeja Kanban de preparación de prendas
- CU28: Cancelar reserva y liberar stock apartado
- CU29: Gestión de despachos y asignación de transportistas
- CU30: Tracking timeline en tiempo real por código
- CU31: Zonas y cálculo de tarifas por distancia/anillos
- CU32: Vestidor virtual con recomendador biométrico de tallas
- CU33: Chatbot asistente y estilista IA
- CU34: Búsqueda por voz con NLP y extracción de entidades
- CU35: Reportes gerenciales (Kardex, Top Vendidos, exportación CSV, resumen de voz)
- CU39: Dashboard global analítico con KPIs en tiempo real
- CU40: Notificaciones in-app y confirmaciones por correo
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant, Product
from app.packages.envios_y_logistica.models import DeliveryZone, Shipment
from app.packages.ventas_y_pagos.models import Order
from app.packages.inventario_y_proveedores.merchandise.models import Inventory
from app.packages.notificaciones.models import InAppNotification
from app.packages.reservas_y_citas.models import Reservation
from app.packages.seguridad_y_usuarios.models import User, SessionToken
from app.packages.seguridad_y_usuarios.services import create_access_token

client = TestClient(app)


def get_auth_token():
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@fashionstore.com", "password": "Admin123!"})
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@fashionstore.com").first()
    if not admin:
        admin = db.query(User).filter(User.is_active == True).first()
    token = create_access_token(admin.id)
    session_rec = SessionToken(
        user_id=admin.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        is_revoked=False
    )
    db.add(session_rec)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}


def test_cu26_and_cu27_and_cu28_reservation_lifecycle():
    """[CU26, CU27, CU28] Ciclo de vida de reserva física: creación, kanban y cancelación con liberación."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).filter(Branch.is_active == True).first()
    variant = db.query(ProductVariant).filter(ProductVariant.is_active == True).first()
    assert branch and variant

    b_id = branch.id
    v_id = variant.id
    # Garantizar stock
    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=15, avg_cost=60.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 15)
    db.commit()
    initial_stock = inv.stock_actual
    db.close()

    # 1. [CU26] Agendar reserva de 2 prendas
    res_payload = {
        "branch_id": b_id,
        "items": [{"variant_id": v_id, "quantity": 2, "notes": "Probar en probador 1"}],
        "notes": "Cliente llegará a las 15:00",
    }
    create_res = client.post("/api/v1/reservations", json=res_payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    res_data = create_res.json()
    assert res_data["status"] == "PENDING"
    assert res_data["reservation_code"].startswith("RES-")
    res_id = res_data["id"]

    # Verificar stock apartado (HOLD)
    db = SessionLocal()
    inv_after = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    assert inv_after.stock_actual == initial_stock - 2
    db.close()

    # 2. [CU27] Consultar en bandeja Kanban y avanzar estado PENDING -> PREPARING -> READY
    kanban_res = client.get(f"/api/v1/reservations?branch_id={b_id}", headers=headers)
    assert kanban_res.status_code == 200
    assert any(r["id"] == res_id for r in kanban_res.json())

    patch_prep = client.patch(f"/api/v1/reservations/{res_id}/status", json={"status": "PREPARING"}, headers=headers)
    assert patch_prep.status_code == 200
    assert patch_prep.json()["status"] == "PREPARING"

    patch_ready = client.patch(f"/api/v1/reservations/{res_id}/status", json={"status": "READY"}, headers=headers)
    assert patch_ready.status_code == 200
    assert patch_ready.json()["status"] == "READY"

    # 3. [CU28] Cancelar reserva y validar liberación de stock (HOLD release)
    cancel_res = client.post(f"/api/v1/reservations/{res_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    db = SessionLocal()
    inv_released = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    assert inv_released.stock_actual == initial_stock
    db.close()


def test_cu25_convert_reservation_to_pos_sale():
    """[CU25] Convertir reserva física en venta presencial POS con factura IVA 13%."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).filter(Branch.is_active == True).first()
    variant = db.query(ProductVariant).filter(ProductVariant.is_active == True).first()
    b_id = branch.id
    v_id = variant.id
    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=10, avg_cost=50.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 10)
    db.commit()
    db.close()

    # 1. Crear reserva
    create_res = client.post("/api/v1/reservations", json={
        "branch_id": b_id,
        "items": [{"variant_id": v_id, "quantity": 1, "notes": "Probador vip"}],
    }, headers=headers)
    assert create_res.status_code == 201
    res_id = create_res.json()["id"]

    # 2. El cobro del saldo exige la caja abierta del cajero en esa sucursal
    no_shift = client.post(f"/api/v1/reservations/{res_id}/convert-to-pos", json={"payment_method": "EFECTIVO"}, headers=headers)
    assert no_shift.status_code == 422

    shift = client.get("/api/v1/sales/shifts/current", params={"branch_id": b_id}, headers=headers).json()
    if not shift:
        other = client.get("/api/v1/sales/shifts/current", headers=headers).json()
        if other:
            client.post(f"/api/v1/sales/shifts/{other['id']}/close", json={"closing_amount_declared": 0}, headers=headers)
        shift = client.post("/api/v1/sales/shifts/open", json={"branch_id": b_id, "opening_amount": 100}, headers=headers).json()

    # 3. Convertir a venta POS con el turno de caja
    convert_res = client.post(f"/api/v1/reservations/{res_id}/convert-to-pos", json={
        "cash_shift_id": shift["id"],
        "cash_received": 1000,
        "payment_method": "EFECTIVO",
        "nit_ruc": "87654321",
        "business_name": "CARLOS LOPEZ",
    }, headers=headers)
    assert convert_res.status_code == 200, convert_res.text
    conv_data = convert_res.json()
    assert conv_data["status"] == "COMPLETED"
    assert conv_data["completed_sale_id"] is not None


def test_cu31_delivery_zones_and_rate_calculation():
    """[CU31] Zonas y cálculo dinámico de tarifas de despacho por anillos y kilómetros."""
    headers = get_auth_token()

    # Listar zonas existentes
    zones_res = client.get("/api/v1/logistics/zones")
    assert zones_res.status_code == 200
    zones = zones_res.json()
    assert len(zones) >= 1

    # Calcular tarifa para 4.5 km (Zona 2do a 4to Anillo)
    calc_res = client.post("/api/v1/logistics/calculate-rate", json={"distance_km": 4.5})
    assert calc_res.status_code == 200
    rate_info = calc_res.json()
    assert rate_info["rate"] > 0
    assert rate_info["distance_km"] == 4.5


def test_cu29_and_cu30_shipments_and_tracking_timeline():
    """[CU29, CU30] Despacho de pedido y seguimiento público en tiempo real mediante código."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    b_id = branch.id
    v_id = variant.id

    admin = db.query(User).first()
    order = db.query(Order).first()
    if not order:
        order = Order(
            user_id=admin.id,
            branch_id=b_id,
            channel="ONLINE",
            status="PAGADA",
            subtotal=100.0,
            total_amount=100.0,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
    order_id = order.id
    db.close()

    # 1. [CU29] Crear despacho / shipment
    shipment_payload = {
        "order_id": order_id,
        "carrier_name": "Moto Express SCZ",
        "carrier_phone": "70012345",
        "delivery_address": "Av. San Martín #456, Equipetrol",
        "recipient_name": "María Pérez",
        "recipient_phone": "71122334",
        "shipping_cost": 18.0,
    }
    create_ship = client.post("/api/v1/logistics/shipments", json=shipment_payload, headers=headers)
    assert create_ship.status_code == 201, create_ship.text
    ship_data = create_ship.json()
    tracking_num = ship_data["tracking_number"]
    ship_id = ship_data["id"]
    assert tracking_num.startswith("TRK-")
    assert len(ship_data["events"]) == 1

    # 2. [CU29] Agregar nuevo hito de seguimiento
    event_payload = {
        "status": "DISPATCHED",
        "location": "Av. Banzer km 3",
        "description": "El mensajero ha recogido el paquete y va en camino.",
    }
    event_res = client.post(f"/api/v1/logistics/shipments/{ship_id}/events", json=event_payload, headers=headers)
    assert event_res.status_code == 200
    assert len(event_res.json()["events"]) == 2

    # 3. [CU30] Consulta pública de tracking timeline por código
    track_res = client.get(f"/api/v1/logistics/track/{tracking_num}")
    assert track_res.status_code == 200
    timeline = track_res.json()
    assert timeline["tracking_number"] == tracking_num
    assert len(timeline["events"]) == 2


def test_cu32_virtual_tryon_biometrics():
    """[CU32] Vestidor virtual, sesiones, prendas probadas y recomendación de talla con IA."""
    db = SessionLocal()
    prod = db.query(Product).first()
    variant = db.query(ProductVariant).filter(ProductVariant.product_id == prod.id).first()
    db.close()
    assert prod

    # 1. Iniciar sesión de vestidor
    res_sess = client.post("/api/v1/analytics/tryon/sessions", json={"channel": "WEB"})
    assert res_sess.status_code == 200, res_sess.text
    session_data = res_sess.json()
    token = session_data["session_token"]
    assert token

    # 2. Registrar prenda probada en la sesión
    res_item = client.post("/api/v1/analytics/tryon/items", json={
        "session_token": token,
        "product_id": prod.id,
        "variant_id": variant.id if variant else None,
        "tested_size": "M",
        "fit_feedback": "Ajuste excelente",
    })
    assert res_item.status_code == 200, res_item.text
    assert res_item.json()["product_name"] == prod.name

    # 3. Consultar historial de prendas probadas
    res_hist = client.get(f"/api/v1/analytics/tryon/sessions/{token}/items")
    assert res_hist.status_code == 200
    items_list = res_hist.json()
    assert len(items_list) >= 1
    assert items_list[0]["product_id"] == prod.id

    # 4. Simulación biométrica y ajuste
    res = client.post("/api/v1/analytics/tryon/simulate", json={
        "session_token": token,
        "product_id": prod.id,
        "user_height_cm": 172.0,
        "user_weight_kg": 68.0,
        "chest_cm": 96.0,
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["recommended_size"] == "M"
    assert data["confidence_score"] > 0.8
    assert "fit_assessment" in data

    # 5. Generación de síntesis VTON con IA (IDM-VTON)
    res_vton = client.post("/api/v1/analytics/tryon/generate-vton", json={
        "session_token": token,
        "product_id": prod.id,
        "person_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "category": "tops",
        "model_choice": "IDM-VTON",
    })
    assert res_vton.status_code == 200, res_vton.text
    vton_data = res_vton.json()
    assert vton_data["status"] == "COMPLETED"
    assert "result_image_url" in vton_data


def test_cu33_chatbot_assistant():
    """[CU33] Chatbot asistente inteligente y estilista de moda."""
    # Saludo
    res_greet = client.post("/api/v1/analytics/chatbot/message", json={"message": "Hola, necesito ayuda"})
    assert res_greet.status_code == 200
    assert "Asistente Virtual" in res_greet.json()["reply"]

    # Consulta de sucursales
    res_stores = client.post("/api/v1/analytics/chatbot/message", json={"message": "¿Dónde quedan sus sucursales y sus horarios?"})
    assert res_stores.status_code == 200
    assert res_stores.json()["detected_intent"] == "STORE_INFO"


def test_cu34_voice_search_nlp():
    """[CU34] Búsqueda por voz con extracción de entidades semánticas (NLP)."""
    res = client.post("/api/v1/analytics/search/voice-nlp", json={
        "query_text": "Quiero un vestido rojo para mujer de menos de 300 bolivianos"
    })
    assert res.status_code == 200
    data = res.json()
    entities = data["extracted_entities"]
    assert entities["color"] == "rojo"
    assert entities["garment"] == "vestido"
    assert entities["gender"] == "Damas"
    assert entities["max_price"] == 300.0


def test_cu35_manager_reports_and_csv():
    """[CU35] Reportes gerenciales: Kardex físico-valorado, top vendidos y exportación."""
    headers = get_auth_token()

    # Kardex
    kardex_res = client.get("/api/v1/analytics/reports/kardex", headers=headers)
    assert kardex_res.status_code == 200
    assert isinstance(kardex_res.json(), list)

    # Exportación CSV
    csv_res = client.get("/api/v1/analytics/reports/kardex/export-csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert b"Tipo Movimiento" in csv_res.content

    # Top vendidos
    top_res = client.get("/api/v1/analytics/reports/top-selling", headers=headers)
    assert top_res.status_code == 200
    assert isinstance(top_res.json(), list)

    # Resumen de voz
    voice_res = client.get("/api/v1/analytics/reports/executive-summary", headers=headers)
    assert voice_res.status_code == 200
    assert "summary_text" in voice_res.json()


def test_cu39_analytics_dashboard():
    """[CU39] Dashboard global analítico con KPIs consolidados."""
    headers = get_auth_token()
    res = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert res.status_code == 200
    dash = res.json()
    assert "total_sales_revenue" in dash
    assert "total_orders_count" in dash
    assert "sales_by_channel" in dash
    assert "daily_sales_last_7_days" in dash


def test_cu40_in_app_notifications():
    """[CU40] Notificaciones in-app y conteo de no leídas."""
    headers = get_auth_token()
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@fashionstore.com").first()
    if not admin:
        admin = db.query(User).first()

    # Crear notificación de prueba
    notif = InAppNotification(
        user_id=admin.id,
        title="¡Tu reserva está lista!",
        message="Las prendas de tu reserva RES-TEST están preparadas en el probador 2.",
        notification_type="RESERVATION",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    notif_id = notif.id
    db.close()

    # 1. Consultar no leídas
    count_res = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_res.status_code == 200
    assert count_res.json()["unread_count"] >= 1

    # 2. Listar notificaciones
    my_notifs = client.get("/api/v1/notifications/my", headers=headers)
    assert my_notifs.status_code == 200
    assert any(n["id"] == notif_id for n in my_notifs.json()["notifications"])

    # 3. Marcar como leída
    read_res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True
