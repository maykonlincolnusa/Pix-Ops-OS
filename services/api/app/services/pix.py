import base64
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PaymentIntent, PixCharge, PixChargeStatus, Sale
from app.providers.registry import provider_registry
from app.schemas.pix import PixChargeCreate


def build_qr_preview_base64(qr_text: str) -> str:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='360' height='360' viewBox='0 0 360 360'>"
        "<rect width='100%' height='100%' fill='#F4F7FB'/>"
        "<rect x='20' y='20' width='320' height='320' fill='#0B1220' rx='16'/>"
        "<text x='32' y='48' font-family='monospace' font-size='12' fill='#7EE787'>PIX QR</text>"
        f"<text x='32' y='74' font-family='monospace' font-size='10' fill='#D9E1EC'>{qr_text[:120]}</text>"
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"


def create_pix_charge(
    db: Session,
    data: PixChargeCreate,
    *,
    provider_name: str = "mock_pix",
) -> tuple[PixCharge, PaymentIntent]:
    sale = db.scalar(
        select(Sale).where(
            Sale.id == data.sale_id,
            Sale.company_id == data.company_id,
            Sale.tenant_id == data.tenant_id,
        )
    )
    if not sale:
        raise ValueError("Sale not found for this tenant/company.")

    existing = db.scalar(select(PixCharge).where(PixCharge.sale_id == sale.id))
    if existing:
        raise ValueError("This sale already has a Pix charge.")

    payment_intent = db.scalar(select(PaymentIntent).where(PaymentIntent.sale_id == sale.id))
    if not payment_intent:
        payment_intent = PaymentIntent(
            tenant_id=sale.tenant_id,
            sale_id=sale.id,
            method="pix",
            provider=provider_name,
            amount=sale.expected_amount_cents / 100,
            expected_amount=sale.expected_amount_cents / 100,
            status="awaiting_payment",
        )
        db.add(payment_intent)
        db.flush()

    provider = provider_registry.get(provider_name)
    provider_charge = provider.create_pix_charge(
        {
            "pix_key": data.pix_key,
            "amount_cents": sale.expected_amount_cents,
            "expires_in_minutes": data.expires_in_minutes,
        }
    )
    payment_intent.provider = provider_name
    payment_intent.status = "awaiting_payment"
    payment_intent.expires_at = datetime.fromisoformat(provider_charge["expires_at"])
    db.add(payment_intent)

    qr_text = provider_charge.get("emv_payload", "")
    charge = PixCharge(
        tenant_id=sale.tenant_id,
        company_id=sale.company_id,
        sale_id=sale.id,
        payment_intent_id=payment_intent.id,
        txid=provider_charge["txid"],
        pix_key=data.pix_key,
        emv_payload=provider_charge.get("emv_payload"),
        qr_code_url=provider_charge.get("qr_code_url"),
        location_id=provider_charge.get("location_id"),
        provider_charge_id=provider_charge.get("provider_charge_id"),
        amount=sale.expected_amount_cents / 100,
        amount_cents=sale.expected_amount_cents,
        payer_name=data.payer_name,
        qr_code_text=qr_text,
        qr_code_base64=build_qr_preview_base64(qr_text),
        status=PixChargeStatus.CREATED.value,
        expires_at=payment_intent.expires_at,
    )
    db.add(charge)
    db.flush()
    return charge, payment_intent
