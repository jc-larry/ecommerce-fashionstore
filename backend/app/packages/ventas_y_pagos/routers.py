import uuid
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app.db.session import get_db

from app.packages.ventas_y_pagos.models import (
    Order, OrderItem, Payment, EfectivoPayment, TarjetaPayment, QRPayment, CreditoPayment,
    Invoice, Cart, CartItem, CashShift, Quotation, QuotationItem, OrderReturn, OrderReturnItem,
)
from app.packages.ventas_y_pagos.schemas import (
    CartItemAdd, CartItemUpdate, CartItemResponse, CartResponse,
    CheckoutRequest, OrderResponse, OrderItemResponse, PaymentResponse, InvoiceResponse,
    CashShiftOpen, CashShiftClose, CashShiftResponse,
    QuotationCreate, QuotationResponse, QuotationConvertRequest,
    OrderReturnCreate, OrderReturnResponse,
)
from app.packages.catalogo_y_tiendas.branches.models import Branch
from app.packages.catalogo_y_tiendas.models import Product, ProductVariant, Color, Size, Coupon
from app.packages.inventario_y_proveedores.merchandise.models import Inventory, InventoryLedger
from app.packages.seguridad_y_usuarios import User, RoleChecker, log_event, get_current_user, get_branch_scope, BranchScope

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])

staff_check = RoleChecker(allowed_roles=["SUPERADMIN", "ENCARGADO", "CAJERO"])


# ===================================================================
# CU17 — Carrito de Compras Digital
# ===================================================================

def _get_or_create_cart(db: Session, user: Optional[User], session_id: Optional[str] = None) -> Cart:
    cart = None
    if user:
        cart = db.query(Cart).filter(Cart.user_id == user.id).first()
    elif session_id:
        cart = db.query(Cart).filter(Cart.session_id == session_id).first()

    if not cart:
        cart = Cart(
            user_id=user.id if user else None,
            session_id=session_id if not user else None,
        )
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _build_cart_response(db: Session, cart: Cart) -> CartResponse:
    items_resp = []
    subtotal = 0.0

    for item in cart.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            continue
        prod = db.query(Product).filter(Product.id == variant.product_id).first()
        size = db.query(Size).filter(Size.id == variant.size_id).first()
        color = db.query(Color).filter(Color.id == variant.color_id).first()

        unit_price = float(prod.base_price if prod else 0.0)
        item_subtotal = round(unit_price * item.quantity, 2)
        subtotal += item_subtotal

        # Stock total disponible entre todas las sucursales
        stock_sum = (
            db.query(func.sum(Inventory.stock_actual))
            .filter(Inventory.variant_id == item.variant_id)
            .scalar() or 0
        )

        items_resp.append(
            CartItemResponse(
                id=item.id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
                sku=variant.sku,
                product_name=prod.name if prod else "Prenda",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
                image_url=prod.images[0].image_url if (prod and prod.images) else None,
                stock_available=int(stock_sum),
            )
        )

    return CartResponse(
        id=cart.id,
        items=items_resp,
        subtotal=round(subtotal, 2),
        items_count=sum(i.quantity for i in items_resp),
    )


@router.get("/cart", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Consulta el carrito de compras digital del usuario autenticado."""
    cart = _get_or_create_cart(db, current_user)
    return _build_cart_response(db, cart)


@router.post("/cart/items", response_model=CartResponse)
def add_to_cart(
    item_in: CartItemAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Agrega una prenda al carrito con control estricto de existencias (bloqueo stock = 0)."""
    variant = db.query(ProductVariant).filter(ProductVariant.id == item_in.variant_id).first()
    if not variant or not variant.is_active:
        raise HTTPException(status_code=404, detail="Variante de prenda no encontrada o inactiva.")

    # Control de existencias físicas
    stock_total = (
        db.query(func.sum(Inventory.stock_actual))
        .filter(Inventory.variant_id == item_in.variant_id)
        .scalar() or 0
    )
    if stock_total <= 0:
        raise HTTPException(
            status_code=400,
            detail="La prenda se encuentra temporalmente agotada en todas las sucursales (stock = 0)."
        )

    cart = _get_or_create_cart(db, current_user)
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id, CartItem.variant_id == item_in.variant_id
    ).first()

    desired_qty = item_in.quantity + (existing_item.quantity if existing_item else 0)
    if desired_qty > stock_total:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Solo quedan {stock_total} unidades disponibles."
        )

    if existing_item:
        existing_item.quantity = desired_qty
    else:
        db.add(CartItem(cart_id=cart.id, variant_id=item_in.variant_id, quantity=item_in.quantity))

    db.commit()
    return _build_cart_response(db, cart)


@router.put("/cart/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    item_id: int,
    item_in: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Actualiza la cantidad de un ítem en el carrito (0 lo elimina)."""
    cart = _get_or_create_cart(db, current_user)
    cart_item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado en el carrito.")

    if item_in.quantity <= 0:
        db.delete(cart_item)
    else:
        stock_total = (
            db.query(func.sum(Inventory.stock_actual))
            .filter(Inventory.variant_id == cart_item.variant_id)
            .scalar() or 0
        )
        if item_in.quantity > stock_total:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente. Solo quedan {stock_total} unidades disponibles."
            )
        cart_item.quantity = item_in.quantity

    db.commit()
    return _build_cart_response(db, cart)


@router.delete("/cart/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Quita un producto del carrito digital."""
    cart = _get_or_create_cart(db, current_user)
    db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).delete()
    db.commit()
    return _build_cart_response(db, cart)


@router.delete("/cart/clear", response_model=CartResponse)
def clear_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU17] Vacía completamente el carrito digital."""
    cart = _get_or_create_cart(db, current_user)
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    return _build_cart_response(db, cart)


# ===================================================================
# CU18, CU19, CU20 — Checkout Polimórfico, POS y Facturación IVA 13%
# ===================================================================

def _build_order_response(db: Session, order: Order) -> OrderResponse:
    items_resp = []
    for it in order.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == it.variant_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
        size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
        color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None

        items_resp.append(
            OrderItemResponse(
                id=it.id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                unit_price=float(it.unit_price),
                subtotal=round(float(it.unit_price) * it.quantity, 2),
                product_name=prod.name if prod else "Prenda",
                sku=variant.sku if variant else "N/A",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
            )
        )

    payments_resp = [
        PaymentResponse(
            id=p.id,
            payment_type=p.payment_type,
            amount=float(p.amount),
            status=p.status,
            paid_at=p.paid_at,
            cash_received=float(p.cash_received) if p.cash_received is not None else None,
            cash_change=float(p.cash_change) if p.cash_change is not None else None,
            card_brand=p.card_brand,
            card_last4=p.card_last4,
            qr_reference=p.qr_reference,
        )
        for p in order.payments
    ]

    inv_resp = None
    if order.invoice:
        inv = order.invoice
        qr_payload = f"NIT:{inv.customer_nit or '0'}|FAC:{inv.id}|AUT:18273645|TOTAL:{inv.total}|IVA:{inv.tax_amount}|FECHA:{inv.issued_at.isoformat()}|COD:{inv.control_code or 'N/A'}"
        inv_resp = InvoiceResponse(
            id=inv.id,
            doc_type=inv.doc_type,
            subtotal=float(inv.subtotal),
            tax_rate=float(inv.tax_rate),
            tax_amount=float(inv.tax_amount),
            total=float(inv.total),
            control_code=inv.control_code,
            customer_nit=inv.customer_nit,
            customer_name=inv.customer_name,
            issued_at=inv.issued_at,
            qr_payload=qr_payload,
        )

    order_num = f"ORD-{order.created_at.year}-{order.id:06d}"

    return OrderResponse(
        id=order.id,
        order_number=order_num,
        channel=order.channel,
        status=order.status,
        subtotal=float(order.subtotal),
        discount_amount=float(order.discount_amount),
        coupon_code=order.coupon_code,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        items=items_resp,
        payments=payments_resp,
        invoice=inv_resp,
    )


@router.post("/checkout", response_model=OrderResponse, status_code=201)
def process_checkout(
    data: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU18 / CU19 / CU20] Procesa una compra omnicanal con herencia de pagos y facturación IVA 13% (ACID)."""
    # [Separación por sucursal] Una venta POS es una operación de personal de tienda: exige
    # rol de staff y fuerza la sucursal real del usuario (ignora branch_id del cliente).
    # El canal ONLINE sigue abierto a cualquier usuario autenticado (checkout de cliente),
    # donde branch_id es solo el punto de recogida elegido, no un límite de propiedad de datos.
    if data.channel == "POS":
        user_roles = [r.name for r in current_user.roles]
        if not any(r in user_roles for r in ("SUPERADMIN", "ENCARGADO", "CAJERO")):
            raise HTTPException(status_code=403, detail="Solo el personal de tienda puede registrar ventas en POS.")
        scope = get_branch_scope(current_user, db)
        if not scope.is_central:
            data.branch_id = scope.branch_id

    branch = db.query(Branch).filter(Branch.id == data.branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada.")

    # Si es POS, validar turno de caja abierto y de propiedad del cajero autenticado
    if data.channel == "POS":
        if not data.cash_shift_id:
            raise HTTPException(status_code=400, detail="Ventas en POS requieren un turno de caja activo (cash_shift_id).")
        shift = db.query(CashShift).filter(
            CashShift.id == data.cash_shift_id,
            CashShift.status == "ABIERTO"
        ).first()
        if not shift:
            raise HTTPException(status_code=400, detail="El turno de caja especificado no existe o ya está cerrado.")
        if shift.cashier_id != current_user.id:
            raise HTTPException(status_code=400, detail="El turno de caja especificado no pertenece a tu usuario.")
        if shift.branch_id != data.branch_id:
            raise HTTPException(
                status_code=400,
                detail=f"Inconsistencia multi-sucursal: El turno de caja #{shift.id} pertenece a otra sucursal, no a la sucursal seleccionada (#{data.branch_id})."
            )

    # 1. Determinar ítems comprados
    checkout_items: List[tuple[int, int, float]] = []  # (variant_id, quantity, unit_price)

    if data.channel == "POS":
        if not data.pos_items or len(data.pos_items) == 0:
            raise HTTPException(status_code=400, detail="Debes ingresar al menos una prenda en el POS.")
        for item in data.pos_items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
            if not variant:
                raise HTTPException(status_code=404, detail=f"Variante {item.variant_id} no encontrada.")
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            checkout_items.append((item.variant_id, item.quantity, float(prod.base_price if prod else 0.0)))
    else:
        # Canal ONLINE: tomar ítems del carrito del usuario
        cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="El carrito de compras está vacío.")
        for item in cart.items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
            if not variant:
                continue
            prod = db.query(Product).filter(Product.id == variant.product_id).first()
            checkout_items.append((item.variant_id, item.quantity, float(prod.base_price if prod else 0.0)))

    # 2. Validar stock en la sucursal seleccionada y calcular subtotal
    subtotal = 0.0
    for var_id, qty, unit_price in checkout_items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == var_id
        ).first()
        current_stock = inv.stock_actual if inv else 0
        if current_stock < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en la sucursal para la prenda con ID variante {var_id} (Disponible: {current_stock}, Requerido: {qty})."
            )
        subtotal += unit_price * qty

    subtotal = round(subtotal, 2)

    # 3. Aplicar cupón de descuento si existe (CU13)
    discount_amount = 0.0
    if data.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == data.coupon_code.strip().upper(),
            Coupon.is_active == True,
            Coupon.valid_from <= func.now(),
            Coupon.valid_until >= func.now(),
        ).first()
        if coupon and subtotal >= float(coupon.min_purchase_amount) and coupon.used_count < coupon.max_uses:
            if coupon.discount_type == "PORCENTAJE":
                discount_amount = round(subtotal * (float(coupon.discount_value) / 100.0), 2)
            else:
                discount_amount = round(min(subtotal, float(coupon.discount_value)), 2)
            coupon.used_count += 1

    total_amount = max(0.0, round(subtotal - discount_amount, 2))

    # 4. Crear la Orden
    order = Order(
        user_id=current_user.id,
        branch_id=data.branch_id,
        channel=data.channel,
        status="PAGADA",
        subtotal=subtotal,
        discount_amount=discount_amount,
        coupon_code=data.coupon_code.strip().upper() if data.coupon_code else None,
        total_amount=total_amount,
        cash_shift_id=data.cash_shift_id if data.channel == "POS" else None,
    )
    db.add(order)
    db.flush()

    # 5. Insertar ítems y descontar inventario con registro en ledger
    order_ref = f"ORD-{order.id}"
    for var_id, qty, unit_price in checkout_items:
        db.add(OrderItem(order_id=order.id, variant_id=var_id, quantity=qty, unit_price=unit_price))

        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == var_id
        ).first()
        inv.stock_actual -= qty

        db.add(InventoryLedger(
            branch_id=data.branch_id,
            variant_id=var_id,
            quantity=-qty,
            movement_type="VENTA",
            unit_cost=float(inv.avg_cost or 0),
            reference_id=order_ref,
        ))

    # 6. Crear Medio de Pago Polimórfico (STI)
    p_type = data.payment_type
    if p_type == "EFECTIVO":
        cash_rec = data.cash_payment.cash_received if data.cash_payment else total_amount
        if cash_rec < total_amount:
            raise HTTPException(status_code=400, detail=f"El efectivo recibido (Bs. {cash_rec}) no cubre el total (Bs. {total_amount}).")
        change = round(cash_rec - total_amount, 2)
        payment = EfectivoPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            cash_received=cash_rec,
            cash_change=change,
        )
    elif p_type == "TARJETA":
        if not data.card_payment:
            raise HTTPException(status_code=400, detail="Faltan datos de la tarjeta bancaria.")
        payment = TarjetaPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            card_brand=data.card_payment.card_brand,
            card_last4=data.card_payment.card_last4,
            gateway_reference=data.card_payment.gateway_reference or f"TX-{uuid.uuid4().hex[:8].upper()}",
        )
    elif p_type == "QR":
        qr_ref = data.qr_payment.qr_reference if data.qr_payment else f"QR-{uuid.uuid4().hex[:8].upper()}"
        payment = QRPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            qr_reference=qr_ref,
        )
    elif p_type == "CREDITO":
        due_date = data.credit_payment.credit_due_date if data.credit_payment else (date.today() + timedelta(days=30))
        payment = CreditoPayment(
            order_id=order.id,
            amount=total_amount,
            status="CONFIRMADO",
            credit_due_date=due_date,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Medio de pago {p_type} no soportado.")

    db.add(payment)

    # 7. Generar Comprobante Fiscal (Factura IVA 13% o Nota de Entrega)
    tax_rate = 0.130
    tax_amount = round(total_amount * tax_rate, 2)
    control_code = None
    if data.doc_type == "FACTURA":
        control_code = f"{uuid.uuid4().hex[:2]}-{uuid.uuid4().hex[2:4]}-{uuid.uuid4().hex[4:6]}-{uuid.uuid4().hex[6:8]}".upper()

    invoice = Invoice(
        order_id=order.id,
        doc_type=data.doc_type,
        tax_rate=tax_rate,
        subtotal=total_amount,
        tax_amount=tax_amount,
        total=total_amount,
        control_code=control_code,
        customer_nit=data.customer_nit.strip() if data.customer_nit else "0",
        customer_name=data.customer_name.strip() if data.customer_name else f"{current_user.first_name} {current_user.last_name}".strip(),
    )
    db.add(invoice)

    # 8. Si era venta ONLINE, vaciar el carrito
    if data.channel == "ONLINE":
        cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
        if cart:
            db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

    db.commit()
    db.refresh(order)

    log_event(db, current_user.id, "INSERT", "orders", order.id,
              {"channel": data.channel, "total": total_amount, "doc_type": data.doc_type},
              request.client.host)

    return _build_order_response(db, order)


@router.get("/orders/my-orders", response_model=List[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[CU24] Historial de compras y pedidos del cliente en sesión."""
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_build_order_response(db, o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU24] Detalle de una compra con sus ítems, comprobante y pago."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    is_owner = order.user_id == current_user.id
    is_staff_same_branch = not scope.is_central and order.branch_id == scope.branch_id
    if not (is_owner or scope.is_central or is_staff_same_branch):
        # 404 en vez de 403: no confirmar a terceros que el pedido existe.
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
    return _build_order_response(db, order)


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    branch_id: Optional[int] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[Separación por sucursal] Lista los pedidos de la sucursal del usuario (o consolidado si es central)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(Order)
    if effective_branch_id:
        query = query.filter(Order.branch_id == effective_branch_id)
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return [_build_order_response(db, o) for o in orders]


# ===================================================================
# CU23 — Arqueo de Caja (Apertura y Cierre de Turno)
# ===================================================================

def _build_cash_shift_response(db: Session, shift: CashShift) -> CashShiftResponse:
    cashier = db.query(User).filter(User.id == shift.cashier_id).first()
    branch = db.query(Branch).filter(Branch.id == shift.branch_id).first()

    # Ventas en efectivo durante el turno
    orders_in_shift = db.query(Order).filter(Order.cash_shift_id == shift.id).all()
    cash_total = 0.0
    for ord in orders_in_shift:
        for p in ord.payments:
            if p.payment_type == "EFECTIVO":
                cash_total += float(p.amount)

    return CashShiftResponse(
        id=shift.id,
        cashier_id=shift.cashier_id,
        cashier_name=f"{cashier.first_name} {cashier.last_name}".strip() if cashier else "Cajero",
        branch_id=shift.branch_id,
        branch_name=branch.name if branch else "Sucursal",
        opening_amount=float(shift.opening_amount),
        closing_amount_declared=float(shift.closing_amount_declared) if shift.closing_amount_declared is not None else None,
        closing_amount_system=float(shift.closing_amount_system) if shift.closing_amount_system is not None else None,
        difference=float(shift.difference) if shift.difference is not None else None,
        status=shift.status,
        opened_at=shift.opened_at,
        closed_at=shift.closed_at,
        notes=shift.notes,
        total_sales_count=len(orders_in_shift),
        total_cash_sales=round(cash_total, 2),
    )


@router.post("/shifts/open", response_model=CashShiftResponse, status_code=201)
def open_cash_shift(
    data: CashShiftOpen,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Apertura de turno de caja con fondo inicial."""
    if not scope.is_central:
        data.branch_id = scope.branch_id

    active_shift = db.query(CashShift).filter(
        CashShift.cashier_id == current_user.id,
        CashShift.status == "ABIERTO"
    ).first()
    if active_shift:
        from app.packages.catalogo_y_tiendas.branches.models import Branch
        shift_branch = db.query(Branch).filter(Branch.id == active_shift.branch_id).first()
        branch_desc = f"'{shift_branch.name}'" if shift_branch else f"sucursal #{active_shift.branch_id}"
        raise HTTPException(
            status_code=400, 
            detail=f"Ya tienes el Turno #{active_shift.id} ABIERTO en la sucursal {branch_desc}. Debes cerrarlo o hacer el arqueo en esa sucursal antes de abrir una nueva caja aquí."
        )

    shift = CashShift(
        cashier_id=current_user.id,
        branch_id=data.branch_id,
        opening_amount=data.opening_amount,
        status="ABIERTO",
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    log_event(db, current_user.id, "INSERT", "cash_shifts", shift.id,
              {"opening_amount": data.opening_amount, "branch_id": data.branch_id},
              request.client.host)

    return _build_cash_shift_response(db, shift)


@router.get("/shifts/current", response_model=Optional[CashShiftResponse])
def get_current_cash_shift(
    branch_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Obtiene el turno de caja abierto del usuario actual (opcionalmente filtrado por sucursal)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(CashShift).filter(
        CashShift.cashier_id == current_user.id,
        CashShift.status == "ABIERTO"
    )
    if effective_branch_id is not None:
        query = query.filter(CashShift.branch_id == effective_branch_id)
    shift = query.first()
    if not shift:
        return None
    return _build_cash_shift_response(db, shift)


@router.get("/shifts", response_model=List[CashShiftResponse])
def get_cash_shifts(
    branch_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Historial de turnos y arqueos de caja por sucursal o consolidado global (Casa Matriz)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(CashShift)
    if effective_branch_id is not None:
        query = query.filter(CashShift.branch_id == effective_branch_id)
    if status:
        query = query.filter(CashShift.status == status)
    shifts = query.order_by(CashShift.id.desc()).limit(limit).all()
    return [_build_cash_shift_response(db, s) for s in shifts]


@router.post("/shifts/{shift_id}/close", response_model=CashShiftResponse)
def close_cash_shift(
    shift_id: int,
    data: CashShiftClose,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU23] Cierre ciego de turno de caja y balance con ventas del sistema."""
    shift = db.query(CashShift).filter(CashShift.id == shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Turno de caja no encontrado.")
    if not scope.is_central and shift.branch_id != scope.branch_id:
        raise HTTPException(status_code=404, detail="Turno de caja no encontrado.")
    if shift.status == "CERRADO":
        raise HTTPException(status_code=400, detail="El turno de caja ya se encuentra cerrado.")

    # Calcular ventas del sistema en efectivo
    orders_in_shift = db.query(Order).filter(Order.cash_shift_id == shift.id).all()
    cash_sales = 0.0
    for ord in orders_in_shift:
        for p in ord.payments:
            if p.payment_type == "EFECTIVO":
                cash_sales += float(p.amount)

    system_total = round(float(shift.opening_amount) + cash_sales, 2)
    difference = round(data.closing_amount_declared - system_total, 2)

    shift.closing_amount_declared = data.closing_amount_declared
    shift.closing_amount_system = system_total
    shift.difference = difference
    shift.status = "CERRADO"
    shift.closed_at = func.now()
    if data.notes:
        shift.notes = data.notes

    db.commit()
    db.refresh(shift)

    log_event(db, current_user.id, "UPDATE", "cash_shifts", shift.id,
              {"declared": data.closing_amount_declared, "system": system_total, "diff": difference},
              request.client.host)

    return _build_cash_shift_response(db, shift)


# ===================================================================
# CU21 — Generación de Cotizaciones
# ===================================================================

@router.post("/quotations", response_model=QuotationResponse, status_code=201)
def create_quotation(
    data: QuotationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21] Genera una cotización comercial con período de validez."""
    if not data.details:
        raise HTTPException(status_code=400, detail="La cotización debe incluir al menos una prenda.")

    total = 0.0
    q_items: List[tuple[int, int, float]] = []

    for item in data.details:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variante {item.variant_id} no encontrada.")
        prod = db.query(Product).filter(Product.id == variant.product_id).first()
        u_price = float(prod.base_price if prod else 0.0)
        total += u_price * item.quantity
        q_items.append((item.variant_id, item.quantity, u_price))

    q_num = f"COT-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    valid_until = datetime.now(timezone.utc) + timedelta(days=data.valid_days)

    quotation = Quotation(
        quotation_number=q_num,
        customer_name=data.customer_name.strip(),
        customer_email=data.customer_email.strip() if data.customer_email else None,
        customer_phone=data.customer_phone.strip() if data.customer_phone else None,
        created_by_id=current_user.id,
        branch_id=scope.branch_id if not scope.is_central else None,
        total_amount=round(total, 2),
        valid_until=valid_until,
        status="VIGENTE",
    )
    db.add(quotation)
    db.flush()

    created_items = []
    for var_id, qty, u_price in q_items:
        qi = QuotationItem(quotation_id=quotation.id, variant_id=var_id, quantity=qty, unit_price=u_price)
        db.add(qi)
        created_items.append((qi, var_id, qty, u_price))
    db.flush()

    items_resp = []
    for qi, var_id, qty, u_price in created_items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == var_id).first()
        prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
        size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
        color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None

        items_resp.append(
            OrderItemResponse(
                id=qi.id,
                variant_id=var_id,
                quantity=qty,
                unit_price=u_price,
                subtotal=round(u_price * qty, 2),
                product_name=prod.name if prod else "Prenda",
                sku=variant.sku if variant else "N/A",
                size=size.name if size else "Única",
                color=color.name if color else "Estándar",
            )
        )

    db.commit()
    db.refresh(quotation)

    log_event(db, current_user.id, "INSERT", "quotations", quotation.id,
              {"quotation_number": quotation.quotation_number, "total": float(quotation.total_amount)},
              request.client.host)

    branch = db.query(Branch).filter(Branch.id == quotation.branch_id).first() if quotation.branch_id else None
    return QuotationResponse(
        id=quotation.id,
        quotation_number=quotation.quotation_number,
        customer_name=quotation.customer_name,
        customer_email=quotation.customer_email,
        customer_phone=quotation.customer_phone,
        total_amount=float(quotation.total_amount),
        valid_until=quotation.valid_until,
        status=quotation.status,
        created_at=quotation.created_at,
        items=items_resp,
        branch_id=quotation.branch_id,
        branch_name=branch.name if branch else None,
    )


@router.get("/quotations", response_model=List[QuotationResponse])
def list_quotations(
    branch_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21] Lista el historial de cotizaciones comerciales generadas (scoped por sucursal)."""
    effective_branch_id = branch_id if scope.is_central else scope.branch_id
    query = db.query(Quotation)
    if effective_branch_id:
        query = query.filter(Quotation.branch_id == effective_branch_id)
    quotes = query.order_by(Quotation.id.desc()).limit(limit).all()
    branches_by_id = {b.id: b.name for b in db.query(Branch.id, Branch.name).all()}
    results = []
    now_utc = datetime.now(timezone.utc)
    for q in quotes:
        v_until = q.valid_until
        if v_until.tzinfo is None:
            v_until = v_until.replace(tzinfo=timezone.utc)
        if q.status == "VIGENTE" and now_utc > v_until:
            q.status = "EXPIRADA"
            db.commit()

        items_resp = []
        for qi in q.items:
            variant = db.query(ProductVariant).filter(ProductVariant.id == qi.variant_id).first()
            prod = db.query(Product).filter(Product.id == variant.product_id).first() if variant else None
            size = db.query(Size).filter(Size.id == variant.size_id).first() if variant else None
            color = db.query(Color).filter(Color.id == variant.color_id).first() if variant else None
            items_resp.append(
                OrderItemResponse(
                    id=qi.id,
                    variant_id=qi.variant_id,
                    quantity=qi.quantity,
                    unit_price=float(qi.unit_price),
                    subtotal=round(float(qi.unit_price) * qi.quantity, 2),
                    product_name=prod.name if prod else "Prenda",
                    sku=variant.sku if variant else "N/A",
                    size=size.name if size else "Única",
                    color=color.name if color else "Estándar",
                )
            )
        results.append(
            QuotationResponse(
                id=q.id,
                quotation_number=q.quotation_number,
                customer_name=q.customer_name,
                customer_email=q.customer_email,
                customer_phone=q.customer_phone,
                total_amount=float(q.total_amount),
                valid_until=q.valid_until,
                status=q.status,
                created_at=q.created_at,
                items=items_resp,
                branch_id=q.branch_id,
                branch_name=branches_by_id.get(q.branch_id) if q.branch_id else None,
            )
        )
    return results


@router.post("/quotations/{quotation_id}/convert", response_model=OrderResponse)
def convert_quotation_to_order(
    quotation_id: int,
    data: QuotationConvertRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU21 -> CU18/CU20] Convierte una cotización vigente en venta formal con emisión de factura."""
    if not scope.is_central:
        data.branch_id = scope.branch_id

    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Cotización no encontrada.")

    if quotation.status == "CONVERTIDA":
        raise HTTPException(status_code=400, detail="Esta cotización ya fue convertida en una venta anteriormente.")

    now_utc = datetime.now(timezone.utc)
    v_until = quotation.valid_until
    if v_until.tzinfo is None:
        v_until = v_until.replace(tzinfo=timezone.utc)
    if now_utc > v_until:
        quotation.status = "EXPIRADA"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"La cotización {quotation.quotation_number} ha vencido el {quotation.valid_until.strftime('%d/%m/%Y')}. La validez de la oferta expiró y los precios no son vinculantes; debe generarse una nueva cotización."
        )

    # Validar stock en la sucursal seleccionada
    for qi in quotation.items:
        inv = db.query(Inventory).filter(
            Inventory.branch_id == data.branch_id,
            Inventory.variant_id == qi.variant_id
        ).first()
        avail = inv.stock_actual if inv else 0
        if avail < qi.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente en la sucursal para la prenda variante #{qi.variant_id} (Disponible: {avail}, Requerido: {qi.quantity})."
            )

    pos_items = [CartItemAdd(variant_id=qi.variant_id, quantity=qi.quantity) for qi in quotation.items]
    checkout_payload = CheckoutRequest(
        channel="POS",
        branch_id=data.branch_id,
        cash_shift_id=data.cash_shift_id,
        payment_method=data.payment_method,
        pos_items=pos_items,
        customer_nit=data.customer_nit or "0",
        customer_business_name=data.customer_business_name or quotation.customer_name,
    )
    order_res = process_checkout(checkout_payload, request, db, current_user)
    quotation.status = "CONVERTIDA"
    db.commit()
    return order_res


# ===================================================================
# CU22 — Devoluciones y Cambios de Prendas
# ===================================================================

@router.post("/returns", response_model=OrderReturnResponse, status_code=201)
def process_order_return(
    data: OrderReturnCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_check),
    scope: BranchScope = Depends(get_branch_scope),
):
    """[CU22] Procesa devolución de dinero o cambio de prendas reingresando stock al inventario."""
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")
    if not scope.is_central and order.branch_id != scope.branch_id:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    # [Regla de Negocio] Validación de plazo máximo de 30 días para devolución
    if order.created_at:
        now_utc = datetime.now(timezone.utc)
        order_time = order.created_at
        if order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
        diff_days = (now_utc - order_time).days
        if diff_days > 30:
            raise HTTPException(
                status_code=400,
                detail=f"Plazo de devolución vencido. La compra fue realizada hace {diff_days} días (el {order.created_at.strftime('%d/%m/%Y')}). Por política comercial de tienda, el plazo máximo para cambios o devoluciones es de 30 días calendario."
            )

    refund_total = 0.0
    for it in data.items:
        order_it = db.query(OrderItem).filter(
            OrderItem.order_id == order.id, OrderItem.variant_id == it.variant_id
        ).first()
        if not order_it:
            raise HTTPException(status_code=400, detail=f"La prenda con ID variante {it.variant_id} no pertenece a esta orden.")
        if it.quantity > order_it.quantity:
            raise HTTPException(status_code=400, detail="La cantidad a devolver no puede superar la cantidad comprada.")

        if data.return_type == "DEVOLUCION_DINERO":
            refund_total += float(order_it.unit_price) * it.quantity

    ret_num = f"DEV-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    order_ret = OrderReturn(
        return_number=ret_num,
        order_id=order.id,
        processed_by_id=current_user.id,
        return_type=data.return_type,
        reason=data.reason,
        refund_amount=round(refund_total, 2),
        status="APROBADA",
    )
    db.add(order_ret)
    db.flush()

    for it in data.items:
        db.add(OrderReturnItem(
            return_id=order_ret.id,
            variant_id=it.variant_id,
            quantity=it.quantity,
            replacement_variant_id=it.replacement_variant_id,
        ))

        # Reingreso físico al stock de la sucursal
        inv = db.query(Inventory).filter(
            Inventory.branch_id == order.branch_id,
            Inventory.variant_id == it.variant_id
        ).first()
        if inv:
            inv.stock_actual += it.quantity
            db.add(InventoryLedger(
                branch_id=order.branch_id,
                variant_id=it.variant_id,
                quantity=it.quantity,
                movement_type="DEVOLUCION_CLIENTE",
                unit_cost=float(inv.avg_cost or 0),
                reference_id=ret_num,
            ))

        # Si es cambio, descontar la prenda de reemplazo
        if data.return_type == "CAMBIO_PRENDA" and it.replacement_variant_id:
            repl_inv = db.query(Inventory).filter(
                Inventory.branch_id == order.branch_id,
                Inventory.variant_id == it.replacement_variant_id
            ).first()
            if not repl_inv or repl_inv.stock_actual < it.quantity:
                raise HTTPException(status_code=400, detail="Stock insuficiente para la prenda de cambio.")
            repl_inv.stock_actual -= it.quantity
            db.add(InventoryLedger(
                branch_id=order.branch_id,
                variant_id=it.replacement_variant_id,
                quantity=-it.quantity,
                movement_type="VENTA",
                unit_cost=float(repl_inv.avg_cost or 0),
                reference_id=ret_num,
            ))

    db.commit()
    db.refresh(order_ret)

    log_event(db, current_user.id, "INSERT", "order_returns", order_ret.id,
              {"return_number": order_ret.return_number, "order_id": order.id, "type": data.return_type},
              request.client.host)

    return OrderReturnResponse(
        id=order_ret.id,
        return_number=order_ret.return_number,
        order_id=order_ret.order_id,
        return_type=order_ret.return_type,
        reason=order_ret.reason,
        refund_amount=float(order_ret.refund_amount),
        status=order_ret.status,
        created_at=order_ret.created_at,
    )
