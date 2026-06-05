"use client";

import { useEffect, useState } from "react";

import { apiRequest } from "@/lib/api";
import type {
  AiSummary,
  CashRegister,
  CloseoutReport,
  Company,
  DashboardMetrics,
  Divergence,
  EventItem,
  FraudAlert,
  LedgerEntry,
  ManualReviewCase,
  NotificationOutbox,
  Operator,
  PixCharge,
  Sale,
  Store,
  Tenant,
} from "@/lib/types";
import { money } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useTenantStore } from "@/stores/use-tenant-store";

const tabs = ["operations", "events", "ledger", "fraud", "review", "notifications"] as const;
type TabKey = (typeof tabs)[number];

export function PixOpsWorkspace() {
  const [tab, setTab] = useState<TabKey>("operations");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const tenantId = useTenantStore((s) => s.tenantId);
  const setTenantId = useTenantStore((s) => s.setTenantId);
  const companyId = useTenantStore((s) => s.companyId);
  const setCompanyId = useTenantStore((s) => s.setCompanyId);
  const [storeId, setStoreId] = useState("");
  const [operatorId, setOperatorId] = useState("");
  const [cashierId, setCashierId] = useState("");
  const [saleId, setSaleId] = useState("");
  const [today, setToday] = useState(new Date().toISOString().slice(0, 10));

  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [cashiers, setCashiers] = useState<CashRegister[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [fraud, setFraud] = useState<FraudAlert[]>([]);
  const [manualReviews, setManualReviews] = useState<ManualReviewCase[]>([]);
  const [notifications, setNotifications] = useState<NotificationOutbox[]>([]);
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [closeout, setCloseout] = useState<CloseoutReport | null>(null);
  const [aiSummary, setAiSummary] = useState<AiSummary | null>(null);
  const [lastCharge, setLastCharge] = useState<PixCharge | null>(null);

  const [tenantForm, setTenantForm] = useState({
    name: "Tenant Piloto PixOps",
    document_number: "12345678000190",
    plan: "pro",
  });
  const [companyForm, setCompanyForm] = useState({
    name: "Rede PixOps",
    legal_name: "Rede PixOps LTDA",
    tax_id: "12345678000190",
  });
  const [storeForm, setStoreForm] = useState({ name: "Unidade Centro", code: "CTR-01" });
  const [operatorForm, setOperatorForm] = useState({
    full_name: "Operador 01",
    document: "12345678900",
  });
  const [cashierForm, setCashierForm] = useState({ code: "CX-01" });
  const [saleForm, setSaleForm] = useState({
    external_ref: `VENDA-${Date.now()}`,
    description: "Venda balcão",
    expected_amount_cents: 10000,
    expected_method: "pix",
  });
  const [chargeForm, setChargeForm] = useState({
    pix_key: "pixops@empresa.com.br",
    payer_name: "Cliente",
    expires_in_minutes: 20,
  });
  const [webhookForm, setWebhookForm] = useState({
    txid: "",
    end_to_end_id: `E2E${Date.now()}`,
    amount_cents: 10000,
  });

  const safe = async (fn: () => Promise<void>, ok: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await fn();
      setSuccess(ok);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadBase = async () => {
    const tenantList = await apiRequest<Tenant[]>("/setup/tenants");
    setTenants(tenantList);
    if (!tenantId && tenantList[0]) setTenantId(tenantList[0].id);
  };

  const loadScoped = async () => {
    if (!tenantId) return;
    const companyList = await apiRequest<Company[]>(`/setup/companies?tenant_id=${tenantId}`);
    setCompanies(companyList);
    const comp = companyId || companyList[0]?.id;
    if (!companyId && comp) setCompanyId(comp);
    if (!comp) return;

    const [storeList, operatorList, cashierList, salesList] = await Promise.all([
      apiRequest<Store[]>(`/setup/stores?tenant_id=${tenantId}&company_id=${comp}`),
      apiRequest<Operator[]>(`/setup/operators?tenant_id=${tenantId}&company_id=${comp}`),
      apiRequest<CashRegister[]>(
        `/setup/cash-registers?tenant_id=${tenantId}&company_id=${comp}`,
      ),
      apiRequest<Sale[]>(
        `/payments/sales?tenant_id=${tenantId}&company_id=${comp}&business_date=${today}`,
      ),
    ]);
    setStores(storeList);
    setOperators(operatorList);
    setCashiers(cashierList);
    setSales(salesList);
    if (!storeId && storeList[0]) setStoreId(storeList[0].id);
    if (!operatorId && operatorList[0]) setOperatorId(operatorList[0].id);
    if (!cashierId && cashierList[0]) setCashierId(cashierList[0].id);
    if (!saleId && salesList[0]) setSaleId(salesList[0].id);
  };

  const loadDash = async () => {
    if (!tenantId || !companyId) return;
    const [m, e, l, f, d, r, n] = await Promise.all([
      apiRequest<DashboardMetrics>(
        `/dashboard/metrics?tenant_id=${tenantId}&company_id=${companyId}&business_date=${today}`,
      ),
      apiRequest<EventItem[]>(`/dashboard/events?tenant_id=${tenantId}&limit=100`),
      apiRequest<LedgerEntry[]>(`/dashboard/ledger?tenant_id=${tenantId}&limit=100`),
      apiRequest<FraudAlert[]>(`/dashboard/fraud-alerts?tenant_id=${tenantId}&limit=100`),
      apiRequest<Divergence[]>(
        `/dashboard/divergences?tenant_id=${tenantId}&company_id=${companyId}&limit=100`,
      ),
      apiRequest<ManualReviewCase[]>(`/agentic/manual-review-cases?tenant_id=${tenantId}&limit=100`),
      apiRequest<NotificationOutbox[]>(`/agentic/notifications?tenant_id=${tenantId}&limit=100`),
    ]);
    setMetrics(m);
    setEvents(e);
    setLedger(l);
    setFraud(f);
    setDivergences(d);
    setManualReviews(r);
    setNotifications(n);
  };

  const refresh = async () => {
    await loadBase();
    await loadScoped();
    await loadDash();
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadScoped();
    void loadDash();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, companyId, today]);

  useEffect(() => {
    const t = setInterval(() => void loadDash(), 7000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, companyId, today]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <section className="mb-6 rounded-3xl border border-border bg-aurora p-6 shadow-glow">
        <p className="font-display text-xs uppercase tracking-[0.2em] text-primary">PixOps OS</p>
        <h1 className="font-display text-3xl font-bold">
          Real-Time Payment Operations, Reconciliation & Anti-Fraud Platform
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Camada operacional sobre bancos, PSPs e adquirentes. Não promete eliminar 100% das
          fraudes.
        </p>
        {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {success && (
          <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{success}</p>
        )}
      </section>

      <section className="mb-4 flex flex-wrap gap-2">
        {tabs.map((item) => (
          <Button
            key={item}
            variant={tab === item ? "default" : "outline"}
            onClick={() => setTab(item)}
          >
            {item}
          </Button>
        ))}
        <Input className="w-44" type="date" value={today} onChange={(e) => setToday(e.target.value)} />
        <Button variant="outline" onClick={() => void safe(refresh, "Dados atualizados.")} disabled={loading}>
          Atualizar
        </Button>
      </section>

      {tab === "operations" && (
        <section className="grid gap-6 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Onboarding Multi-tenant</CardTitle>
              <CardDescription>Tenant, organização, loja, operador e caixa.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Tenant</Label>
                  <Input
                    value={tenantForm.name}
                    onChange={(e) => setTenantForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>CNPJ</Label>
                  <Input
                    value={tenantForm.document_number}
                    onChange={(e) => setTenantForm((p) => ({ ...p, document_number: e.target.value }))}
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={() =>
                      void safe(async () => {
                        const t = await apiRequest<Tenant>("/setup/tenants", "POST", tenantForm);
                        setTenantId(t.id);
                        await refresh();
                      }, "Tenant criado.")
                    }
                  >
                    Criar tenant
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <Label>Tenant selecionado</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3"
                    value={tenantId}
                    onChange={(e) => setTenantId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {tenants.map((t) => (
                      <option value={t.id} key={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Empresa selecionada</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3"
                    value={companyId}
                    onChange={(e) => setCompanyId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {companies.map((c) => (
                      <option value={c.id} key={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <Input
                  placeholder="Nome empresa"
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm((p) => ({ ...p, name: e.target.value }))}
                />
                <Input
                  placeholder="Razão social"
                  value={companyForm.legal_name}
                  onChange={(e) => setCompanyForm((p) => ({ ...p, legal_name: e.target.value }))}
                />
                <Input
                  placeholder="CNPJ"
                  value={companyForm.tax_id}
                  onChange={(e) => setCompanyForm((p) => ({ ...p, tax_id: e.target.value }))}
                />
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const c = await apiRequest<Company>("/setup/companies", "POST", {
                        ...companyForm,
                        tenant_id: tenantId,
                      });
                      setCompanyId(c.id);
                      await refresh();
                    }, "Empresa criada.")
                  }
                  disabled={!tenantId}
                >
                  Criar empresa
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Input
                  placeholder="Loja"
                  value={storeForm.name}
                  onChange={(e) => setStoreForm((p) => ({ ...p, name: e.target.value }))}
                />
                <Input
                  placeholder="Código"
                  value={storeForm.code}
                  onChange={(e) => setStoreForm((p) => ({ ...p, code: e.target.value }))}
                />
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const s = await apiRequest<Store>("/setup/stores", "POST", {
                        ...storeForm,
                        tenant_id: tenantId,
                        company_id: companyId,
                      });
                      setStoreId(s.id);
                      await refresh();
                    }, "Loja criada.")
                  }
                  disabled={!tenantId || !companyId}
                >
                  Criar loja
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Input
                  placeholder="Operador"
                  value={operatorForm.full_name}
                  onChange={(e) => setOperatorForm((p) => ({ ...p, full_name: e.target.value }))}
                />
                <Input
                  placeholder="Documento"
                  value={operatorForm.document}
                  onChange={(e) => setOperatorForm((p) => ({ ...p, document: e.target.value }))}
                />
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const o = await apiRequest<Operator>("/setup/operators", "POST", {
                        ...operatorForm,
                        tenant_id: tenantId,
                        company_id: companyId,
                        store_id: storeId,
                      });
                      setOperatorId(o.id);
                      await refresh();
                    }, "Operador criado.")
                  }
                  disabled={!tenantId || !companyId || !storeId}
                >
                  Criar operador
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Input
                  placeholder="Caixa"
                  value={cashierForm.code}
                  onChange={(e) => setCashierForm((p) => ({ ...p, code: e.target.value }))}
                />
                <select
                  className="h-10 w-full rounded-xl border border-input bg-white/80 px-3"
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                >
                  <option value="">Operador</option>
                  {operators.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.full_name}
                    </option>
                  ))}
                </select>
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const c = await apiRequest<CashRegister>("/setup/cash-registers", "POST", {
                        ...cashierForm,
                        tenant_id: tenantId,
                        company_id: companyId,
                        store_id: storeId,
                        operator_id: operatorId || null,
                      });
                      setCashierId(c.id);
                      await refresh();
                    }, "Caixa criado.")
                  }
                  disabled={!tenantId || !companyId || !storeId}
                >
                  Criar caixa
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Fluxo Pix End-to-end</CardTitle>
              <CardDescription>Venda, QR dinâmico, webhook, conciliação e ledger.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 md:grid-cols-4">
                <Input
                  value={saleForm.external_ref}
                  onChange={(e) => setSaleForm((p) => ({ ...p, external_ref: e.target.value }))}
                  placeholder="Ref venda"
                />
                <Input
                  value={saleForm.description}
                  onChange={(e) => setSaleForm((p) => ({ ...p, description: e.target.value }))}
                  placeholder="Descrição"
                />
                <Input
                  type="number"
                  value={saleForm.expected_amount_cents}
                  onChange={(e) =>
                    setSaleForm((p) => ({ ...p, expected_amount_cents: Number(e.target.value) }))
                  }
                  placeholder="Centavos"
                />
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const s = await apiRequest<Sale>("/payments/sales", "POST", {
                        ...saleForm,
                        tenant_id: tenantId,
                        company_id: companyId,
                        store_id: storeId,
                        operator_id: operatorId || null,
                        cash_register_id: cashierId || null,
                      });
                      setSaleId(s.id);
                      setWebhookForm((p) => ({ ...p, amount_cents: s.expected_amount_cents }));
                      await refresh();
                    }, "Venda criada.")
                  }
                  disabled={!tenantId || !companyId || !storeId}
                >
                  Criar venda
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <select
                  className="h-10 w-full rounded-xl border border-input bg-white/80 px-3"
                  value={saleId}
                  onChange={(e) => setSaleId(e.target.value)}
                >
                  <option value="">Selecione venda</option>
                  {sales.map((s) => (
                    <option value={s.id} key={s.id}>
                      {s.external_ref} | {money(s.expected_amount_cents)} | {s.status}
                    </option>
                  ))}
                </select>
                <Input
                  value={chargeForm.pix_key}
                  onChange={(e) => setChargeForm((p) => ({ ...p, pix_key: e.target.value }))}
                  placeholder="Chave Pix"
                />
                <Button
                  onClick={() =>
                    void safe(async () => {
                      const ch = await apiRequest<PixCharge>("/payments/pix/charges", "POST", {
                        ...chargeForm,
                        tenant_id: tenantId,
                        company_id: companyId,
                        sale_id: saleId,
                      });
                      setLastCharge(ch);
                      setWebhookForm((p) => ({
                        ...p,
                        txid: ch.txid,
                        amount_cents: ch.amount_cents,
                      }));
                      await refresh();
                    }, "QR dinâmico gerado.")
                  }
                  disabled={!tenantId || !companyId || !saleId}
                >
                  Gerar cobrança Pix
                </Button>
              </div>

              {lastCharge && (
                <div className="rounded-xl border border-border bg-white/70 p-3">
                  <p className="text-xs text-muted-foreground">TXID: {lastCharge.txid}</p>
                  <p className="text-sm font-semibold">{money(lastCharge.amount_cents)}</p>
                  {lastCharge.qr_code_base64 && (
                    <img src={lastCharge.qr_code_base64} className="mt-2 h-32 w-32 rounded-lg" alt="qr" />
                  )}
                  <Textarea value={lastCharge.qr_code_text} readOnly className="mt-2 text-xs" />
                </div>
              )}

              <div className="rounded-xl border border-border bg-white/70 p-3">
                <p className="mb-2 text-sm font-semibold">Webhook Pix simulado</p>
                <div className="grid gap-3 md:grid-cols-3">
                  <Input
                    value={webhookForm.txid}
                    onChange={(e) => setWebhookForm((p) => ({ ...p, txid: e.target.value }))}
                    placeholder="txid"
                  />
                  <Input
                    value={webhookForm.end_to_end_id}
                    onChange={(e) =>
                      setWebhookForm((p) => ({ ...p, end_to_end_id: e.target.value }))
                    }
                    placeholder="end_to_end_id"
                  />
                  <Input
                    type="number"
                    value={webhookForm.amount_cents}
                    onChange={(e) =>
                      setWebhookForm((p) => ({ ...p, amount_cents: Number(e.target.value) }))
                    }
                    placeholder="valor"
                  />
                </div>
                <Button
                  className="mt-2"
                  onClick={() =>
                    void safe(async () => {
                      await apiRequest("/payments/pix/webhooks/confirmation", "POST", {
                        tenant_id: tenantId,
                        company_id: companyId,
                        txid: webhookForm.txid,
                        end_to_end_id: webhookForm.end_to_end_id,
                        amount_cents: webhookForm.amount_cents,
                        raw_payload: { source: "dashboard" },
                      });
                      await refresh();
                    }, "Webhook processado.")
                  }
                  disabled={!tenantId || !webhookForm.txid}
                >
                  Confirmar pagamento
                </Button>
              </div>

              <div className="grid gap-2 md:grid-cols-2">
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Recebido hoje</p>
                  <p className="text-xl font-bold">{money(metrics?.received_total_cents)}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Divergências</p>
                  <p className="text-xl font-bold">{metrics?.divergent_sales ?? 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      {tab === "events" && (
        <Card>
          <CardHeader>
            <CardTitle>Event Monitor</CardTitle>
            <CardDescription>Timeline do event store com hash chain.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {events.slice(0, 60).map((evt) => (
              <div key={`${evt.event_id}-${evt.id}`} className="rounded-xl border border-border p-3">
                <div className="flex justify-between">
                  <p className="font-semibold text-sm">{evt.event_type}</p>
                  <Badge variant="neutral">{evt.aggregate_type}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {evt.aggregate_id} · {evt.source} · {evt.provider ?? "internal"}
                </p>
                <p className="text-xs text-muted-foreground">{evt.current_hash.slice(0, 20)}...</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "ledger" && (
        <Card>
          <CardHeader>
            <CardTitle>Ledger</CardTitle>
            <CardDescription>Entradas contábeis debit/credit por transação.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {ledger.slice(0, 80).map((entry) => (
              <div key={entry.id} className="rounded-xl border border-border p-3">
                <div className="flex justify-between">
                  <p className="text-sm font-semibold">{entry.account_id}</p>
                  <Badge variant={entry.direction === "credit" ? "success" : "warning"}>
                    {entry.direction}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {entry.transaction_id} · {entry.provider ?? "-"} · {entry.entry_type}
                </p>
                <p className="text-sm">{entry.currency} {Number(entry.amount).toFixed(2)}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "fraud" && (
        <section className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Fraud Center</CardTitle>
              <CardDescription>Alertas por severidade com evidências.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {fraud.slice(0, 40).map((alert) => (
                <div key={alert.id} className="rounded-xl border border-border p-3">
                  <div className="flex justify-between">
                    <Badge
                      variant={
                        alert.severity === "critical" || alert.severity === "high"
                          ? "danger"
                          : alert.severity === "medium"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {alert.severity}
                    </Badge>
                    <p className="text-xs text-muted-foreground">{alert.category}</p>
                  </div>
                  <p className="text-sm mt-1">{alert.reason}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Conciliação & IA</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                onClick={() =>
                  void safe(async () => {
                    const report = await apiRequest<CloseoutReport>(
                      `/dashboard/closeout?tenant_id=${tenantId}&company_id=${companyId}&store_id=${storeId}&business_date=${today}`,
                    );
                    setCloseout(report);
                  }, "Fechamento gerado.")
                }
                disabled={!tenantId || !companyId || !storeId}
              >
                Gerar fechamento
              </Button>
              <Button
                variant="outline"
                onClick={() =>
                  void safe(async () => {
                    const summary = await apiRequest<AiSummary>(
                      `/ai/daily-summary?tenant_id=${tenantId}&company_id=${companyId}&store_id=${storeId}`,
                    );
                    setAiSummary(summary);
                  }, "Resumo IA gerado.")
                }
                disabled={!tenantId || !companyId || !storeId}
              >
                Gerar resumo IA
              </Button>

              {closeout && (
                <div className="rounded-xl border border-border p-3 text-sm">
                  {money(closeout.totals.expected_total_cents)} esperado vs{" "}
                  {money(closeout.totals.received_total_cents)} recebido
                </div>
              )}
              {aiSummary && <div className="rounded-xl border border-border p-3 text-sm">{aiSummary.summary}</div>}
              {divergences.slice(0, 6).map((d) => (
                <div key={d.id} className="rounded-xl border border-border p-3">
                  <p className="text-sm font-semibold">{d.status}</p>
                  <p className="text-xs text-muted-foreground">{d.reason}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      )}

      {tab === "review" && (
        <Card>
          <CardHeader>
            <CardTitle>Manual Review</CardTitle>
            <CardDescription>Casos que exigem decisao humana antes de liberar a venda.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {manualReviews.slice(0, 60).map((item) => (
              <div key={item.id} className="rounded-xl border border-border p-3">
                <div className="flex justify-between gap-3">
                  <p className="text-sm font-semibold">{item.summary}</p>
                  <Badge
                    variant={
                      item.severity === "critical" || item.severity === "high"
                        ? "danger"
                        : item.severity === "medium"
                          ? "warning"
                          : "neutral"
                    }
                  >
                    {item.status}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{item.recommendation}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  sale={item.sale_id ?? "-"} payment={item.payment_intent_id ?? "-"}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "notifications" && (
        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
            <CardDescription>Outbox operacional para dashboard, email e canais futuros.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {notifications.slice(0, 80).map((item) => (
              <div key={item.id} className="rounded-xl border border-border p-3">
                <div className="flex justify-between gap-3">
                  <p className="text-sm font-semibold">{item.subject}</p>
                  <Badge variant={item.status === "sent" ? "success" : "warning"}>{item.channel}</Badge>
                </div>
                <p className="mt-1 text-sm">{item.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.recipient} | {item.severity} | {item.correlation_id ?? "-"}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
