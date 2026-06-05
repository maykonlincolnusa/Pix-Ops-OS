# Fraud Rules

## Operational Fraud Rules
- tentativa de liberação manual sem pagamento confirmado
- pagamento com valor menor que esperado
- txid desconhecido (orphan payment)
- webhook duplicado
- pagamento após expiração
- divergência no fechamento de caixa

## Process Risk Rules
- assinatura webhook inválida
- provider desconhecido
- evento fora da janela esperada
- alteração manual indevida de status

## Severity
- low
- medium
- high
- critical

## Artifacts
- `fraud_flags` (legado operacional)
- `fraud_alerts` (centro antifraude)
- eventos `fraud.alert.*`
