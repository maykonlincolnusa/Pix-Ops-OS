from datetime import date


def generate_daily_ai_summary(
    *,
    company_id: str,
    business_date: date,
    metrics: dict,
    closure: dict,
) -> dict:
    divergent = metrics.get("divergent_sales", 0)
    flags = metrics.get("open_fraud_flags", 0)
    expected = metrics.get("expected_total_cents", 0)
    received = metrics.get("received_total_cents", 0)
    delta = received - expected

    if divergent >= 5 or flags >= 5:
        risk_level = "HIGH"
    elif divergent > 0 or flags > 0 or delta != 0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    action_items: list[str] = []
    if divergent > 0:
        action_items.append("Investigar vendas com status DIVERGENT antes de efetivar baixa financeira.")
    if flags > 0:
        action_items.append("Revisar flags de fraude operacional e evidências de webhook por txid.")
    if delta < 0:
        action_items.append("Recebimento abaixo do esperado: validar possíveis perdas ou pagamentos pendentes.")
    elif delta > 0:
        action_items.append("Recebimento acima do esperado: verificar pagamentos inesperados e identificar origem.")
    if not action_items:
        action_items.append("Sem anomalias relevantes no dia. Manter rotina de auditoria preventiva.")

    summary = (
        f"No dia {business_date.isoformat()}, a empresa {company_id} registrou "
        f"{metrics.get('total_sales', 0)} vendas, com {metrics.get('paid_sales', 0)} pagas, "
        f"{metrics.get('pending_sales', 0)} pendentes e {divergent} divergentes. "
        f"O total esperado foi R$ {expected / 100:.2f} e o recebido confirmado foi "
        f"R$ {received / 100:.2f} (diferença de R$ {delta / 100:.2f}). "
        f"Nível de risco operacional do fechamento: {risk_level}."
    )

    return {
        "company_id": company_id,
        "business_date": business_date,
        "summary": summary,
        "risk_level": risk_level,
        "action_items": action_items,
        "closure_recommendations": closure.get("recommendations", []),
    }
