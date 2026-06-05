from __future__ import annotations

import time
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agentic.state import AgenticState
from app.agentic.store import (
    create_agent_task,
    create_manual_review_case,
    enqueue_notification,
    mark_notification_sent,
    resolve_agent_task,
    save_agent_run,
)
from app.core.config import get_settings
from app.db.models import (
    AgentTask,
    FraudSeverity,
    PaymentIntent,
    PaymentIntentStatus,
    PixCharge,
    PixChargeStatus,
    ReconciliationRecord,
    ReconciliationStatus,
    Sale,
    SaleStatus,
)
from app.services.event_catalog import EventType
from app.services.fraud import create_fraud_alert
from app.services.ledger import append_event, create_double_entry


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _route_from_event(event_type: str) -> str:
    mapping = {
        EventType.WEBHOOK_RECEIVED.value: "provider_verification",
        EventType.WEBHOOK_VERIFIED.value: "payment_state",
        EventType.PAYMENT_STATE_CHECKED.value: "reconciliation",
        "reconciliation.matched": "ledger",
        EventType.RECONCILIATION_FAILED.value: "fraud_defense",
        EventType.PAYMENT_AWAITING_CONFIRMATION.value: "timeout_watchdog",
        EventType.PAYMENT_TIMEOUT_DETECTED.value: "notification",
        EventType.FRAUD_ALERT_CREATED.value: "human_review",
        EventType.LEDGER_ENTRY_CREATED.value: "notification",
        EventType.CASHIER_SESSION_CLOSED.value: "report",
    }
    return mapping.get(event_type, "report")


def _db_resolve_payment_context(db: Session, state: AgenticState) -> AgenticState:
    payload = state.get("payload", {})
    txid = payload.get("txid")
    payment_intent_id = state.get("payment_intent_id") or payload.get("payment_intent_id")
    sale_id = state.get("sale_id") or payload.get("sale_id")

    if not payment_intent_id and txid:
        charge = db.scalar(
            select(PixCharge).where(PixCharge.tenant_id == state["tenant_id"], PixCharge.txid == txid)
        )
        if charge:
            payment_intent_id = charge.payment_intent_id
            sale_id = sale_id or charge.sale_id
            state["aggregate_id"] = charge.id

    if payment_intent_id:
        state["payment_intent_id"] = payment_intent_id
    if sale_id:
        state["sale_id"] = sale_id
    return state


def _record_agent_node(
    db: Session,
    *,
    state: AgenticState,
    agent_name: str,
    input_event_id: str | None,
    output_event_id: str | None,
    decision: str,
    reasoning_summary: str,
    confidence_score: float,
    status: str,
    duration_ms: int,
) -> None:
    save_agent_run(
        db,
        tenant_id=state["tenant_id"],
        correlation_id=state["correlation_id"],
        causation_id=state.get("causation_id"),
        trace_id=state.get("trace_id"),
        agent_name=agent_name,
        input_event_id=input_event_id,
        output_event_id=output_event_id,
        status=status,
        decision=decision,
        reasoning_summary=reasoning_summary,
        confidence_score=confidence_score,
        langsmith_trace_id=state.get("trace_id"),
        duration_ms=duration_ms,
        metadata={
            "aggregate_id": state.get("aggregate_id"),
            "aggregate_type": state.get("aggregate_type"),
            "event_type": state.get("event_type"),
        },
    )


def _run_node(db: Session, state: AgenticState, agent_name: str, logic):
    started = time.perf_counter()
    input_event_id = state.get("source_event_id")
    updates: AgenticState = logic(state)
    duration_ms = int((time.perf_counter() - started) * 1000)
    decision = updates.get("decision", "no_decision")
    reasoning_summary = updates.get("reasoning_summary", "")
    confidence_score = float(updates.get("confidence_score", 0.5))
    status = updates.get("status", "ok")
    output_event_id = updates.get("output_event_id")
    _record_agent_node(
        db,
        state=updates,
        agent_name=agent_name,
        input_event_id=input_event_id,
        output_event_id=output_event_id,
        decision=decision,
        reasoning_summary=reasoning_summary,
        confidence_score=confidence_score,
        status=status,
        duration_ms=duration_ms,
    )
    decisions = list(updates.get("decisions", []))
    decisions.append(
        {
            "agent": agent_name,
            "decision": decision,
            "status": status,
            "confidence_score": confidence_score,
        }
    )
    updates["decisions"] = decisions
    return updates


def build_agent_graph(db: Session):
    settings = get_settings()

    def event_intake(state: AgenticState) -> AgenticState:
        state = _db_resolve_payment_context(db, state)
        payload = state.get("payload", {})
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type=state.get("aggregate_type", "payment"),
            aggregate_id=state.get("aggregate_id", state.get("payment_intent_id") or "unknown"),
            event_type=EventType.EVENT_CLASSIFIED.value,
            payload={
                "incoming_event_type": state["event_type"],
                "provider": state.get("provider"),
                "payment_intent_id": state.get("payment_intent_id"),
                "sale_id": state.get("sale_id"),
                "external_event_id": payload.get("external_event_id"),
            },
            source="agentic.event_intake",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("causation_id"),
        )
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.EVENT_CLASSIFIED.value
        state["next_route"] = _route_from_event(state["event_type"])
        state["decision"] = f"classified:{state['next_route']}"
        state["reasoning_summary"] = "Incoming event classified and routed."
        state["confidence_score"] = 0.98
        state["status"] = "ok"
        return state

    def provider_verification(state: AgenticState) -> AgenticState:
        payload = state.get("payload", {})
        signature_valid = bool(payload.get("signature_valid", False))
        external_event_id = payload.get("external_event_id")
        duplicate_hint = bool(payload.get("duplicate", False))

        if not signature_valid or not external_event_id:
            event = append_event(
                db,
                tenant_id=state["tenant_id"],
                aggregate_type="webhook",
                aggregate_id=state.get("aggregate_id", external_event_id or "unknown"),
                event_type=EventType.WEBHOOK_REJECTED.value,
                payload={
                    "signature_valid": signature_valid,
                    "external_event_id": external_event_id,
                    "reason": "invalid_signature_or_missing_external_id",
                },
                source="agentic.provider_verification",
                provider=state.get("provider"),
                correlation_id=state["correlation_id"],
                causation_id=state.get("source_event_id"),
            )
            state["output_event_id"] = event.event_id
            state["output_event_type"] = EventType.WEBHOOK_REJECTED.value
            state["next_route"] = "fraud_defense"
            state["decision"] = "webhook_rejected"
            state["reasoning_summary"] = "Signature validation or external event id failed."
            state["confidence_score"] = 0.99
            state["status"] = "blocked"
            return state

        if duplicate_hint:
            event = append_event(
                db,
                tenant_id=state["tenant_id"],
                aggregate_type="webhook",
                aggregate_id=state.get("aggregate_id", external_event_id or "duplicate"),
                event_type=EventType.PIX_PAYMENT_DUPLICATE_WEBHOOK_IGNORED.value,
                payload={
                    "external_event_id": external_event_id,
                    "provider": state.get("provider"),
                    "reason": "duplicate_event_ignored",
                },
                source="agentic.provider_verification",
                provider=state.get("provider"),
                correlation_id=state["correlation_id"],
                causation_id=state.get("source_event_id"),
                idempotency_key=str(external_event_id) if external_event_id else None,
            )
            state["output_event_id"] = event.event_id
            state["output_event_type"] = EventType.PIX_PAYMENT_DUPLICATE_WEBHOOK_IGNORED.value
            state["reconciliation_status"] = ReconciliationStatus.DUPLICATE.value
            state["next_route"] = "notification"
            state["decision"] = "duplicate_ignored"
            state["reasoning_summary"] = "Webhook marked as duplicate by ingestion pipeline."
            state["confidence_score"] = 0.97
            state["status"] = "ok"
            return state

        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="webhook",
            aggregate_id=state.get("aggregate_id", external_event_id),
            event_type=EventType.WEBHOOK_VERIFIED.value,
            payload={
                "signature_valid": True,
                "external_event_id": external_event_id,
                "provider": state.get("provider"),
            },
            source="agentic.provider_verification",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
            idempotency_key=str(external_event_id),
        )
        state["source_event_id"] = event.event_id
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.WEBHOOK_VERIFIED.value
        state["provider_verified"] = True
        state["next_route"] = "payment_state"
        state["decision"] = "webhook_verified"
        state["reasoning_summary"] = "Webhook signature, idempotency and provider identity validated."
        state["confidence_score"] = 0.98
        state["status"] = "ok"
        return state

    def payment_state(state: AgenticState) -> AgenticState:
        state = _db_resolve_payment_context(db, state)
        payment_intent_id = state.get("payment_intent_id")
        payment_status = "not_found"
        if payment_intent_id:
            payment_intent = db.scalar(
                select(PaymentIntent).where(
                    PaymentIntent.tenant_id == state["tenant_id"],
                    PaymentIntent.id == payment_intent_id,
                )
            )
            if payment_intent:
                payment_status = payment_intent.status

        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="payment_intent",
            aggregate_id=payment_intent_id or state.get("aggregate_id", "unknown"),
            event_type=EventType.PAYMENT_STATE_CHECKED.value,
            payload={
                "payment_intent_id": payment_intent_id,
                "status": payment_status,
            },
            source="agentic.payment_state",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        state["source_event_id"] = event.event_id
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.PAYMENT_STATE_CHECKED.value

        if state["event_type"] == EventType.PAYMENT_AWAITING_CONFIRMATION.value:
            state["next_route"] = "timeout_watchdog"
        elif payment_status == "not_found" and state.get("payload", {}).get("txid"):
            state["next_route"] = "reconciliation"
        elif payment_status in {
            PaymentIntentStatus.AWAITING_PAYMENT.value,
            PaymentIntentStatus.CREATED.value,
            PaymentIntentStatus.SUSPICIOUS.value,
        }:
            state["next_route"] = "reconciliation"
        elif payment_status == PaymentIntentStatus.PAID.value:
            state["next_route"] = "notification"
        elif payment_status == PaymentIntentStatus.TIMEOUT.value:
            state["next_route"] = "notification"
        else:
            state["next_route"] = "fraud_defense"
        state["decision"] = f"state_checked:{payment_status}"
        state["reasoning_summary"] = "Payment intent state evaluated without self-confirming payment."
        state["confidence_score"] = 0.96
        state["status"] = "ok"
        return state

    def reconciliation(state: AgenticState) -> AgenticState:
        state = _db_resolve_payment_context(db, state)
        payload = state.get("payload", {})
        received_cents = int(payload.get("amount_cents", 0))
        payment_intent_id = state.get("payment_intent_id")
        sale_id = state.get("sale_id")
        classification = ReconciliationStatus.PENDING.value
        reason = "awaiting_evidence"
        txid = payload.get("txid")
        paid_at = payload.get("paid_at")
        paid_at_dt = _now()
        if isinstance(paid_at, str):
            try:
                paid_at_dt = datetime.fromisoformat(paid_at)
            except ValueError:
                paid_at_dt = _now()

        sale: Sale | None = None
        charge: PixCharge | None = None
        if sale_id:
            sale = db.scalar(select(Sale).where(Sale.tenant_id == state["tenant_id"], Sale.id == sale_id))
        if txid:
            charge = db.scalar(
                select(PixCharge).where(PixCharge.tenant_id == state["tenant_id"], PixCharge.txid == txid)
            )
        if not charge and payment_intent_id:
            charge = db.scalar(
                select(PixCharge).where(
                    PixCharge.tenant_id == state["tenant_id"],
                    PixCharge.payment_intent_id == payment_intent_id,
                )
            )
        if charge and not sale:
            sale = db.scalar(select(Sale).where(Sale.tenant_id == state["tenant_id"], Sale.id == charge.sale_id))
            state["sale_id"] = charge.sale_id

        payment_intent: PaymentIntent | None = None
        if payment_intent_id:
            payment_intent = db.scalar(
                select(PaymentIntent).where(
                    PaymentIntent.tenant_id == state["tenant_id"],
                    PaymentIntent.id == payment_intent_id,
                )
            )

        if charge and charge.status == PixChargeStatus.CONFIRMED.value:
            classification = ReconciliationStatus.DUPLICATE.value
            reason = "duplicate_event_ignored"
        elif not sale:
            classification = ReconciliationStatus.ORPHAN_PAYMENT.value
            reason = "sale_not_found"
        elif charge and paid_at_dt > charge.expires_at:
            classification = ReconciliationStatus.LATE_PAYMENT.value
            reason = "payment_received_after_expiration"
        else:
            expected = int(sale.expected_amount_cents)
            if received_cents <= 0:
                classification = ReconciliationStatus.PENDING.value
                reason = "missing_received_amount"
            elif received_cents == expected:
                classification = ReconciliationStatus.MATCHED.value
                reason = "txid_and_amount_match"
            elif received_cents < expected:
                classification = ReconciliationStatus.UNDERPAID.value
                reason = "amount_mismatch_underpaid"
            elif received_cents > expected:
                classification = ReconciliationStatus.OVERPAID.value
                reason = "amount_mismatch_overpaid"

        if payment_intent:
            payment_intent.received_amount = received_cents / 100 if received_cents > 0 else payment_intent.received_amount
            payment_intent.paid_at = paid_at_dt
            if classification == ReconciliationStatus.MATCHED.value:
                payment_intent.status = PaymentIntentStatus.RECONCILING.value
            elif classification != ReconciliationStatus.DUPLICATE.value:
                payment_intent.status = PaymentIntentStatus.MANUAL_REVIEW_REQUIRED.value
            db.add(payment_intent)

        if charge and classification not in {ReconciliationStatus.DUPLICATE.value, ReconciliationStatus.ORPHAN_PAYMENT.value}:
            charge.confirmed_amount_cents = received_cents if received_cents > 0 else charge.confirmed_amount_cents
            charge.end_to_end_id = payload.get("end_to_end_id", charge.end_to_end_id)
            charge.confirmed_at = paid_at_dt
            charge.paid_at = paid_at_dt
            charge.status = (
                PixChargeStatus.CONFIRMED.value
                if classification == ReconciliationStatus.MATCHED.value
                else charge.status
            )
            db.add(charge)

        if sale and classification != ReconciliationStatus.MATCHED.value and classification != ReconciliationStatus.DUPLICATE.value:
            sale.status = SaleStatus.MANUAL_REVIEW_REQUIRED.value
            db.add(sale)

        record = ReconciliationRecord(
            tenant_id=state["tenant_id"],
            company_id=sale.company_id if sale else payload.get("company_id"),
            store_id=sale.store_id if sale else None,
            sale_id=sale.id if sale else None,
            txid=txid,
            expected_amount_cents=sale.expected_amount_cents if sale else None,
            received_amount_cents=received_cents if received_cents > 0 else None,
            status=classification,
            reason=reason,
        )
        db.add(record)
        db.flush()

        event_type = "reconciliation.matched" if classification == ReconciliationStatus.MATCHED.value else EventType.RECONCILIATION_FAILED.value
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="payment_intent",
            aggregate_id=payment_intent_id or state.get("aggregate_id", "unknown"),
            event_type=event_type,
            payload={
                "classification": classification,
                "reason": reason,
                "sale_id": state.get("sale_id"),
                "payment_intent_id": payment_intent_id,
                "reconciliation_record_id": record.id,
                "received_amount_cents": received_cents,
                "txid": txid,
            },
            source="agentic.reconciliation",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        state["source_event_id"] = event.event_id
        state["output_event_id"] = event.event_id
        state["output_event_type"] = event_type
        state["reconciliation_status"] = classification
        state["next_route"] = "ledger" if classification == ReconciliationStatus.MATCHED.value else "fraud_defense"
        state["decision"] = f"reconciliation:{classification}"
        state["reasoning_summary"] = reason
        state["confidence_score"] = 0.95
        state["status"] = "ok" if classification == ReconciliationStatus.MATCHED.value else "blocked"
        return state

    def ledger(state: AgenticState) -> AgenticState:
        state = _db_resolve_payment_context(db, state)
        payment_intent_id = state.get("payment_intent_id")
        sale_id = state.get("sale_id")
        payload = state.get("payload", {})
        received_cents = int(payload.get("amount_cents", 0))
        if not state.get("provider_verified"):
            state["next_route"] = "fraud_defense"
            state["decision"] = "ledger_blocked_provider_not_verified"
            state["reasoning_summary"] = "Payment cannot be finalized without verified provider webhook."
            state["confidence_score"] = 0.99
            state["status"] = "blocked"
            return state
        if state.get("reconciliation_status") != ReconciliationStatus.MATCHED.value:
            state["next_route"] = "fraud_defense"
            state["decision"] = "ledger_blocked_not_matched"
            state["reasoning_summary"] = "Ledger creation blocked because reconciliation is not matched."
            state["confidence_score"] = 0.99
            state["status"] = "blocked"
            return state

        payment_intent = None
        sale = None
        if payment_intent_id:
            payment_intent = db.scalar(
                select(PaymentIntent).where(
                    PaymentIntent.tenant_id == state["tenant_id"],
                    PaymentIntent.id == payment_intent_id,
                )
            )
        if sale_id:
            sale = db.scalar(select(Sale).where(Sale.tenant_id == state["tenant_id"], Sale.id == sale_id))
        if not payment_intent or not sale:
            state["next_route"] = "fraud_defense"
            state["decision"] = "ledger_blocked_missing_context"
            state["reasoning_summary"] = "Missing payment intent or sale context."
            state["confidence_score"] = 0.98
            state["status"] = "failed"
            return state

        payment_intent.status = PaymentIntentStatus.PAID.value
        payment_intent.paid_at = _now()
        payment_intent.received_amount = received_cents / 100 if received_cents > 0 else payment_intent.expected_amount
        sale.status = SaleStatus.PAID.value
        sale.paid_at = payment_intent.paid_at
        db.add(payment_intent)
        db.add(sale)

        payment_event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.PAYMENT_INTENT_PAID.value,
            payload={
                "payment_intent_id": payment_intent.id,
                "sale_id": sale.id,
                "amount_cents": received_cents or int(sale.expected_amount_cents),
            },
            source="agentic.ledger",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="sale",
            aggregate_id=sale.id,
            event_type=EventType.SALE_PAID.value,
            payload={"sale_id": sale.id, "payment_intent_id": payment_intent.id},
            source="agentic.ledger",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=payment_event.event_id,
        )
        ledger_event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="ledger",
            aggregate_id=payment_intent.id,
            event_type=EventType.LEDGER_ENTRY_CREATED.value,
            payload={
                "transaction_id": payment_intent.id,
                "amount_cents": received_cents or int(sale.expected_amount_cents),
            },
            source="agentic.ledger",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=payment_event.event_id,
        )
        create_double_entry(
            db,
            tenant_id=state["tenant_id"],
            transaction_id=payment_intent.id,
            amount_cents=received_cents or int(sale.expected_amount_cents),
            currency="BRL",
            provider=state.get("provider") or payment_intent.provider,
            source_event_id=ledger_event.event_id,
            debit_account_id="cash_in_transit",
            credit_account_id="sales_revenue",
        )

        state["output_event_id"] = ledger_event.event_id
        state["output_event_type"] = EventType.LEDGER_ENTRY_CREATED.value
        state["next_route"] = "notification"
        state["decision"] = "ledger_entries_created"
        state["reasoning_summary"] = "Reconciliation matched and provider event validated."
        state["confidence_score"] = 0.99
        state["status"] = "ok"
        return state

    def fraud_defense(state: AgenticState) -> AgenticState:
        payload = state.get("payload", {})
        classification = state.get("reconciliation_status")
        score = 0.2
        severity = FraudSeverity.LOW.value
        category = "operational_risk"
        reason = "general_review"
        if state.get("output_event_type") == EventType.WEBHOOK_REJECTED.value:
            score = 0.95
            severity = FraudSeverity.CRITICAL.value
            category = "webhook_invalid"
            reason = "Webhook signature invalid or external id missing."
        elif classification in {ReconciliationStatus.UNDERPAID.value, ReconciliationStatus.OVERPAID.value}:
            score = 0.9
            severity = FraudSeverity.HIGH.value
            category = "amount_mismatch"
            reason = "Expected and received amounts diverge."
        elif classification == ReconciliationStatus.ORPHAN_PAYMENT.value:
            score = 0.92
            severity = FraudSeverity.HIGH.value
            category = "orphan_payment"
            reason = "Payment arrived without known sale or payment intent."
        elif classification == ReconciliationStatus.DUPLICATE.value:
            score = 0.55
            severity = FraudSeverity.MEDIUM.value
            category = "duplicate_event"
            reason = "Duplicate webhook or duplicated provider event ignored."
        elif classification == ReconciliationStatus.LATE_PAYMENT.value:
            score = 0.7
            severity = FraudSeverity.MEDIUM.value
            category = "late_payment"
            reason = "Payment received after configured expiration window."
        elif state.get("event_type") == EventType.PAYMENT_TIMEOUT_DETECTED.value:
            score = 0.7
            severity = FraudSeverity.MEDIUM.value
            category = "timeout_risk"
            reason = "Payment intent timed out with pending release risk."

        alert = create_fraud_alert(
            db,
            tenant_id=state["tenant_id"],
            severity=FraudSeverity(severity),
            category=category,
            reason=reason,
            related_payment_id=state.get("payment_intent_id"),
            related_sale_id=state.get("sale_id"),
            evidence={
                "score": score,
                "correlation_id": state["correlation_id"],
                "payload": payload,
            },
        )
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="fraud_alert",
            aggregate_id=alert.id,
            event_type=EventType.FRAUD_ALERT_CREATED.value,
            payload={
                "fraud_alert_id": alert.id,
                "severity": severity,
                "category": category,
                "reason": reason,
            },
            source="agentic.fraud_defense",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.FRAUD_ALERT_CREATED.value
        state["risk_severity"] = severity
        state["next_route"] = "human_review"
        state["decision"] = f"risk_scored:{severity}"
        state["reasoning_summary"] = reason
        state["confidence_score"] = 0.93
        state["status"] = "blocked"
        state["payload"]["fraud_alert_id"] = alert.id
        return state

    def timeout_watchdog(state: AgenticState) -> AgenticState:
        state = _db_resolve_payment_context(db, state)
        payment_intent_id = state.get("payment_intent_id")
        if not payment_intent_id:
            state["next_route"] = "report"
            state["decision"] = "watchdog_skipped_missing_payment_intent"
            state["reasoning_summary"] = "No payment intent context available."
            state["confidence_score"] = 0.9
            state["status"] = "failed"
            return state

        payment_intent = db.scalar(
            select(PaymentIntent).where(
                PaymentIntent.tenant_id == state["tenant_id"],
                PaymentIntent.id == payment_intent_id,
            )
        )
        if not payment_intent:
            state["next_route"] = "report"
            state["decision"] = "watchdog_skipped_not_found"
            state["reasoning_summary"] = "Payment intent not found."
            state["confidence_score"] = 0.9
            state["status"] = "failed"
            return state

        now = _now()
        due_at_payload = state.get("payload", {}).get("due_at")
        due_at = payment_intent.expires_at or (now + timedelta(minutes=settings.agent_timeout_minutes))
        if isinstance(due_at_payload, str):
            try:
                due_at = datetime.fromisoformat(due_at_payload)
            except ValueError:
                pass
        existing_pending = db.scalar(
            select(AgentTask).where(
                AgentTask.tenant_id == state["tenant_id"],
                AgentTask.agent_name == "TimeoutWatchdogAgent",
                AgentTask.task_type == "payment_timeout_watch",
                AgentTask.status == "pending",
                AgentTask.correlation_id == state["correlation_id"],
            )
        )
        if not existing_pending:
            create_agent_task(
                db,
                tenant_id=state["tenant_id"],
                agent_name="TimeoutWatchdogAgent",
                task_type="payment_timeout_watch",
                priority="high",
                due_at=due_at,
                payload_json={
                    "payment_intent_id": payment_intent.id,
                    "sale_id": payment_intent.sale_id,
                    "provider": payment_intent.provider,
                },
                correlation_id=state["correlation_id"],
                causation_id=state.get("source_event_id"),
                trace_id=state.get("trace_id"),
            )

        if payment_intent.status in {
            PaymentIntentStatus.PAID.value,
            PaymentIntentStatus.CANCELLED.value,
            PaymentIntentStatus.EXPIRED.value,
            PaymentIntentStatus.TIMEOUT.value,
        }:
            state["next_route"] = "report"
            state["decision"] = "watchdog_no_action_final_state"
            state["reasoning_summary"] = "Payment intent already finalized."
            state["confidence_score"] = 0.98
            state["status"] = "ok"
            if existing_pending:
                resolve_agent_task(db, existing_pending)
            return state

        if now < due_at:
            state["next_route"] = "report"
            state["decision"] = "watchdog_waiting"
            state["reasoning_summary"] = "Timeout window not reached yet."
            state["confidence_score"] = 0.98
            state["status"] = "pending"
            return state

        payment_intent.status = PaymentIntentStatus.TIMEOUT.value
        db.add(payment_intent)
        sale = db.scalar(
            select(Sale).where(
                Sale.tenant_id == state["tenant_id"],
                Sale.id == payment_intent.sale_id,
            )
        )
        if sale:
            sale.status = SaleStatus.BLOCKED.value
            db.add(sale)
        if existing_pending:
            resolve_agent_task(db, existing_pending)
        timeout_event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.PAYMENT_TIMEOUT_DETECTED.value,
            payload={
                "payment_intent_id": payment_intent.id,
                "sale_id": payment_intent.sale_id,
                "due_at": due_at.isoformat(),
            },
            source="agentic.timeout_watchdog",
            provider=payment_intent.provider,
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        if sale:
            append_event(
                db,
                tenant_id=state["tenant_id"],
                aggregate_type="sale",
                aggregate_id=sale.id,
                event_type=EventType.SALE_RELEASE_BLOCKED.value,
                payload={
                    "sale_id": sale.id,
                    "payment_intent_id": payment_intent.id,
                    "reason": "payment_timeout_detected",
                },
                source="agentic.timeout_watchdog",
                provider=payment_intent.provider,
                correlation_id=state["correlation_id"],
                causation_id=timeout_event.event_id,
            )
        append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="payment_intent",
            aggregate_id=payment_intent.id,
            event_type=EventType.OPERATIONAL_ALERT_CREATED.value,
            payload={
                "category": "payment_timeout",
                "severity": "high",
                "message": "Payment confirmation window expired before validated provider event.",
            },
            source="agentic.timeout_watchdog",
            provider=payment_intent.provider,
            correlation_id=state["correlation_id"],
            causation_id=timeout_event.event_id,
        )
        state["source_event_id"] = timeout_event.event_id
        state["output_event_id"] = timeout_event.event_id
        state["output_event_type"] = EventType.PAYMENT_TIMEOUT_DETECTED.value
        state["event_type"] = EventType.PAYMENT_TIMEOUT_DETECTED.value
        state["next_route"] = "notification"
        state["decision"] = "timeout_detected_block_release"
        state["reasoning_summary"] = "Payment intent timed out and release must stay blocked."
        state["confidence_score"] = 0.99
        state["status"] = "blocked"
        state["needs_manual_review"] = True
        return state

    def notification(state: AgenticState) -> AgenticState:
        sale_id = state.get("sale_id")
        payment_intent_id = state.get("payment_intent_id")
        severity = state.get("risk_severity") or (
            "high" if state.get("event_type") == EventType.PAYMENT_TIMEOUT_DETECTED.value else "low"
        )
        message = "No payment release without validated provider event."
        if state.get("event_type") == EventType.PAYMENT_TIMEOUT_DETECTED.value:
            message = "Payment timeout detected. Do not release sale until manual review."
        elif state.get("output_event_type") == EventType.LEDGER_ENTRY_CREATED.value:
            message = "Payment reconciled and ledger recorded."

        op_notification = enqueue_notification(
            db,
            tenant_id=state["tenant_id"],
            correlation_id=state["correlation_id"],
            channel="dashboard",
            recipient="operator",
            severity=severity,
            subject="Payment operations update",
            message=message,
        )
        owner_notification = enqueue_notification(
            db,
            tenant_id=state["tenant_id"],
            correlation_id=state["correlation_id"],
            channel="email",
            recipient="owner",
            severity=severity,
            subject="PixOps OS alert",
            message=(
                f"{message} correlation_id={state['correlation_id']} "
                f"sale_id={sale_id} payment_intent_id={payment_intent_id}"
            ),
        )
        mark_notification_sent(db, op_notification)
        mark_notification_sent(db, owner_notification)
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="notification",
            aggregate_id=op_notification.id,
            event_type=EventType.NOTIFICATION_SENT.value,
            payload={
                "channels": ["dashboard", "email"],
                "severity": severity,
                "sale_id": sale_id,
                "payment_intent_id": payment_intent_id,
            },
            source="agentic.notification",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.NOTIFICATION_SENT.value
        if state.get("needs_manual_review"):
            state["review_after_notification"] = True
            state["next_route"] = "human_review"
        else:
            state["next_route"] = "end"
        state["decision"] = "notifications_dispatched"
        state["reasoning_summary"] = "Operator and owner notifications dispatched."
        state["confidence_score"] = 0.95
        state["status"] = "ok"
        return state

    def human_review(state: AgenticState) -> AgenticState:
        fraud_alert_id = state.get("payload", {}).get("fraud_alert_id")
        case = create_manual_review_case(
            db,
            tenant_id=state["tenant_id"],
            sale_id=state.get("sale_id"),
            payment_intent_id=state.get("payment_intent_id"),
            fraud_alert_id=fraud_alert_id,
            severity=state.get("risk_severity") or "medium",
            summary="Agentic flow requires manual review before release.",
            recommendation="Review webhook evidence, reconciliation details, and ledger timeline.",
        )
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="manual_review_case",
            aggregate_id=case.id,
            event_type=EventType.MANUAL_REVIEW_CASE_CREATED.value,
            payload={
                "manual_review_case_id": case.id,
                "sale_id": case.sale_id,
                "payment_intent_id": case.payment_intent_id,
            },
            source="agentic.human_review",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="manual_review_case",
            aggregate_id=case.id,
            event_type=EventType.MANUAL_REVIEW_REQUIRED.value,
            payload={
                "manual_review_case_id": case.id,
                "severity": case.severity,
                "reason": case.summary,
            },
            source="agentic.human_review",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=event.event_id,
        )
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.MANUAL_REVIEW_CASE_CREATED.value
        state["next_route"] = "end" if state.get("review_after_notification") else "notification"
        state["decision"] = "manual_review_case_opened"
        state["reasoning_summary"] = "Human-in-the-loop case created for manual decision."
        state["confidence_score"] = 0.97
        state["status"] = "blocked"
        return state

    def report(state: AgenticState) -> AgenticState:
        event = append_event(
            db,
            tenant_id=state["tenant_id"],
            aggregate_type="report",
            aggregate_id=state.get("aggregate_id", state.get("tenant_id")),
            event_type=EventType.AI_SUMMARY_GENERATED.value,
            payload={
                "summary_type": "agentic_operation_summary",
                "correlation_id": state["correlation_id"],
                "event_type": state.get("event_type"),
                "status": state.get("status"),
            },
            source="agentic.report",
            provider=state.get("provider"),
            correlation_id=state["correlation_id"],
            causation_id=state.get("source_event_id"),
        )
        state["output_event_id"] = event.event_id
        state["output_event_type"] = EventType.AI_SUMMARY_GENERATED.value
        state["next_route"] = "end"
        state["decision"] = "report_generated"
        state["reasoning_summary"] = "Operational summary event generated."
        state["confidence_score"] = 0.9
        state["status"] = state.get("status", "ok")
        return state

    builder = StateGraph(AgenticState)
    builder.add_node("event_intake", lambda s: _run_node(db, s, "EventIntakeAgent", event_intake))
    builder.add_node(
        "provider_verification",
        lambda s: _run_node(db, s, "ProviderVerificationAgent", provider_verification),
    )
    builder.add_node("payment_state", lambda s: _run_node(db, s, "PaymentStateAgent", payment_state))
    builder.add_node("reconciliation", lambda s: _run_node(db, s, "ReconciliationAgent", reconciliation))
    builder.add_node("ledger", lambda s: _run_node(db, s, "LedgerAgent", ledger))
    builder.add_node("fraud_defense", lambda s: _run_node(db, s, "FraudDefenseAgent", fraud_defense))
    builder.add_node("timeout_watchdog", lambda s: _run_node(db, s, "TimeoutWatchdogAgent", timeout_watchdog))
    builder.add_node("notification", lambda s: _run_node(db, s, "NotificationAgent", notification))
    builder.add_node("human_review", lambda s: _run_node(db, s, "HumanReviewAgent", human_review))
    builder.add_node("report", lambda s: _run_node(db, s, "ReportAgent", report))

    builder.add_edge(START, "event_intake")

    def from_intake(state: AgenticState) -> str:
        return state.get("next_route", "report")

    builder.add_conditional_edges(
        "event_intake",
        from_intake,
        {
            "provider_verification": "provider_verification",
            "payment_state": "payment_state",
            "reconciliation": "reconciliation",
            "ledger": "ledger",
            "fraud_defense": "fraud_defense",
            "timeout_watchdog": "timeout_watchdog",
            "notification": "notification",
            "human_review": "human_review",
            "report": "report",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "provider_verification",
        lambda s: s.get("next_route", "fraud_defense"),
        {
            "payment_state": "payment_state",
            "fraud_defense": "fraud_defense",
            "notification": "notification",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "payment_state",
        lambda s: s.get("next_route", "reconciliation"),
        {
            "reconciliation": "reconciliation",
            "timeout_watchdog": "timeout_watchdog",
            "notification": "notification",
            "fraud_defense": "fraud_defense",
            "report": "report",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "reconciliation",
        lambda s: s.get("next_route", "fraud_defense"),
        {"ledger": "ledger", "fraud_defense": "fraud_defense", "end": END},
    )
    builder.add_conditional_edges(
        "ledger",
        lambda s: s.get("next_route", "notification"),
        {"notification": "notification", "fraud_defense": "fraud_defense", "end": END},
    )
    builder.add_conditional_edges(
        "fraud_defense",
        lambda s: s.get("next_route", "human_review"),
        {"human_review": "human_review", "notification": "notification", "end": END},
    )
    builder.add_conditional_edges(
        "timeout_watchdog",
        lambda s: s.get("next_route", "report"),
        {"notification": "notification", "report": "report", "end": END},
    )
    builder.add_conditional_edges(
        "human_review",
        lambda s: s.get("next_route", "notification"),
        {"notification": "notification", "end": END},
    )
    builder.add_conditional_edges(
        "notification",
        lambda s: s.get("next_route", "end"),
        {"end": END, "report": "report", "human_review": "human_review"},
    )
    builder.add_edge("report", END)

    # Prefer Postgres checkpointer when available, fallback to memory.
    try:
        from langgraph.checkpoint.postgres import PostgresSaver

        checkpointer = PostgresSaver.from_conn_string(settings.database_url)
        try:
            checkpointer.setup()
        except Exception:
            pass
        graph = builder.compile(checkpointer=checkpointer)
    except Exception:
        graph = builder.compile(checkpointer=MemorySaver())
    return graph


def run_agentic_graph(db: Session, incoming: AgenticState) -> AgenticState:
    state = incoming.copy()
    state.setdefault("trace_id", str(uuid4()))
    state.setdefault("decisions", [])
    graph = build_agent_graph(db)
    settings = get_settings()
    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    if settings.langchain_project:
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    config = {
        "configurable": {"thread_id": state["correlation_id"]},
        "metadata": {
            "tenant_id": state.get("tenant_id"),
            "correlation_id": state.get("correlation_id"),
            "causation_id": state.get("causation_id"),
            "trace_id": state.get("trace_id"),
            "sale_id": state.get("sale_id"),
            "payment_intent_id": state.get("payment_intent_id"),
            "provider": state.get("provider"),
            "environment": state.get("metadata", {}).get("environment", "mvp"),
        },
    }
    final_state = state
    for update in graph.stream(state, config=config, stream_mode="updates"):
        for _, value in update.items():
            if isinstance(value, dict):
                final_state = value
    return final_state
