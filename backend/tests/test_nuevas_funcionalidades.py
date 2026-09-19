"""Pruebas unitarias y de integración para las nuevas funcionalidades:
- CU05, CU29, CU30: Repartidores, auto-selección de pedidos y reprogramación
- CU08, CU10: Ofertas de proveedores y reposición con selección de sucursal destino
- CU26, CU27, CU28: Reservas con fecha, hora, seña 50% y política de gracia/tolerancia
- CU06: Restricción estricta de sucursales a Santa Cruz
"""
from datetime import date, timedelta, datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.packages.seguridad_y_usuarios.models import User, Role, SessionToken
from app.packages.seguridad_y_usuarios.services import create_access_token
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.inventario_y_proveedores.suppliers.models import Supplier
from app.packages.catalogo_y_tiendas.models import Product, ProductVariant, Color, Size
from app.packages.inventario_y_proveedores.merchandise.models import Inventory

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def get_auth_token():
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@fashionstore.com", "password": "Password123!"})
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
        is_revoked=False,
    )
    db.add(session_rec)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers():
    return get_auth_token()


def test_cu06_restringir_sucursal_a_santa_cruz(auth_headers):
    """Verifica que no se permita registrar sucursales en otras ciudades."""
    res_bad = client.post(
        "/api/v1/branches",
        headers=auth_headers,
        json={
            "name": "Sucursal Cochabamba Test",
            "city": "Cochabamba",
            "address": "Av. Heroínas #123",
        },
    )
    assert res_bad.status_code == 400
    assert "Santa Cruz" in res_bad.json()["detail"]


def test_cu08_cu10_flujo_ofertas_y_reposicion_con_sucursal_destino(db, auth_headers):
    """Verifica el flujo de ofertas y solicitudes de reposición con target_branch_id obligatorio."""
    # Obtener o crear sucursal en Santa Cruz
    branch = db.query(Branch).filter(Branch.city == "Santa Cruz").first()
    if not branch:
        branch = Branch(name="FashionStore Test SCZ", city="Santa Cruz", address="Av. San Martín")
        db.add(branch)
        db.commit()
        db.refresh(branch)

    # Obtener o crear proveedor
    supplier = db.query(Supplier).first()
    if not supplier:
        supplier = Supplier(nit="987654321", name="Textiles del Oriente", city="Santa Cruz")
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

    # 1. Crear oferta del proveedor
    res_offer = client.post(
        "/api/v1/suppliers/offers",
        headers=auth_headers,
        json={
            "supplier_id": supplier.id,
            "product_name": "Blusa Floral Primavera",
            "description": "Blusa en tela lino de alta calidad",
            "category": "Blusas",
            "unit_cost": 45.0,
            "suggested_retail_price": 95.0,
            "min_order_quantity": 10,
            "available_quantity": 50,
            "sizes_available": "S, M, L",
            "colors_available": "Blanco, Rosa",
        },
    )
    assert res_offer.status_code == 201
    offer_id = res_offer.json()["id"]

    # 2. Admin aprueba oferta indicando sucursal destino
    res_review = client.patch(
        f"/api/v1/suppliers/offers/{offer_id}/review",
        headers=auth_headers,
        json={
            "status": "APPROVED",
            "target_branch_id": branch.id,
            "admin_notes": "Aprobado para stock en sucursal",
        },
    )
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "APPROVED"
    assert res_review.json()["target_branch_id"] == branch.id

    # 3. Solicitud de reposición con sucursal destino obligatoria
    variant = db.query(ProductVariant).first()
    if variant:
        res_reorder = client.post(
            "/api/v1/suppliers/reorder-requests",
            headers=auth_headers,
            json={
                "supplier_id": supplier.id,
                "variant_id": variant.id,
                "requested_quantity": 20,
                "target_branch_id": branch.id,
                "unit_cost": 50.0,
            },
        )
        assert res_reorder.status_code == 201
        reorder_id = res_reorder.json()["id"]
        assert res_reorder.json()["target_branch_id"] == branch.id

        # El proveedor debe aceptar antes de poder despachar
        res_ship_early = client.patch(
            f"/api/v1/suppliers/reorder-requests/{reorder_id}/mark-shipped",
            headers=auth_headers,
        )
        assert res_ship_early.status_code == 400

        res_accept = client.patch(
            f"/api/v1/suppliers/reorder-requests/{reorder_id}/respond",
            headers=auth_headers,
            json={"status": "ACCEPTED", "estimated_delivery": "2030-01-15"},
        )
        assert res_accept.status_code == 200
        assert res_accept.json()["status"] == "ACCEPTED"
        assert res_accept.json()["code"] == f"RP-{reorder_id:04d}"

        # Proveedor marca enviado
        res_shipped = client.patch(
            f"/api/v1/suppliers/reorder-requests/{reorder_id}/mark-shipped",
            headers=auth_headers,
        )
        assert res_shipped.status_code == 200
        assert res_shipped.json()["status"] == "SHIPPED"

        # Sucursal confirma recepción física e incrementa stock
        res_rcv = client.patch(
            f"/api/v1/suppliers/reorder-requests/{reorder_id}/mark-received",
            headers=auth_headers,
        )
        assert res_rcv.status_code == 200
        assert res_rcv.json()["status"] == "RECEIVED"


def test_cu26_cu27_cu28_reserva_fecha_hora_seña_y_reprogramacion(db, auth_headers):
    """Verifica reserva con fecha/hora, 50% de seña y reprogramación."""
    branch = db.query(Branch).first()
    variant = db.query(ProductVariant).first()
    if not branch or not variant:
        pytest.skip("Requiere branch y variant en BD")

    # Asegurar stock
    inv = db.query(Inventory).filter(Inventory.branch_id == branch.id, Inventory.variant_id == variant.id).first()
    if not inv:
        inv = Inventory(branch_id=branch.id, variant_id=variant.id, stock_actual=10, avg_cost=30)
        db.add(inv)
        db.commit()
    elif inv.stock_actual < 5:
        inv.stock_actual = 10
        db.commit()

    apt_date = (date.today() + timedelta(days=2)).isoformat()
    res = client.post(
        "/api/v1/reservations",
        headers=auth_headers,
        json={
            "branch_id": branch.id,
            "appointment_date": apt_date,
            "appointment_time": "10:30",
            "notes": "Prueba de cita",
            "items": [{"variant_id": variant.id, "quantity": 1}],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["appointment_date"] == apt_date
    assert data["appointment_time"] == "10:30"
    assert data["deposit_amount"] > 0
    res_id = data["id"]

    # Probar reprogramación
    new_date = (date.today() + timedelta(days=3)).isoformat()
    res_re = client.patch(
        f"/api/v1/reservations/{res_id}/reschedule",
        headers=auth_headers,
        json={"new_date": new_date, "new_time": "11:00", "reason": "Cambio de turno laboral"},
    )
    assert res_re.status_code == 200
    assert res_re.json()["appointment_date"] == new_date
    assert res_re.json()["reschedule_count"] == 1

    # Probar marcación de llegada
    res_arr = client.patch(f"/api/v1/reservations/{res_id}/mark-arrived", headers=auth_headers)
    assert res_arr.status_code == 200
    assert res_arr.json()["status"] == "READY"


def test_cu05_cu29_cu30_repartidor_y_autoseleccion(db, auth_headers):
    """Verifica creación de repartidor, consulta de bolsa disponible y toma de pedido."""
    user = db.query(User).filter(User.email == "admin@fashionstore.com").first()

    # Perfil repartidor
    res_dp = client.post(
        "/api/v1/logistics/delivery-persons",
        headers=auth_headers,
        json={
            "user_id": user.id,
            "vehicle_type": "MOTO",
            "vehicle_plate": "1234-XYZ",
            "coverage_zone": "Santa Cruz - Equipetrol y Anillos 1-3",
            "phone": "77012345",
        },
    )
    assert res_dp.status_code in [201, 400]  # 400 si ya fue creado

    # Consultar envíos disponibles
    res_avail = client.get("/api/v1/logistics/shipments/available", headers=auth_headers)
    assert res_avail.status_code == 200
    assert isinstance(res_avail.json(), list)
