import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.packages.seguridad_y_usuarios.models import User, SessionToken
from app.packages.seguridad_y_usuarios.services import create_access_token

client = TestClient(app)

def get_admin_token():
    # Intento 1: Login directo
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@fashionstore.com", "password": "Admin123!"})
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # Intento 2: Inserción directa en session_tokens para el admin
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@fashionstore.com").first()
    if not admin:
        admin = db.query(User).filter(User.is_active == True).first()
    token = create_access_token({"sub": str(admin.id), "roles": ["SUPERADMIN"]})
    session_rec = SessionToken(
        user_id=admin.id,
        token=token,
        ip_address="127.0.0.1",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        is_revoked=False
    )
    db.add(session_rec)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}

def test_coupon_crud_and_validation():
    headers = get_admin_token()
    now = datetime.now(timezone.utc)
    valid_from = (now - timedelta(days=1)).isoformat()
    valid_until = (now + timedelta(days=30)).isoformat()

    code = f"PROMO_{uuid.uuid4().hex[:6].upper()}"
    coupon_data = {
        "code": code,
        "discount_type": "PORCENTAJE",
        "discount_value": 20.0,
        "min_purchase_amount": 150.0,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "max_uses": 50,
        "is_active": True
    }

    # 1. Crear Cupón (Admin)
    res = client.post("/api/v1/catalog/coupons", json=coupon_data, headers=headers)
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["code"] == code
    assert created["discount_value"] == 20.0

    # 2. Validar cupón con compra de Bs. 200 (cumple el mínimo de Bs. 150)
    # Descuento del 20% sobre 200 = 40. Nuevo total = 160.
    val_res = client.post("/api/v1/catalog/coupons/validate", json={
        "code": code,
        "cart_total": 200.0
    })
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["valid"] is True
    assert val_data["discount_amount"] == 40.0
    assert val_data["new_total"] == 160.0

    # 3. Validar cupón con compra de Bs. 100 (inferior al mínimo de Bs. 150)
    val_fail = client.post("/api/v1/catalog/coupons/validate", json={
        "code": code,
        "cart_total": 100.0
    })
    assert val_fail.status_code == 200
    val_fail_data = val_fail.json()
    assert val_fail_data["valid"] is False
    assert "mínima" in val_fail_data["message"]

    # 4. Validar cupón inexistente
    val_no = client.post("/api/v1/catalog/coupons/validate", json={
        "code": "NO_EXISTE_999",
        "cart_total": 300.0
    })
    assert val_no.status_code == 200
    assert val_no.json()["valid"] is False

def test_seasonal_promotion_flow():
    headers = get_admin_token()
    today = datetime.now().date()
    start = today.isoformat()
    end = (today + timedelta(days=15)).isoformat()

    promo_name = f"CyberSale {uuid.uuid4().hex[:4]}"
    promo_data = {
        "name": promo_name,
        "description": "Descuento especial de fin de temporada",
        "discount_percent": 25,
        "start_date": start,
        "end_date": end,
        "is_active": True
    }

    # 1. Crear promoción de temporada (Admin)
    res = client.post("/api/v1/catalog/promotions", json=promo_data, headers=headers)
    assert res.status_code == 201, res.text
    created = res.json()
    assert created["name"] == promo_name
    assert created["discount_percent"] == 25

    # 2. Listar promociones
    list_res = client.get("/api/v1/catalog/promotions")
    assert list_res.status_code == 200
    promos = list_res.json()
    assert any(p["id"] == created["id"] for p in promos)
