import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.packages.seguridad_y_usuarios.models import User, SessionToken
from app.packages.catalogo_y_tiendas.models import Product, ProductReview, Wishlist
from app.packages.seguridad_y_usuarios.services import create_access_token

client = TestClient(app)

def get_admin_token():
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@fashionstore.com", "password": "Admin123!"})
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
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


def test_review_submission_and_moderation():
    """Prueba flujo de publicación de reseña y moderación administrativa (CU14+)"""
    headers = get_admin_token()
    db = SessionLocal()
    prod = db.query(Product).first()
    assert prod is not None, "Debe existir al menos un producto en la base de datos"
    prod_id = prod.id
    db.close()

    # 1. Enviar reseña (como usuario autenticado)
    review_data = {
        "rating": 5,
        "comment": "Prenda excelente, tela de primera calidad y ajuste perfecto."
    }
    res = client.post(f"/api/v1/catalog/products/{prod_id}/reviews", json=review_data, headers=headers)
    assert res.status_code in [200, 201], res.text
    review_resp = res.json()
    assert review_resp["rating"] == 5
    review_id = review_resp["id"]

    # 2. Listado administrativo de moderación
    res_mod = client.get("/api/v1/catalog/admin/reviews", headers=headers)
    assert res_mod.status_code == 200
    mod_items = res_mod.json()
    assert any(m["id"] == review_id for m in mod_items)

    # 3. Moderar la reseña (Rechazar / Ocultar)
    res_reject = client.put(
        f"/api/v1/catalog/admin/reviews/{review_id}/moderate",
        json={"status": "REJECTED"},
        headers=headers
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["status"] == "REJECTED"

    # 4. Verificar que como anónimo no aparece una reseña rechazada
    res_anon = client.get(f"/api/v1/catalog/products/{prod_id}/reviews")
    assert res_anon.status_code == 200
    anon_items = res_anon.json()["items"]
    assert not any(i["id"] == review_id for i in anon_items)

    # 5. Volver a Aprobar la reseña
    res_approve = client.put(
        f"/api/v1/catalog/admin/reviews/{review_id}/moderate",
        json={"status": "APPROVED"},
        headers=headers
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "APPROVED"


def test_multi_wishlists_and_sharing():
    """Prueba creación de múltiples listas de deseos, adición de prendas y enlace compartido (CU14+)"""
    headers = get_admin_token()
    db = SessionLocal()
    prod = db.query(Product).first()
    assert prod is not None
    prod_id = prod.id
    db.close()

    # 1. Obtener wishlists del usuario
    res = client.get("/api/v1/catalog/wishlists", headers=headers)
    assert res.status_code == 200
    lists = res.json()
    assert len(lists) >= 1  # Lista por defecto creada si no había

    # 2. Crear nueva lista de deseos personalizada
    new_name = f"Look Verano {uuid.uuid4().hex[:4]}"
    res_create = client.post(
        "/api/v1/catalog/wishlists",
        json={"name": new_name, "is_public": True},
        headers=headers
    )
    assert res_create.status_code == 201
    wl = res_create.json()
    wl_id = wl["id"]
    share_token = wl["share_token"]
    assert wl["name"] == new_name
    assert wl["is_public"] is True

    # 3. Agregar prenda a la nueva lista
    res_add = client.post(f"/api/v1/catalog/wishlists/{wl_id}/items/{prod_id}", headers=headers)
    assert res_add.status_code == 201

    # 4. Ver detalle de la lista
    res_detail = client.get(f"/api/v1/catalog/wishlists/{wl_id}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert any(p["id"] == prod_id for p in detail["products"])

    # 5. Consultar vía enlace compartido (Público, sin headers)
    res_shared = client.get(f"/api/v1/catalog/wishlists/shared/{share_token}")
    assert res_shared.status_code == 200
    shared_data = res_shared.json()
    assert shared_data["name"] == new_name
    assert len(shared_data["products"]) >= 1

    # 6. Eliminar prenda de la lista
    res_del_item = client.delete(f"/api/v1/catalog/wishlists/{wl_id}/items/{prod_id}", headers=headers)
    assert res_del_item.status_code == 200

    # 7. Eliminar lista de deseos
    res_del_wl = client.delete(f"/api/v1/catalog/wishlists/{wl_id}", headers=headers)
    assert res_del_wl.status_code == 204
