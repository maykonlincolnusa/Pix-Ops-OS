import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PixCharge, PixChargeStatus, Sale
from app.schemas.pix import PixChargeCreate


def generate_txid() -> str:
    return uuid4().hex[:30].upper()


def build_qr_payload(*, txid: str, pix_key: str, amount_cents: int, merchant_name: str = "PIXOPS OS") -> str:
    amount = f"{amount_cents / 100:.2f}"
    return (
        "000201"
        "26360014BR.GOV.BCB.PIX01"
        f"{len(pix_key):02d}{pix_key}"
        "52040000"
        "5303986"
        f"540{len(amount):02d}{amount}"
        "5802BR"
        f"5913{merchant_name[:13].ljust(13)}"
        "6008SAOPAULO"
        f"62070503***6304{txid[-4:]}"
    )


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


def create_pix_charge(db: Session, data: PixChargeCreate) -> PixCharge:
    sale = db.scalar(
        select(Sale).where(Sale.id == data.sale_id, Sale.company_id == data.company_id)
    )
    if not sale:
        raise ValueError("Sale not found for this company.")

    existing = db.scalar(select(PixCharge).where(PixCharge.sale_id == sale.id))
    if existing:
        raise ValueError("This sale already has a Pix charge.")

    txid = generate_txid()
    qr_text = build_qr_payload(
        txid=txid,
        pix_key=data.pix_key,
        amount_cents=sale.expected_amount_cents,
    )
    charge = PixCharge(
        company_id=data.company_id,
        sale_id=sale.id,
        txid=txid,
        pix_key=data.pix_key,
        amount_cents=sale.expected_amount_cents,
        payer_name=data.payer_name,
        qr_code_text=qr_text,
        qr_code_base64=build_qr_preview_base64(qr_text),
        status=PixChargeStatus.CREATED.value,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=data.expires_in_minutes),
    )
    db.add(charge)
    db.flush()
    return charge
