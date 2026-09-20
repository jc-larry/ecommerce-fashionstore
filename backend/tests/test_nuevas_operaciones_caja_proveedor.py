import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.packages.paquete_seguridad_usuarios.models import User, SessionToken
from app.packages.paquete_seguridad_usuarios.services import create_access_token
from app.packages.paquete_catalogo_y_tiendas.models import Product, ProductVariant, Color, Size
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch
from app.packages.paquete_inventario_y_proveedores.suppliers.models import Supplier
from app.packages.paquete_inventario_y_proveedores.suppliers.offer_models import SupplierOffer

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


def test_supplier_discontinued_offer_blocks_reorder():
    headers = get_auth_token()
    db = SessionLocal()

    branch = db.query(Branch).first()
    supplier = db.query(Supplier).first()
    color = db.query(Color).first()
    size = db.query(Size).first()
    assert branch is not None and supplier is not None and color is not None and size is not None

    # Create dedicated test product and variant for isolation
    prod = db.query(Product).filter(Product.name == "Prenda Descontinuada Test").first()
    if not prod:
        cat = db.query(Product).first()
        prod = Product(
            name="Prenda Descontinuada Test",
            description="Prenda exclusiva para prueba de descontinuación",
            base_price=60.0,
            category_id=cat.category_id if cat else 1,
            is_active=True
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)

        variant = ProductVariant(
            product_id=prod.id,
            color_id=color.id,
            size_id=size.id,
            sku="TEST-DESC-001",
            price_override=60.0,
            is_active=True
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
    else:
        variant = db.query(ProductVariant).filter(ProductVariant.product_id == prod.id).first()
        if not variant:
            variant = ProductVariant(
                product_id=prod.id,
                color_id=color.id,
                size_id=size.id,
                sku="TEST-DESC-001",
                price_override=60.0,
                is_active=True
            )
            db.add(variant)
            db.commit()
            db.refresh(variant)

    offer = db.query(SupplierOffer).filter(
        SupplierOffer.supplier_id == supplier.id,
        SupplierOffer.product_name == prod.name
    ).first()

    if not offer:
        offer = SupplierOffer(
            supplier_id=supplier.id,
            product_name=prod.name,
            description="Prenda de prueba",
            category="Casual",
            unit_cost=50.0,
            suggested_retail_price=100.0,
            min_order_quantity=5,
            available_quantity=0,
            sizes_available="S, M, L",
            colors_available="Negro, Blanco",
            status="DESCONTINUADO",
            product_id=prod.id,
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)
    else:
        offer.status = "DESCONTINUADO"
        offer.available_quantity = 0
        offer.product_id = prod.id
        db.commit()

    # Also restore any other offers to APPROVED so other tests pass cleanly
    other_offers = db.query(SupplierOffer).filter(SupplierOffer.product_name != prod.name).all()
    for o in other_offers:
        if o.status in ("DESCONTINUADO", "AGOTADO"):
            o.status = "APPROVED"
            o.available_quantity = 100
    db.commit()

    payload = {
        "supplier_id": supplier.id,
        "variant_id": variant.id,
        "requested_quantity": 10,
        "target_branch_id": branch.id,
        "unit_cost": 50.0
    }

    res = client.post("/api/v1/suppliers/reorder-requests", json=payload, headers=headers)
    db.close()

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "ya no trae" in detail


def test_branch_fulfillment_order_lifecycle():
    headers = get_auth_token()
    res = client.get("/api/v1/sales/orders-fulfillment", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_cash_shift_breakdown_response():
    headers = get_auth_token()
    res = client.get("/api/v1/sales/shifts", headers=headers)
    assert res.status_code == 200
    shifts = res.json()
    assert len(shifts) > 0

    s = shifts[0]
    assert "total_cash_sales" in s
    assert "total_card_sales" in s
    assert "total_qr_sales" in s
    assert "total_reservation_sales" in s
    assert "total_delivery_sales" in s
