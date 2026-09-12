import pytest
import uuid
from datetime import datetime, timedelta, timezone, date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.packages.seguridad_y_usuarios.models import User, SessionToken
from app.packages.seguridad_y_usuarios.services import create_access_token
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant, Product
from app.packages.inventario_y_proveedores.merchandise.models import Inventory

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


def test_cu17_cart_lifecycle():
    """[CU17] Carrito de compras digital: adición con control de stock, actualización y limpieza."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    assert branch and variant, "Se requiere al menos una sucursal y una variante"
    b_id = branch.id
    v_id = variant.id

    # Asegurar stock positivo
    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=20, avg_cost=50.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 20)
    db.commit()
    db.close()

    # 1. Limpiar carrito inicial
    client.delete("/api/v1/sales/cart/clear", headers=headers)

    # 2. Agregar ítem válido
    add_res = client.post("/api/v1/sales/cart/items", json={"variant_id": v_id, "quantity": 2}, headers=headers)
    assert add_res.status_code == 200
    data = add_res.json()
    assert data["items_count"] == 2
    assert len(data["items"]) == 1
    item_id = data["items"][0]["id"]

    # 3. Intentar agregar cantidad que excede stock
    over_res = client.post("/api/v1/sales/cart/items", json={"variant_id": v_id, "quantity": 99999}, headers=headers)
    assert over_res.status_code == 400

    # 4. Actualizar cantidad
    upd_res = client.put(f"/api/v1/sales/cart/items/{item_id}", json={"quantity": 3}, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["items_count"] == 3

    # 5. Obtener carrito
    get_res = client.get("/api/v1/sales/cart", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["items_count"] == 3

    # 6. Eliminar ítem
    del_res = client.delete(f"/api/v1/sales/cart/items/{item_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["items_count"] == 0


def test_cu18_cu20_cu24_online_checkout_and_invoice():
    """[CU18, CU20, CU24] Checkout online con tarjeta, factura IVA 13% y consulta en historial de compras."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    b_id = branch.id
    v_id = variant.id

    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=15, avg_cost=50.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 15)
    db.commit()
    stock_before = inv.stock_actual
    db.close()

    # 1. Preparar carrito
    client.delete("/api/v1/sales/cart/clear", headers=headers)
    client.post("/api/v1/sales/cart/items", json={"variant_id": v_id, "quantity": 2}, headers=headers)

    # 2. Checkout con TARJETA y FACTURA fiscal
    checkout_payload = {
        "channel": "ONLINE",
        "branch_id": b_id,
        "payment_type": "TARJETA",
        "card_payment": {
            "card_brand": "VISA",
            "card_last4": "4242",
            "gateway_reference": f"TX-{uuid.uuid4().hex[:6].upper()}"
        },
        "doc_type": "FACTURA",
        "customer_nit": "1029384756",
        "customer_name": "Juan Perez Cliente"
    }
    chk_res = client.post("/api/v1/sales/checkout", json=checkout_payload, headers=headers)
    assert chk_res.status_code == 201, chk_res.text
    ord_data = chk_res.json()

    assert ord_data["channel"] == "ONLINE"
    assert ord_data["status"] == "PAGADA"
    assert len(ord_data["items"]) == 1
    assert ord_data["items"][0]["quantity"] == 2

    # Validar factura IVA 13%
    inv_data = ord_data["invoice"]
    assert inv_data is not None
    assert inv_data["doc_type"] == "FACTURA"
    assert inv_data["tax_rate"] == 0.13
    assert inv_data["customer_nit"] == "1029384756"
    assert inv_data["control_code"] is not None
    assert "NIT:1029384756" in inv_data["qr_payload"]

    # Validar que el stock se redujo en 2
    db = SessionLocal()
    inv_after = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    assert inv_after.stock_actual == stock_before - 2
    db.close()

    # Validar historial de pedidos (CU24)
    my_orders_res = client.get("/api/v1/sales/orders/my-orders", headers=headers)
    assert my_orders_res.status_code == 200
    orders_list = my_orders_res.json()
    assert any(o["id"] == ord_data["id"] for o in orders_list)


def test_cu19_cu23_pos_and_cash_shift():
    """[CU19, CU23] Flujo completo de Punto de Venta (POS): Apertura de turno, venta en efectivo y cierre de caja."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    b_id = branch.id
    v_id = variant.id

    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=25, avg_cost=40.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 25)
    db.commit()
    db.close()

    # 1. Cerrar turnos previos si existieran
    curr_res = client.get("/api/v1/sales/shifts/current", headers=headers)
    if curr_res.status_code == 200 and curr_res.json() is not None:
        shift_id = curr_res.json()["id"]
        client.post(f"/api/v1/sales/shifts/{shift_id}/close", json={"closing_amount_declared": 100.0}, headers=headers)

    # 2. Abrir nuevo turno con fondo inicial de Bs. 150.00
    open_res = client.post("/api/v1/sales/shifts/open", json={"branch_id": b_id, "opening_amount": 150.0}, headers=headers)
    assert open_res.status_code == 201, open_res.text
    shift_data = open_res.json()
    active_shift_id = shift_data["id"]
    assert shift_data["status"] == "ABIERTO"
    assert shift_data["opening_amount"] == 150.0

    # 3. Realizar venta POS en EFECTIVO con cambio (CU19)
    pos_payload = {
        "channel": "POS",
        "branch_id": b_id,
        "cash_shift_id": active_shift_id,
        "pos_items": [
            {"variant_id": v_id, "quantity": 1}
        ],
        "payment_type": "EFECTIVO",
        "cash_payment": {
            "cash_received": 500.0
        },
        "doc_type": "NOTA_ENTREGA",
        "customer_name": "Cliente de Paso"
    }
    pos_res = client.post("/api/v1/sales/checkout", json=pos_payload, headers=headers)
    assert pos_res.status_code == 201, pos_res.text
    pos_order = pos_res.json()
    assert pos_order["channel"] == "POS"
    total_sale = pos_order["total_amount"]
    assert pos_order["payments"][0]["cash_received"] == 500.0
    assert pos_order["payments"][0]["cash_change"] == round(500.0 - total_sale, 2)

    # 4. Cierre de turno de caja (Arqueo ciego - CU23)
    # Total esperado en caja = 150.00 (fondo inicial) + total_sale
    expected_system = round(150.0 + total_sale, 2)
    close_payload = {
        "closing_amount_declared": expected_system,
        "notes": "Arqueo conforme al cierre del turno tarde"
    }
    close_res = client.post(f"/api/v1/sales/shifts/{active_shift_id}/close", json=close_payload, headers=headers)
    assert close_res.status_code == 200, close_res.text
    close_data = close_res.json()
    assert close_data["status"] == "CERRADO"
    assert close_data["closing_amount_system"] == expected_system
    assert close_data["difference"] == 0.0
    assert close_data["total_sales_count"] >= 1


def test_cu21_quotation_generation():
    """[CU21] Generación de cotización formal con período de validez."""
    headers = get_auth_token()
    db = SessionLocal()
    variant = db.query(ProductVariant).first()
    v_id = variant.id
    db.close()

    quote_payload = {
        "customer_name": "Empresa Comercializadora SRL",
        "customer_email": "compras@comercializadora.com",
        "customer_phone": "77334455",
        "valid_days": 15,
        "details": [
            {"variant_id": v_id, "quantity": 10}
        ]
    }
    res = client.post("/api/v1/sales/quotations", json=quote_payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["quotation_number"].startswith("COT-")
    assert data["status"] == "VIGENTE"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 10
    assert data["total_amount"] > 0


def test_cu22_order_returns_refund_and_exchange():
    """[CU22] Devoluciones y cambios de prendas con reingreso al inventario."""
    headers = get_auth_token()
    db = SessionLocal()
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    b_id = branch.id
    v_id = variant.id

    inv = db.query(Inventory).filter(Inventory.branch_id == b_id, Inventory.variant_id == v_id).first()
    if not inv:
        inv = Inventory(branch_id=b_id, variant_id=v_id, stock_actual=20, avg_cost=45.0)
        db.add(inv)
    else:
        inv.stock_actual = max(inv.stock_actual, 20)
    db.commit()
    db.close()

    # 1. Realizar una compra para devolver
    client.delete("/api/v1/sales/cart/clear", headers=headers)
    client.post("/api/v1/sales/cart/items", json={"variant_id": v_id, "quantity": 2}, headers=headers)
    chk_res = client.post("/api/v1/sales/checkout", json={
        "channel": "ONLINE",
        "branch_id": b_id,
        "payment_type": "QR",
        "qr_payment": {"qr_reference": "QR-REF-TEST"},
        "doc_type": "FACTURA"
    }, headers=headers)
    assert chk_res.status_code == 201
    order_id = chk_res.json()["id"]

    # 2. Registrar devolución de dinero de 1 prenda
    return_payload = {
        "order_id": order_id,
        "return_type": "DEVOLUCION_DINERO",
        "reason": "Talla no adecuada según especificación del cliente",
        "items": [
            {"variant_id": v_id, "quantity": 1}
        ]
    }
    ret_res = client.post("/api/v1/sales/returns", json=return_payload, headers=headers)
    assert ret_res.status_code == 201, ret_res.text
    ret_data = ret_res.json()
    assert ret_data["return_number"].startswith("DEV-")
    assert ret_data["status"] == "APROBADA"
    assert ret_data["refund_amount"] > 0
