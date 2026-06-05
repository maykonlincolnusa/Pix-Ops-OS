# Demo Flows

## Flow 1: Venda Pix normal

1. Create tenant/company/store/operator/cash register in the setup panel.
2. Create a sale in the cashier flow.
3. Generate a mocked Pix charge.
4. Copy/display QR Code payload and `txid`.
5. Simulate an approved webhook with the expected amount.
6. Provider Verification Agent validates the event.
7. Reconciliation Agent classifies it as `matched`.
8. Ledger Agent creates double-entry ledger records.
9. Sale becomes `paid`, payment intent becomes `paid`, and events appear in Event Monitor.

Expected evidence:
- `webhook.received`
- `webhook.verified`
- `payment.state_checked`
- `reconciliation.matched`
- `ledger.entry.created`
- `sale.paid`

## Flow 2: Pix com valor divergente

1. Create a sale for BRL 100.00.
2. Generate Pix charge.
3. Simulate webhook for BRL 90.00.
4. Reconciliation Agent classifies `underpaid`.
5. Sale moves to `manual_review_required`.
6. Fraud Defense Agent creates high-risk alert.
7. Human Review Agent creates a manual review case.

Expected result:
- Sale is not paid.
- No final ledger confirmation is created.
- Fraud Center and manual review show the case.

## Flow 3: Webhook duplicado

1. Send a Pix webhook with an `external_event_id`.
2. Send the same event again.
3. Webhook idempotency ignores the second event.

Expected result:
- First event processes normally.
- Second event records duplicate handling and must not create a second ledger entry.

## Flow 4: Pagamento orfao

1. Send a Pix webhook with unknown `txid`.
2. Agentic Reconciliation classifies `orphan_payment`.
3. Fraud alert and manual review case are created.

Expected result:
- No sale is paid.
- No final ledger confirmation is created.

## Flow 5: Timeout

1. Create sale and Pix charge.
2. Do not send webhook before `due_at`.
3. Run `/api/v1/agentic/watchdog/run`.
4. Timeout Watchdog emits `payment.timeout_detected`.
5. Sale becomes `blocked`.
6. Notification and manual review case are created.

Expected evidence:
- `payment.timeout_detected`
- `sale.release_blocked`
- `notification.sent`
- `manual_review_case.created`

## Flow 6: Tentativa manual de liberacao

1. Attempt manual release before validated payment.
2. System records `sale.manual_release_attempted`.
3. System emits `sale.release_blocked`.
4. Fraud alert and manual review case are created.

Expected result:
- Sale remains blocked/manual-review.
- Audit trail includes actor and justification.

## Flow 7: Fechamento de caixa

1. Generate multiple paid, pending and divergent sales.
2. Open dashboard closeout.
3. Review expected total, received total, differences and recommendations.

Expected result:
- Matched payments contribute to received total.
- Divergences and pending payments appear separately.
