"""[CU40] Los eventos del negocio generan notificaciones in-app en el buzón del usuario."""
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant
from app.packages.inventario_y_proveedores.merchandise.models import Inventory
from tests.test_cu17_cu24 import get_auth_token

client = TestClient(app)


def _preparar_stock(minimo=20):
    db = SessionLocal()
    branch = db.query(Branch).filter(Branch.is_active == True).first()
    variant = db.query(ProductVariant).filter(ProductVariant.is_active == True).first()
    b_id, v_id = branch.id, variant.id
    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        db.add(Inventory(branch_id=b_id, variant_id=v_id, stock_actual=minimo, avg_cost=50.0))
    else:
        inv.stock_actual = max(inv.stock_actual, minimo)
    db.commit()
    db.close()
    return b_id, v_id


def _titulos(headers):
    res = client.get("/api/v1/notifications/my?limit=100", headers=headers)
    assert res.status_code == 200, res.text
    return [(n["title"], n["reference_type"], n["reference_id"]) for n in res.json()["notifications"]]


def test_checkout_y_alistado_generan_notificaciones_de_pedido():
    headers = get_auth_token()
    b_id, v_id = _preparar_stock()

    client.delete("/api/v1/sales/cart/clear", headers=headers)
    client.post("/api/v1/sales/cart/items", json={"variant_id": v_id, "quantity": 1}, headers=headers)
    chk = client.post("/api/v1/sales/checkout", json={
        "channel": "ONLINE", "branch_id": b_id, "payment_type": "QR",
        "qr_payment": {"qr_reference": f"QR-{uuid.uuid4().hex[:6]}"}, "doc_type": "NOTA_ENTREGA",
    }, headers=headers)
    assert chk.status_code == 201, chk.text
    order_id = chk.json()["id"]

    avisos = _titulos(headers)
    assert any(t.startswith("Compra confirmada") and ref == order_id for t, _, ref in avisos)

    # Alistado: requiere caja abierta del usuario en la sucursal del pedido.
    shift = client.get("/api/v1/sales/shifts/current", headers=headers)
    if shift.status_code != 200 or not shift.json():
        client.post("/api/v1/sales/shifts/open", json={"branch_id": b_id, "opening_amount": 100}, headers=headers)
    upd = client.patch(f"/api/v1/sales/orders/{order_id}/fulfillment", json={"status": "PREPARANDO"}, headers=headers)
    assert upd.status_code == 200, upd.text
    avisos = _titulos(headers)
    assert any(t == "Estamos preparando tu pedido" and ref == order_id for t, _, ref in avisos)


def test_reserva_genera_notificacion_al_cliente_y_al_cancelar():
    headers = get_auth_token()
    b_id, v_id = _preparar_stock()
    from datetime import date, timedelta

    res = client.post("/api/v1/reservations", json={
        "branch_id": b_id,
        "items": [{"variant_id": v_id, "quantity": 1}],
        "appointment_date": str(date.today() + timedelta(days=5)),
        "appointment_time": "15:00",
        "payment_method": "TARJETA",
        "payment_reference": "TARJETA-VISA-****4242",
    }, headers=headers)
    assert res.status_code in (200, 201), res.text
    res_id = res.json()["id"]

    avisos = _titulos(headers)
    assert any(t == "Reserva confirmada" and ref == res_id for t, _, ref in avisos)

    cancel = client.post(f"/api/v1/reservations/{res_id}/cancel", headers=headers)
    assert cancel.status_code == 200, cancel.text
    avisos = _titulos(headers)
    assert any(t == "Reserva cancelada" and ref == res_id for t, _, ref in avisos)
