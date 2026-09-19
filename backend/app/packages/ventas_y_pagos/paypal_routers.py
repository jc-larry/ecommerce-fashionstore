"""Rutas API para la Pasarela de Pagos PayPal (CU18, CU19, CU26)."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.config import settings
from app.packages.seguridad_y_usuarios.models import User
from app.packages.seguridad_y_usuarios.routers import get_current_user
from app.packages.ventas_y_pagos.schemas import (
    PayPalOrderCreateRequest,
    PayPalOrderCaptureRequest,
)
from app.packages.ventas_y_pagos.paypal_service import paypal_service

router = APIRouter(prefix="/payments/paypal", tags=["Ventas y Pagos - PayPal"])


@router.get("/config")
def get_paypal_config():
    """Retorna la configuración pública para inicializar el SDK de PayPal en frontend/mobile.

    El Client ID es público por diseño (va en el <script> del SDK); el Secret nunca sale del
    backend. `simulated=True` indica que no hay credenciales y el frontend usa el simulador.
    """
    simulated = paypal_service.is_simulation()
    return {
        "client_id": None if simulated else settings.PAYPAL_CLIENT_ID,
        "mode": settings.PAYPAL_MODE,
        "currency": "USD",
        "exchange_rate_bob_usd": settings.PAYPAL_EXCHANGE_RATE_BOB_USD,
        "simulated": simulated,
    }


@router.get("/status")
async def get_paypal_status():
    """Diagnóstico: verifica contra PayPal (OAuth) que las credenciales configuradas funcionan."""
    return await paypal_service.check_connection()


@router.post("/create-order")
async def create_paypal_order(
    payload: PayPalOrderCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Crea una orden de pago en PayPal con conversión de BOB a USD."""
    if payload.amount_bob <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El monto a pagar debe ser mayor a 0 Bs.",
        )

    ref_id = payload.reference_id or f"USER-{current_user.id}"
    order_data = await paypal_service.create_order(
        amount_bob=payload.amount_bob,
        reference_id=ref_id,
        description=payload.description or "Pago FashionStore",
        customer_email=current_user.email,
    )
    return order_data


@router.post("/capture-order")
async def capture_paypal_order(
    payload: PayPalOrderCaptureRequest,
    current_user: User = Depends(get_current_user),
):
    """Captura los fondos de una orden aprobada por el comprador en PayPal."""
    if not payload.paypal_order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere el ID de la orden de PayPal.",
        )

    capture_data = await paypal_service.capture_order(payload.paypal_order_id)
    if capture_data.get("status") not in ("COMPLETED", "APPROVED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo capturar el pago en PayPal. Estado: "
            + str(capture_data.get("status")),
        )
    return capture_data
