import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.packages.seguridad_y_usuarios.models import User, SessionToken
from app.packages.seguridad_y_usuarios.services import create_access_token
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import ProductVariant
from app.packages.inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger, StockTransfer

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


def test_cu15_stock_transfers_lifecycle():
    headers = get_admin_token()
    db = SessionLocal()
    branches = db.query(Branch).limit(2).all()
    assert len(branches) >= 2, "Se requieren al menos 2 sucursales para probar transferencias"
    b1, b2 = branches[0], branches[1]
    b1_id = b1.id
    b2_id = b2.id

    variant = db.query(ProductVariant).first()
    assert variant is not None, "Se requiere al menos una variante de producto"
    var_id = variant.id

    # Asegurar stock inicial en origen para la prueba
    inv_b1 = db.query(Inventory).filter(Inventory.branch_id == b1_id, Inventory.variant_id == var_id).first()
    if not inv_b1:
        inv_b1 = Inventory(branch_id=b1_id, variant_id=var_id, stock_actual=25, avg_cost=80.0)
        db.add(inv_b1)
    else:
        inv_b1.stock_actual = max(inv_b1.stock_actual, 25)
    db.commit()
    initial_origin_stock = inv_b1.stock_actual
    db.close()

    transfer_qty = 5

    # 1. Crear solicitud de transferencia (SOLICITADA)
    payload = {
        "origin_branch_id": b1_id,
        "destination_branch_id": b2_id,
        "notes": "Transferencia de reposición prueba CU15",
        "details": [{"variant_id": var_id, "quantity": transfer_qty}]
    }
    res_create = client.post("/api/v1/merchandise/transfers", json=payload, headers=headers)
    assert res_create.status_code == 201, res_create.text
    trf = res_create.json()
    trf_id = trf["id"]
    assert trf["status"] == "SOLICITADA"
    assert len(trf["details"]) == 1

    # 2. Transición a EN_TRANSITO (Descuento en origen y registro en ledger)
    res_transit = client.put(
        f"/api/v1/merchandise/transfers/{trf_id}/status",
        json={"status": "EN_TRANSITO", "notes": "Salida de mercadería en camión"},
        headers=headers
    )
    assert res_transit.status_code == 200, res_transit.text
    assert res_transit.json()["status"] == "EN_TRANSITO"

    db = SessionLocal()
    inv_after_transit = db.query(Inventory).filter(Inventory.branch_id == b1_id, Inventory.variant_id == var_id).first()
    assert inv_after_transit.stock_actual == initial_origin_stock - transfer_qty

    # Verificar registro en libro mayor (InventoryLedger)
    ledger_out = db.query(InventoryLedger).filter(
        InventoryLedger.reference_id == trf["transfer_number"],
        InventoryLedger.movement_type == "TRANSFERENCIA_SALIDA"
    ).first()
    assert ledger_out is not None
    assert ledger_out.quantity == -transfer_qty
    db.close()

    # 3. Transición a COMPLETADA (Ingreso en destino y registro en ledger)
    res_complete = client.put(
        f"/api/v1/merchandise/transfers/{trf_id}/status",
        json={"status": "COMPLETADA", "notes": "Recepción conforme en almacén de destino"},
        headers=headers
    )
    assert res_complete.status_code == 200, res_complete.text
    assert res_complete.json()["status"] == "COMPLETADA"

    db = SessionLocal()
    ledger_in = db.query(InventoryLedger).filter(
        InventoryLedger.reference_id == trf["transfer_number"],
        InventoryLedger.movement_type == "TRANSFERENCIA_ENTRADA"
    ).first()
    assert ledger_in is not None
    assert ledger_in.quantity == transfer_qty
    db.close()


def test_cu16_stock_alerts_and_thresholds():
    headers = get_admin_token()
    db = SessionLocal()
    inv = db.query(Inventory).first()
    assert inv is not None, "Se requiere al menos un registro de inventario"
    b_id = inv.branch_id
    v_id = inv.variant_id
    db.close()

    # 1. Configurar umbrales de stock mínimo y máximo (CU16)
    res_thresh = client.put(
        f"/api/v1/merchandise/inventory/thresholds/{b_id}/{v_id}",
        json={"stock_minimo": 10, "stock_maximo": 50},
        headers=headers
    )
    assert res_thresh.status_code == 200, res_thresh.text

    # 2. Consultar alertas de stock (CU16)
    res_alerts = client.get("/api/v1/merchandise/inventory/alerts", headers=headers)
    assert res_alerts.status_code == 200, res_alerts.text
    alerts = res_alerts.json()
    assert isinstance(alerts, list)
    for a in alerts:
        assert a["alert_type"] in ["QUIEBRE_STOCK", "SOBRESTOCK"]
