"""Servicio de integración con la Pasarela de Pagos PayPal (REST API v2).

Crea y captura órdenes en PayPal (sandbox o live) con conversión BOB -> USD.

Modo simulación: solo cuando NO hay credenciales reales configuradas (valores vacíos o
de ejemplo con "demo"/"test"). Con credenciales reales, cualquier fallo de PayPal se
reporta como error: nunca se fabrica un pago aprobado.
"""
import uuid
import base64
import logging
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger("paypal_service")

SIMULATED_ORDER_PREFIX = "PAYPAL-SIM-"
PAYPAL_UNAVAILABLE = "No se pudo procesar el pago con PayPal. Intenta nuevamente en unos minutos."


class PayPalService:
    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.base_url = settings.paypal_api_base
        self.exchange_rate = settings.PAYPAL_EXCHANGE_RATE_BOB_USD

    def bob_to_usd(self, amount_bob: float) -> float:
        """Convierte monto en Bolivianos a Dólares Estadounidenses con 2 decimales."""
        if not self.exchange_rate or self.exchange_rate <= 0:
            return round(amount_bob / 6.96, 2)
        return round(float(amount_bob) / self.exchange_rate, 2)

    def is_simulation(self) -> bool:
        """True si no hay credenciales reales de PayPal (entorno académico sin cuenta sandbox)."""
        cid = (self.client_id or "").lower()
        secret = (self.client_secret or "").lower()
        return not cid or not secret or "demo" in cid or "test" in cid or "demo" in secret

    def _basic_auth_header(self) -> Dict[str, str]:
        encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        return {"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"}

    async def get_access_token(self) -> str:
        """Obtiene token OAuth 2.0 de PayPal. Lanza 502 si PayPal no responde correctamente."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers=self._basic_auth_header(),
                    data={"grant_type": "client_credentials"},
                )
        except httpx.HTTPError as exc:
            logger.error("Error conectando con PayPal OAuth: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)
        if resp.status_code != 200:
            logger.error("PayPal OAuth falló (%s): %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)
        return resp.json()["access_token"]

    async def check_connection(self) -> Dict[str, Any]:
        """Comprueba la conexión real con PayPal pidiendo un token OAuth.

        Sirve para demostrar (y diagnosticar) que las credenciales sandbox son válidas
        sin crear ninguna orden. Nunca expone el token ni el secret.
        """
        status = {"mode": settings.PAYPAL_MODE, "api_base": self.base_url, "simulated": self.is_simulation()}
        if self.is_simulation():
            return {**status, "connected": False, "detail": "Sin credenciales de PayPal: modo simulación."}
        try:
            await self.get_access_token()
        except HTTPException:
            return {**status, "connected": False, "detail": "PayPal rechazó las credenciales o no respondió."}
        return {**status, "connected": True, "detail": "Conexión OAuth con PayPal establecida."}

    async def create_order(
        self,
        amount_bob: float,
        reference_id: str,
        description: str = "Pago en FashionStore",
        customer_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Crea una orden en PayPal (intent: CAPTURE). Retorna el order_id y approve_url."""
        amount_usd = self.bob_to_usd(amount_bob)
        base = {
            "amount_bob": amount_bob,
            "amount_usd": amount_usd,
            "currency": "USD",
            "exchange_rate": self.exchange_rate,
            "simulated": self.is_simulation(),
        }

        if self.is_simulation():
            sim_id = f"{SIMULATED_ORDER_PREFIX}{uuid.uuid4().hex[:10].upper()}"
            return {**base, "id": sim_id, "status": "CREATED", "approve_url": None}

        token = await self.get_access_token()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": reference_id,
                    "description": description[:120],
                    "amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"},
                }
            ],
            "application_context": {
                "brand_name": "FashionStore",
                "user_action": "PAY_NOW",
                # Retiro/entrega en sucursal: PayPal no debe pedir dirección de envío.
                "shipping_preference": "NO_SHIPPING",
                "return_url": f"{settings.FRONTEND_URL}/store/checkout/success",
                "cancel_url": f"{settings.FRONTEND_URL}/store/checkout/cancel",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v2/checkout/orders",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.error("Excepción en create_order de PayPal: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        data = resp.json()
        if resp.status_code not in (200, 201):
            logger.error("Error creando orden PayPal (%s): %s", resp.status_code, data)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        approve_url = next((l.get("href") for l in data.get("links", []) if l.get("rel") == "approve"), None)
        return {**base, "id": data.get("id"), "status": data.get("status"), "approve_url": approve_url}

    async def capture_order(self, paypal_order_id: str) -> Dict[str, Any]:
        """Captura los fondos de una orden aprobada por el comprador."""
        if self.is_simulation():
            if not paypal_order_id.startswith(SIMULATED_ORDER_PREFIX):
                raise HTTPException(status_code=400, detail="Orden de PayPal no válida.")
            capture_id = f"CAP-SIM-{uuid.uuid4().hex[:12].upper()}"
            return {
                "id": paypal_order_id,
                "status": "COMPLETED",
                "capture_id": capture_id,
                "payer": {"payer_id": "SANDBOX-SIM", "email_address": None},
                "gateway_reference": f"PAYPAL:{capture_id}",
                "simulated": True,
            }

        token = await self.get_access_token()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v2/checkout/orders/{paypal_order_id}/capture",
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json={},
                )
        except httpx.HTTPError as exc:
            logger.error("Excepción en capture_order de PayPal: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        data = resp.json()
        if resp.status_code not in (200, 201) or data.get("status") != "COMPLETED":
            logger.warning("Captura PayPal rechazada (%s): %s", resp.status_code, data)
            raise HTTPException(status_code=402, detail="PayPal no aprobó el pago. Verifica tu cuenta o intenta otro medio.")

        purchase_units = data.get("purchase_units", [])
        captures = purchase_units[0].get("payments", {}).get("captures", []) if purchase_units else []
        capture_id = captures[0].get("id") if captures else paypal_order_id
        return {
            "id": data.get("id"),
            "status": "COMPLETED",
            "capture_id": capture_id,
            "payer": data.get("payer", {}),
            "gateway_reference": f"PAYPAL:{capture_id}",
            "simulated": False,
        }

    def verify_completed_order(self, paypal_order_id: str, expected_amount_bob: float) -> None:
        """Comprueba en PayPal (lado servidor) que la orden esté cobrada por el monto esperado.

        Se usa en el checkout para no registrar como pagado un pedido solo porque el cliente
        envió un ID de orden. Lanza HTTPException si el pago no es válido.
        """
        if self.is_simulation():
            if not paypal_order_id.startswith(SIMULATED_ORDER_PREFIX):
                raise HTTPException(status_code=400, detail="Orden de PayPal no válida.")
            return

        try:
            with httpx.Client(timeout=15.0) as client:
                token_resp = client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers=self._basic_auth_header(),
                    data={"grant_type": "client_credentials"},
                )
                if token_resp.status_code != 200:
                    raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)
                resp = client.get(
                    f"{self.base_url}/v2/checkout/orders/{paypal_order_id}",
                    headers={"Authorization": f"Bearer {token_resp.json()['access_token']}"},
                )
        except httpx.HTTPError as exc:
            logger.error("Error verificando orden PayPal: %s", exc)
            raise HTTPException(status_code=502, detail=PAYPAL_UNAVAILABLE)

        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="La orden de PayPal no existe.")
        data = resp.json()
        if data.get("status") != "COMPLETED":
            raise HTTPException(status_code=402, detail="El pago de PayPal no está completado.")
        units = data.get("purchase_units") or [{}]
        paid_usd = float(units[0].get("amount", {}).get("value", 0))
        if paid_usd + 0.01 < self.bob_to_usd(expected_amount_bob):
            raise HTTPException(status_code=402, detail="El monto pagado en PayPal no cubre el total del pedido.")


paypal_service = PayPalService()
