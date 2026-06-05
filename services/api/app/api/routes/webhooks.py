from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agentic.router import run_agent_router
from app.api.deps import DBSession, MasterApiKeyDep
from app.core.config import get_settings
from app.db.models import WebhookEvent
from app.providers.registry import provider_registry
from app.services.event_catalog import EventType
from app.services.ledger import append_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _validate_webhook_ip(request: Request) -> None:
    settings = get_settings()
    allowed_ips = settings.allowed_webhook_ips
    if not allowed_ips:
        return
    remote_ip = request.client.host if request.client else ""
    if remote_ip not in allowed_ips:
        raise HTTPException(status_code=403, detail="Webhook IP not allowed.")


def _ingest_webhook(
    *,
    db: DBSession,
    tenant_id: str,
    provider_name: str,
    channel: str,
    payload: dict,
    raw_payload: dict,
    signature_valid: bool,
) -> WebhookEvent:
    external_event_id = payload.get("external_event_id") or payload.get("event_id")
    if not external_event_id:
        raise HTTPException(status_code=400, detail="Webhook payload missing external_event_id.")

    webhook = WebhookEvent(
        tenant_id=tenant_id,
        provider=provider_name,
        event_type=payload.get("event_type", f"{channel}.event.received"),
        external_event_id=str(external_event_id),
        signature_valid=signature_valid,
        raw_payload=raw_payload,
        normalized_payload=payload,
        status="received",
    )
    db.add(webhook)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.tenant_id == tenant_id,
                WebhookEvent.provider == provider_name,
                WebhookEvent.external_event_id == str(external_event_id),
            )
        )
        if not existing:
            raise
        append_event(
            db,
            tenant_id=tenant_id,
            aggregate_type="webhook",
            aggregate_id=str(external_event_id),
            event_type=EventType.WEBHOOK_DUPLICATED.value,
            payload={"provider": provider_name, "channel": channel},
            source="webhook_receiver",
            provider=provider_name,
            idempotency_key=str(external_event_id),
        )
        existing.status = "duplicated"
        db.add(existing)
        db.commit()
        return existing

    append_event(
        db,
        tenant_id=tenant_id,
        aggregate_type="webhook",
        aggregate_id=str(webhook.id),
        event_type=EventType.WEBHOOK_RECEIVED.value,
        payload={"provider": provider_name, "channel": channel, "external_event_id": str(external_event_id)},
        source="webhook_receiver",
        provider=provider_name,
        idempotency_key=str(external_event_id),
    )
    return webhook


@router.post("/{provider}/pix", status_code=status.HTTP_202_ACCEPTED)
async def receive_pix_webhook(
    _: MasterApiKeyDep,
    provider: str,
    request: Request,
    db: DBSession,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict:
    raw_body = await request.body()
    raw_json = await request.json()
    _validate_webhook_ip(request)

    adapter = provider_registry.get(provider)
    signature_valid = adapter.verify_webhook_signature(
        raw_body,
        x_signature,
        {k.lower(): v for k, v in request.headers.items()},
    )

    normalized = adapter.parse_webhook(raw_json, "pix")
    webhook = _ingest_webhook(
        db=db,
        tenant_id=x_tenant_id,
        provider_name=provider,
        channel="pix",
        payload=normalized,
        raw_payload=raw_json,
        signature_valid=signature_valid,
    )
    if webhook.status == "duplicated":
        final_state = run_agent_router(
            db,
            tenant_id=x_tenant_id,
            event_type=EventType.WEBHOOK_RECEIVED.value,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            payload={
                **normalized,
                "signature_valid": signature_valid,
                "external_event_id": webhook.external_event_id,
                "duplicate": True,
            },
            metadata={
                "tenant_id": x_tenant_id,
                "provider": provider,
                "channel": "pix",
                "environment": "mvp",
            },
            correlation_id=normalized.get("txid") or webhook.external_event_id,
            causation_id=webhook.external_event_id,
            provider=provider,
            source_event_id=webhook.external_event_id,
        )
        db.commit()
        return {
            "status": "duplicate_event_ignored",
            "webhook_id": webhook.id,
            "agent_status": final_state.get("status"),
            "correlation_id": final_state.get("correlation_id"),
        }

    if signature_valid:
        append_event(
            db,
            tenant_id=x_tenant_id,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            event_type=EventType.WEBHOOK_SIGNATURE_VALIDATED.value,
            payload={"provider": provider, "external_event_id": webhook.external_event_id},
            source="webhook_receiver",
            provider=provider,
        )
    else:
        webhook.status = "failed_signature"
        webhook.processed_at = datetime.now(timezone.utc)
        append_event(
            db,
            tenant_id=x_tenant_id,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            event_type=EventType.WEBHOOK_SIGNATURE_FAILED.value,
            payload={"provider": provider, "external_event_id": webhook.external_event_id},
            source="webhook_receiver",
            provider=provider,
        )
        final_state = run_agent_router(
            db,
            tenant_id=x_tenant_id,
            event_type=EventType.WEBHOOK_RECEIVED.value,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            payload={
                **normalized,
                "signature_valid": False,
                "external_event_id": webhook.external_event_id,
            },
            metadata={
                "tenant_id": x_tenant_id,
                "provider": provider,
                "channel": "pix",
                "environment": "mvp",
            },
            correlation_id=normalized.get("txid") or webhook.external_event_id,
            causation_id=webhook.external_event_id,
            provider=provider,
            source_event_id=webhook.external_event_id,
        )
        db.commit()
        return {
            "status": "invalid_signature",
            "webhook_id": webhook.id,
            "agent_status": final_state.get("status"),
            "correlation_id": final_state.get("correlation_id"),
        }

    final_state = run_agent_router(
        db,
        tenant_id=x_tenant_id,
        event_type=EventType.WEBHOOK_RECEIVED.value,
        aggregate_type="webhook",
        aggregate_id=webhook.id,
        payload={
            **normalized,
            "signature_valid": True,
            "external_event_id": webhook.external_event_id,
        },
        metadata={
            "tenant_id": x_tenant_id,
            "provider": provider,
            "channel": "pix",
            "environment": "mvp",
        },
        correlation_id=normalized.get("txid") or webhook.external_event_id,
        causation_id=webhook.external_event_id,
        provider=provider,
        source_event_id=webhook.external_event_id,
    )
    webhook.status = "processed"
    webhook.processed_at = datetime.now(timezone.utc)
    append_event(
        db,
        tenant_id=x_tenant_id,
        aggregate_type="webhook",
        aggregate_id=str(webhook.id),
        event_type=EventType.WEBHOOK_PROCESSED.value,
        payload={"provider": provider, "channel": "pix", "external_event_id": webhook.external_event_id},
        source="webhook_processor",
        provider=provider,
    )
    db.commit()
    return {
        "status": "accepted",
        "webhook_id": webhook.id,
        "agent_status": final_state.get("status"),
        "correlation_id": final_state.get("correlation_id"),
    }


@router.post("/{provider}/card", status_code=status.HTTP_202_ACCEPTED)
async def receive_card_webhook(
    _: MasterApiKeyDep,
    provider: str,
    request: Request,
    db: DBSession,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict:
    raw_body = await request.body()
    raw_json = await request.json()
    _validate_webhook_ip(request)
    adapter = provider_registry.get(provider)
    signature_valid = adapter.verify_webhook_signature(
        raw_body,
        x_signature,
        {k.lower(): v for k, v in request.headers.items()},
    )
    normalized = adapter.parse_webhook(raw_json, "card")
    webhook = _ingest_webhook(
        db=db,
        tenant_id=x_tenant_id,
        provider_name=provider,
        channel="card",
        payload=normalized,
        raw_payload=raw_json,
        signature_valid=signature_valid,
    )
    if webhook.status == "duplicated":
        return {"status": "duplicate_event_ignored", "webhook_id": webhook.id}
    if not signature_valid:
        webhook.status = "failed_signature"
        webhook.processed_at = datetime.now(timezone.utc)
        append_event(
            db,
            tenant_id=x_tenant_id,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            event_type=EventType.WEBHOOK_SIGNATURE_FAILED.value,
            payload={"provider": provider, "channel": "card", "external_event_id": webhook.external_event_id},
            source="webhook_receiver",
            provider=provider,
        )
        run_agent_router(
            db,
            tenant_id=x_tenant_id,
            event_type=EventType.WEBHOOK_RECEIVED.value,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            payload={
                **normalized,
                "signature_valid": False,
                "external_event_id": webhook.external_event_id,
                "channel": "card",
            },
            metadata={"tenant_id": x_tenant_id, "provider": provider, "channel": "card", "environment": "mvp"},
            correlation_id=normalized.get("external_event_id") or webhook.external_event_id,
            causation_id=webhook.external_event_id,
            provider=provider,
            source_event_id=webhook.external_event_id,
        )
        db.commit()
        return {"status": "invalid_signature", "webhook_id": webhook.id}
    run_agent_router(
        db,
        tenant_id=x_tenant_id,
        event_type=EventType.WEBHOOK_RECEIVED.value,
        aggregate_type="webhook",
        aggregate_id=webhook.id,
        payload={
            **normalized,
            "signature_valid": signature_valid,
            "external_event_id": webhook.external_event_id,
            "channel": "card",
        },
        metadata={"tenant_id": x_tenant_id, "provider": provider, "channel": "card", "environment": "mvp"},
        correlation_id=normalized.get("external_event_id") or webhook.external_event_id,
        causation_id=webhook.external_event_id,
        provider=provider,
        source_event_id=webhook.external_event_id,
    )
    webhook.status = "processed"
    webhook.processed_at = datetime.now(timezone.utc)
    append_event(
        db,
        tenant_id=x_tenant_id,
        aggregate_type="webhook",
        aggregate_id=str(webhook.id),
        event_type=EventType.WEBHOOK_PROCESSED.value,
        payload={"provider": provider, "channel": "card", "external_event_id": webhook.external_event_id},
        source="webhook_processor",
        provider=provider,
    )
    db.commit()
    return {"status": "accepted", "webhook_id": webhook.id}


@router.post("/{provider}/bank", status_code=status.HTTP_202_ACCEPTED)
async def receive_bank_webhook(
    _: MasterApiKeyDep,
    provider: str,
    request: Request,
    db: DBSession,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict:
    raw_body = await request.body()
    raw_json = await request.json()
    _validate_webhook_ip(request)
    adapter = provider_registry.get(provider)
    signature_valid = adapter.verify_webhook_signature(
        raw_body,
        x_signature,
        {k.lower(): v for k, v in request.headers.items()},
    )
    normalized = adapter.parse_webhook(raw_json, "bank")
    webhook = _ingest_webhook(
        db=db,
        tenant_id=x_tenant_id,
        provider_name=provider,
        channel="bank",
        payload=normalized,
        raw_payload=raw_json,
        signature_valid=signature_valid,
    )
    if webhook.status == "duplicated":
        return {"status": "duplicate_event_ignored", "webhook_id": webhook.id}
    if not signature_valid:
        webhook.status = "failed_signature"
        webhook.processed_at = datetime.now(timezone.utc)
        append_event(
            db,
            tenant_id=x_tenant_id,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            event_type=EventType.WEBHOOK_SIGNATURE_FAILED.value,
            payload={"provider": provider, "channel": "bank", "external_event_id": webhook.external_event_id},
            source="webhook_receiver",
            provider=provider,
        )
        run_agent_router(
            db,
            tenant_id=x_tenant_id,
            event_type=EventType.WEBHOOK_RECEIVED.value,
            aggregate_type="webhook",
            aggregate_id=webhook.id,
            payload={
                **normalized,
                "signature_valid": False,
                "external_event_id": webhook.external_event_id,
                "channel": "bank",
            },
            metadata={"tenant_id": x_tenant_id, "provider": provider, "channel": "bank", "environment": "mvp"},
            correlation_id=normalized.get("external_event_id") or webhook.external_event_id,
            causation_id=webhook.external_event_id,
            provider=provider,
            source_event_id=webhook.external_event_id,
        )
        db.commit()
        return {"status": "invalid_signature", "webhook_id": webhook.id}
    run_agent_router(
        db,
        tenant_id=x_tenant_id,
        event_type=EventType.WEBHOOK_RECEIVED.value,
        aggregate_type="webhook",
        aggregate_id=webhook.id,
        payload={
            **normalized,
            "signature_valid": signature_valid,
            "external_event_id": webhook.external_event_id,
            "channel": "bank",
        },
        metadata={"tenant_id": x_tenant_id, "provider": provider, "channel": "bank", "environment": "mvp"},
        correlation_id=normalized.get("external_event_id") or webhook.external_event_id,
        causation_id=webhook.external_event_id,
        provider=provider,
        source_event_id=webhook.external_event_id,
    )
    webhook.status = "processed"
    webhook.processed_at = datetime.now(timezone.utc)
    append_event(
        db,
        tenant_id=x_tenant_id,
        aggregate_type="webhook",
        aggregate_id=str(webhook.id),
        event_type=EventType.WEBHOOK_PROCESSED.value,
        payload={"provider": provider, "channel": "bank", "external_event_id": webhook.external_event_id},
        source="webhook_processor",
        provider=provider,
    )
    db.commit()
    return {"status": "accepted", "webhook_id": webhook.id}


@router.get("/events")
def list_webhook_events(_: MasterApiKeyDep, tenant_id: str, db: DBSession, limit: int = 100) -> list[WebhookEvent]:
    return db.scalars(
        select(WebhookEvent)
        .where(WebhookEvent.tenant_id == tenant_id)
        .order_by(WebhookEvent.received_at.desc())
        .limit(limit)
    ).all()
