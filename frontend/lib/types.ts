export type Company = {
  id: string;
  name: string;
  legal_name: string;
  tax_id: string;
  created_at: string;
};

export type Store = {
  id: string;
  company_id: string;
  name: string;
  code: string;
  created_at: string;
};

export type Operator = {
  id: string;
  company_id: string;
  store_id: string | null;
  full_name: string;
  document: string | null;
  active: boolean;
  created_at: string;
};

export type CashRegister = {
  id: string;
  company_id: string;
  store_id: string;
  operator_id: string | null;
  code: string;
  status: string;
  created_at: string;
};

export type Sale = {
  id: string;
  company_id: string;
  store_id: string;
  cash_register_id: string | null;
  operator_id: string | null;
  external_ref: string;
  description: string | null;
  expected_amount_cents: number;
  currency: string;
  expected_method: string;
  status: string;
  opened_at: string;
  paid_at: string | null;
};

export type PixCharge = {
  id: string;
  company_id: string;
  sale_id: string;
  txid: string;
  pix_key: string;
  amount_cents: number;
  payer_name: string | null;
  qr_code_text: string;
  qr_code_base64: string | null;
  status: string;
  expires_at: string;
  confirmed_at: string | null;
  confirmed_amount_cents: number | null;
  end_to_end_id: string | null;
  created_at: string;
};

export type DashboardMetrics = {
  company_id: string;
  business_date: string;
  total_sales: number;
  paid_sales: number;
  pending_sales: number;
  divergent_sales: number;
  expected_total_cents: number;
  received_total_cents: number;
  open_fraud_flags: number;
  latest_events: Array<{
    event_id: string;
    sequence_no: number;
    source: string;
    event_type: string;
    reference_id: string | null;
    amount_cents: number | null;
    occurred_at: string;
    event_hash: string;
  }>;
};

export type Divergence = {
  id: string;
  company_id: string;
  store_id: string | null;
  sale_id: string | null;
  txid: string | null;
  expected_amount_cents: number | null;
  received_amount_cents: number | null;
  status: string;
  reason: string;
  created_at: string;
};

export type FraudFlag = {
  id: string;
  company_id: string;
  store_id: string | null;
  sale_id: string | null;
  txid: string | null;
  severity: string;
  flag_type: string;
  description: string;
  status: string;
  created_at: string;
};

export type CloseoutReport = {
  company_id: string;
  store_id: string;
  business_date: string;
  totals: {
    sales_count: number;
    paid_sales_count: number;
    divergent_sales_count: number;
    expected_total_cents: number;
    received_total_cents: number;
    difference_cents: number;
  };
  divergences: Array<{
    sale_id: string | null;
    txid: string | null;
    status: string;
    reason: string;
    expected_amount_cents: number | null;
    received_amount_cents: number | null;
    created_at: string;
  }>;
  recommendations: string[];
};

export type AiSummary = {
  company_id: string;
  business_date: string;
  summary: string;
  risk_level: string;
  action_items: string[];
};
