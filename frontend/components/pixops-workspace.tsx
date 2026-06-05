"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCcw, ShieldAlert, Zap } from "lucide-react";

import { apiRequest } from "@/lib/api";
import type {
  AiSummary,
  CashRegister,
  CloseoutReport,
  Company,
  DashboardMetrics,
  Divergence,
  FraudFlag,
  Operator,
  PixCharge,
  Sale,
  Store,
} from "@/lib/types";
import { cn, money } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

function metricTone(
  value: string,
): "default" | "danger" | "success" | "warning" | "neutral" {
  if (value === "PAID" || value === "MATCHED" || value === "LOW") return "success";
  if (value === "DIVERGENT" || value === "HIGH") return "danger";
  if (value === "MEDIUM") return "warning";
  return "neutral";
}

export function PixOpsWorkspace() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [companies, setCompanies] = useState<Company[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [cashRegisters, setCashRegisters] = useState<CashRegister[]>([]);
  const [sales, setSales] = useState<Sale[]>([]);

  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [divergences, setDivergences] = useState<Divergence[]>([]);
  const [fraudFlags, setFraudFlags] = useState<FraudFlag[]>([]);
  const [closeout, setCloseout] = useState<CloseoutReport | null>(null);
  const [aiSummary, setAiSummary] = useState<AiSummary | null>(null);

  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedStore, setSelectedStore] = useState("");
  const [selectedOperator, setSelectedOperator] = useState("");
  const [selectedCashRegister, setSelectedCashRegister] = useState("");
  const [selectedSale, setSelectedSale] = useState("");
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().slice(0, 10),
  );

  const [companyForm, setCompanyForm] = useState({
    name: "Loja Piloto PixOps",
    legal_name: "Loja Piloto PixOps LTDA",
    tax_id: "12345678000190",
  });

  const [storeForm, setStoreForm] = useState({
    name: "Unidade Centro",
    code: "CTR-01",
  });

  const [operatorForm, setOperatorForm] = useState({
    full_name: "Operador Caixa 1",
    document: "12345678900",
  });

  const [cashRegisterForm, setCashRegisterForm] = useState({
    code: "CX-01",
  });

  const [saleForm, setSaleForm] = useState({
    external_ref: `VENDA-${Date.now()}`,
    description: "Venda balcão",
    expected_amount_cents: 19990,
  });

  const [chargeForm, setChargeForm] = useState({
    pix_key: "pixops@empresa.com.br",
    payer_name: "Cliente PixOps",
    expires_in_minutes: 20,
  });

  const [webhookForm, setWebhookForm] = useState({
    txid: "",
    end_to_end_id: `E2E${Date.now()}`,
    amount_cents: 19990,
  });

  const [lastCharge, setLastCharge] = useState<PixCharge | null>(null);

  const resetMessages = useCallback(() => {
    setError(null);
    setSuccess(null);
  }, []);

  const refreshSetup = useCallback(async () => {
    const listCompanies = await apiRequest<Company[]>("/setup/companies");
    setCompanies(listCompanies);
    if (!selectedCompany && listCompanies.length > 0) {
      setSelectedCompany(listCompanies[0].id);
    }
  }, [selectedCompany]);

  const refreshCompanyData = useCallback(async () => {
    if (!selectedCompany) return;
    const [storeRes, operatorRes, cashRes, saleRes] = await Promise.all([
      apiRequest<Store[]>(`/setup/stores?company_id=${selectedCompany}`),
      apiRequest<Operator[]>(`/setup/operators?company_id=${selectedCompany}`),
      apiRequest<CashRegister[]>(`/setup/cash-registers?company_id=${selectedCompany}`),
      apiRequest<Sale[]>(
        `/payments/sales?company_id=${selectedCompany}&business_date=${selectedDate}`,
      ),
    ]);
    setStores(storeRes);
    setOperators(operatorRes);
    setCashRegisters(cashRes);
    setSales(saleRes);

    if (!selectedStore && storeRes.length > 0) setSelectedStore(storeRes[0].id);
    if (!selectedOperator && operatorRes.length > 0) setSelectedOperator(operatorRes[0].id);
    if (!selectedCashRegister && cashRes.length > 0) setSelectedCashRegister(cashRes[0].id);
    if (!selectedSale && saleRes.length > 0) setSelectedSale(saleRes[0].id);
  }, [
    selectedCompany,
    selectedDate,
    selectedStore,
    selectedOperator,
    selectedCashRegister,
    selectedSale,
  ]);

  const refreshDashboard = useCallback(async () => {
    if (!selectedCompany) return;
    const [metricsRes, divergencesRes, fraudRes] = await Promise.all([
      apiRequest<DashboardMetrics>(
        `/dashboard/metrics?company_id=${selectedCompany}&business_date=${selectedDate}`,
      ),
      apiRequest<Divergence[]>(`/dashboard/divergences?company_id=${selectedCompany}`),
      apiRequest<FraudFlag[]>(`/dashboard/fraud-flags?company_id=${selectedCompany}`),
    ]);
    setMetrics(metricsRes);
    setDivergences(divergencesRes);
    setFraudFlags(fraudRes);
  }, [selectedCompany, selectedDate]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    resetMessages();
    try {
      await refreshSetup();
      await refreshCompanyData();
      await refreshDashboard();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [refreshSetup, refreshCompanyData, refreshDashboard, resetMessages]);

  useEffect(() => {
    void refreshSetup();
  }, [refreshSetup]);

  useEffect(() => {
    void refreshCompanyData();
    void refreshDashboard();
  }, [selectedCompany, selectedDate, refreshCompanyData, refreshDashboard]);

  useEffect(() => {
    const timer = setInterval(() => {
      void refreshDashboard();
    }, 8000);
    return () => clearInterval(timer);
  }, [refreshDashboard]);

  const handleAction = async (task: () => Promise<void>, message: string) => {
    setLoading(true);
    resetMessages();
    try {
      await task();
      setSuccess(message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const riskVariant = useMemo(() => {
    if (!aiSummary) return "neutral";
    return metricTone(aiSummary.risk_level);
  }, [aiSummary]);

  return (
    <main className="mx-auto max-w-7xl animate-fadeUp px-4 py-6 md:px-8 md:py-10">
      <section className="mb-6 rounded-3xl border border-border/60 bg-aurora p-6 shadow-glow md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-display text-sm uppercase tracking-[0.2em] text-primary">
              PixOps OS
            </p>
            <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
              Sistema Operacional Financeiro
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-muted-foreground md:text-base">
              Rastreie e concilie pagamentos em tempo real. Uma venda só fecha
              quando existe confirmação real do PSP/adquirente.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-44"
            />
            <Button onClick={() => void refreshAll()} disabled={loading} variant="outline">
              <RefreshCcw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
              Atualizar
            </Button>
          </div>
        </div>
        {error ? (
          <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}
        {success ? (
          <p className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {success}
          </p>
        ) : null}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>1) Onboarding Operacional</CardTitle>
              <CardDescription>
                Cadastre empresa, loja, operador e caixa para iniciar o fluxo de
                pagamento e conciliação.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Empresa (nome fantasia)</Label>
                  <Input
                    value={companyForm.name}
                    onChange={(e) =>
                      setCompanyForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <Label>Razão social</Label>
                  <Input
                    value={companyForm.legal_name}
                    onChange={(e) =>
                      setCompanyForm((prev) => ({
                        ...prev,
                        legal_name: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label>CNPJ</Label>
                  <Input
                    value={companyForm.tax_id}
                    onChange={(e) =>
                      setCompanyForm((prev) => ({ ...prev, tax_id: e.target.value }))
                    }
                  />
                </div>
              </div>
              <Button
                onClick={() =>
                  void handleAction(async () => {
                    const company = await apiRequest<Company>("/setup/companies", "POST", companyForm);
                    setSelectedCompany(company.id);
                    await refreshAll();
                  }, "Empresa cadastrada.")
                }
                disabled={loading}
              >
                Cadastrar empresa
              </Button>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <Label>Empresa selecionada</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3 text-sm"
                    value={selectedCompany}
                    onChange={(e) => setSelectedCompany(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {companies.map((company) => (
                      <option key={company.id} value={company.id}>
                        {company.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Loja selecionada</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3 text-sm"
                    value={selectedStore}
                    onChange={(e) => setSelectedStore(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {stores.map((store) => (
                      <option key={store.id} value={store.id}>
                        {store.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Nome da loja</Label>
                  <Input
                    value={storeForm.name}
                    onChange={(e) =>
                      setStoreForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <Label>Código da loja</Label>
                  <Input
                    value={storeForm.code}
                    onChange={(e) =>
                      setStoreForm((prev) => ({ ...prev, code: e.target.value }))
                    }
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={() =>
                      void handleAction(async () => {
                        await apiRequest<Store>("/setup/stores", "POST", {
                          ...storeForm,
                          company_id: selectedCompany,
                        });
                        await refreshAll();
                      }, "Loja cadastrada.")
                    }
                    disabled={loading || !selectedCompany}
                  >
                    Cadastrar loja
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Operador</Label>
                  <Input
                    value={operatorForm.full_name}
                    onChange={(e) =>
                      setOperatorForm((prev) => ({
                        ...prev,
                        full_name: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label>Documento</Label>
                  <Input
                    value={operatorForm.document}
                    onChange={(e) =>
                      setOperatorForm((prev) => ({
                        ...prev,
                        document: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={() =>
                      void handleAction(async () => {
                        await apiRequest<Operator>("/setup/operators", "POST", {
                          ...operatorForm,
                          company_id: selectedCompany,
                          store_id: selectedStore || null,
                        });
                        await refreshAll();
                      }, "Operador cadastrado.")
                    }
                    disabled={loading || !selectedCompany}
                  >
                    Cadastrar operador
                  </Button>
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Caixa</Label>
                  <Input
                    value={cashRegisterForm.code}
                    onChange={(e) =>
                      setCashRegisterForm((prev) => ({
                        ...prev,
                        code: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label>Operador vinculado</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3 text-sm"
                    value={selectedOperator}
                    onChange={(e) => setSelectedOperator(e.target.value)}
                  >
                    <option value="">Sem vínculo</option>
                    {operators.map((op) => (
                      <option key={op.id} value={op.id}>
                        {op.full_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    onClick={() =>
                      void handleAction(async () => {
                        await apiRequest<CashRegister>("/setup/cash-registers", "POST", {
                          ...cashRegisterForm,
                          company_id: selectedCompany,
                          store_id: selectedStore,
                          operator_id: selectedOperator || null,
                        });
                        await refreshAll();
                      }, "Caixa cadastrado.")
                    }
                    disabled={loading || !selectedCompany || !selectedStore}
                  >
                    Cadastrar caixa
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2) Venda + Cobrança Pix + Webhook</CardTitle>
              <CardDescription>
                Registre venda esperada, gere QR dinâmico e confirme via webhook
                real/simulado.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Referência da venda</Label>
                  <Input
                    value={saleForm.external_ref}
                    onChange={(e) =>
                      setSaleForm((prev) => ({
                        ...prev,
                        external_ref: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label>Descrição</Label>
                  <Input
                    value={saleForm.description}
                    onChange={(e) =>
                      setSaleForm((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label>Valor esperado (centavos)</Label>
                  <Input
                    type="number"
                    value={saleForm.expected_amount_cents}
                    onChange={(e) =>
                      setSaleForm((prev) => ({
                        ...prev,
                        expected_amount_cents: Number(e.target.value),
                      }))
                    }
                  />
                </div>
              </div>

              <Button
                onClick={() =>
                  void handleAction(async () => {
                    const sale = await apiRequest<Sale>("/payments/sales", "POST", {
                      ...saleForm,
                      company_id: selectedCompany,
                      store_id: selectedStore,
                      operator_id: selectedOperator || null,
                      cash_register_id: selectedCashRegister || null,
                    });
                    setSelectedSale(sale.id);
                    setWebhookForm((prev) => ({
                      ...prev,
                      amount_cents: sale.expected_amount_cents,
                    }));
                    await refreshAll();
                  }, "Venda registrada.")
                }
                disabled={loading || !selectedCompany || !selectedStore}
              >
                Registrar venda esperada
              </Button>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Venda alvo</Label>
                  <select
                    className="h-10 w-full rounded-xl border border-input bg-white/80 px-3 text-sm"
                    value={selectedSale}
                    onChange={(e) => setSelectedSale(e.target.value)}
                  >
                    <option value="">Selecione uma venda</option>
                    {sales.map((sale) => (
                      <option key={sale.id} value={sale.id}>
                        {sale.external_ref} - {money(sale.expected_amount_cents)} -{" "}
                        {sale.status}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label>Chave Pix</Label>
                  <Input
                    value={chargeForm.pix_key}
                    onChange={(e) =>
                      setChargeForm((prev) => ({ ...prev, pix_key: e.target.value }))
                    }
                  />
                </div>
                <div>
                  <Label>Nome pagador</Label>
                  <Input
                    value={chargeForm.payer_name}
                    onChange={(e) =>
                      setChargeForm((prev) => ({ ...prev, payer_name: e.target.value }))
                    }
                  />
                </div>
              </div>

              <Button
                onClick={() =>
                  void handleAction(async () => {
                    const charge = await apiRequest<PixCharge>(
                      "/payments/pix/charges",
                      "POST",
                      {
                        ...chargeForm,
                        company_id: selectedCompany,
                        sale_id: selectedSale,
                      },
                    );
                    setLastCharge(charge);
                    setWebhookForm((prev) => ({
                      ...prev,
                      txid: charge.txid,
                      amount_cents: charge.amount_cents,
                    }));
                    await refreshAll();
                  }, "Cobrança Pix dinâmica gerada.")
                }
                disabled={loading || !selectedCompany || !selectedSale}
                variant="secondary"
              >
                <Zap className="mr-2 h-4 w-4" />
                Gerar cobrança Pix
              </Button>

              {lastCharge ? (
                <div className="rounded-2xl border border-border/60 bg-white/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Última cobrança gerada
                  </p>
                  <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-start">
                    {lastCharge.qr_code_base64 ? (
                      <img
                        src={lastCharge.qr_code_base64}
                        alt="QR preview"
                        className="h-40 w-40 rounded-xl border border-border"
                      />
                    ) : null}
                    <div className="flex-1 space-y-2">
                      <p className="text-sm">
                        <span className="font-semibold">TXID:</span> {lastCharge.txid}
                      </p>
                      <p className="text-sm">
                        <span className="font-semibold">Valor:</span>{" "}
                        {money(lastCharge.amount_cents)}
                      </p>
                      <Textarea readOnly value={lastCharge.qr_code_text} className="text-xs" />
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="rounded-2xl border border-border/60 bg-white/70 p-4">
                <p className="mb-3 text-sm font-semibold">Simular webhook de confirmação Pix</p>
                <div className="grid gap-3 md:grid-cols-3">
                  <div>
                    <Label>TXID</Label>
                    <Input
                      value={webhookForm.txid}
                      onChange={(e) =>
                        setWebhookForm((prev) => ({ ...prev, txid: e.target.value }))
                      }
                    />
                  </div>
                  <div>
                    <Label>End-to-end ID</Label>
                    <Input
                      value={webhookForm.end_to_end_id}
                      onChange={(e) =>
                        setWebhookForm((prev) => ({
                          ...prev,
                          end_to_end_id: e.target.value,
                        }))
                      }
                    />
                  </div>
                  <div>
                    <Label>Valor recebido (centavos)</Label>
                    <Input
                      type="number"
                      value={webhookForm.amount_cents}
                      onChange={(e) =>
                        setWebhookForm((prev) => ({
                          ...prev,
                          amount_cents: Number(e.target.value),
                        }))
                      }
                    />
                  </div>
                </div>
                <Button
                  className="mt-3"
                  onClick={() =>
                    void handleAction(async () => {
                      await apiRequest("/payments/pix/webhooks/confirmation", "POST", {
                        company_id: selectedCompany || null,
                        txid: webhookForm.txid,
                        end_to_end_id: webhookForm.end_to_end_id,
                        amount_cents: webhookForm.amount_cents,
                        raw_payload: { simulated: true, source: "dashboard" },
                      });
                      await refreshAll();
                    }, "Webhook processado e conciliação recalculada.")
                  }
                  disabled={loading || !webhookForm.txid}
                >
                  Confirmar pagamento (webhook)
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>3) Dashboard em Tempo Real</CardTitle>
              <CardDescription>
                Atualização periódica de métricas financeiras, eventos imutáveis e
                risco operacional.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Vendas totais</p>
                  <p className="text-2xl font-bold">{metrics?.total_sales ?? 0}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Vendas pagas</p>
                  <p className="text-2xl font-bold">{metrics?.paid_sales ?? 0}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Pendentes</p>
                  <p className="text-2xl font-bold">{metrics?.pending_sales ?? 0}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-3">
                  <p className="text-xs uppercase text-muted-foreground">Divergentes</p>
                  <p className="text-2xl font-bold">{metrics?.divergent_sales ?? 0}</p>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-border/60 bg-white/80 p-3">
                  <p className="text-xs text-muted-foreground">Esperado</p>
                  <p className="text-base font-semibold">
                    {money(metrics?.expected_total_cents)}
                  </p>
                </div>
                <div className="rounded-xl border border-border/60 bg-white/80 p-3">
                  <p className="text-xs text-muted-foreground">Recebido</p>
                  <p className="text-base font-semibold">
                    {money(metrics?.received_total_cents)}
                  </p>
                </div>
                <div className="rounded-xl border border-border/60 bg-white/80 p-3">
                  <p className="text-xs text-muted-foreground">Flags abertas</p>
                  <p className="text-base font-semibold">
                    {metrics?.open_fraud_flags ?? 0}
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-2xl border border-border/60 bg-white/70 p-3">
                <p className="mb-2 text-sm font-semibold">Últimos eventos do ledger</p>
                <div className="max-h-56 space-y-2 overflow-auto">
                  {(metrics?.latest_events ?? []).map((event) => (
                    <div
                      key={event.event_id}
                      className="rounded-lg border border-border/50 bg-white px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold">{event.event_type}</p>
                        <Badge variant="neutral">#{event.sequence_no}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {event.source} · {event.reference_id ?? "-"} ·{" "}
                        {event.amount_cents ? money(event.amount_cents) : "-"}
                      </p>
                    </div>
                  ))}
                  {(metrics?.latest_events ?? []).length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Sem eventos para o período.
                    </p>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4) Divergências e Sinais de Fraude</CardTitle>
              <CardDescription>
                O sistema reduz fraude operacional, mas não elimina 100% dos
                riscos. Itens abaixo exigem investigação.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="mb-2 text-sm font-semibold">Conciliações divergentes</p>
                <div className="space-y-2">
                  {divergences.slice(0, 6).map((item) => (
                    <div key={item.id} className="rounded-xl border border-border/60 bg-white/80 p-3">
                      <div className="flex items-center justify-between">
                        <Badge variant={metricTone(item.status)}>{item.status}</Badge>
                        <p className="text-xs text-muted-foreground">{item.txid ?? "-"}</p>
                      </div>
                      <p className="mt-2 text-sm">{item.reason}</p>
                      <p className="text-xs text-muted-foreground">
                        Esperado: {money(item.expected_amount_cents)} · Recebido:{" "}
                        {money(item.received_amount_cents)}
                      </p>
                    </div>
                  ))}
                  {divergences.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Nenhuma divergência recente.
                    </p>
                  ) : null}
                </div>
              </div>

              <div>
                <p className="mb-2 text-sm font-semibold">Flags de fraude operacional</p>
                <div className="space-y-2">
                  {fraudFlags.slice(0, 6).map((flag) => (
                    <div key={flag.id} className="rounded-xl border border-border/60 bg-white/80 p-3">
                      <div className="flex items-center justify-between">
                        <Badge variant={metricTone(flag.severity)}>{flag.severity}</Badge>
                        <p className="text-xs text-muted-foreground">{flag.flag_type}</p>
                      </div>
                      <p className="mt-2 text-sm">{flag.description}</p>
                    </div>
                  ))}
                  {fraudFlags.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sem flags abertas.</p>
                  ) : null}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>5) Fechamento Diário + IA</CardTitle>
              <CardDescription>
                Fechamento de caixa com recomendação operacional e resumo inteligente
                do dia financeiro.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() =>
                    void handleAction(async () => {
                      if (!selectedStore) throw new Error("Selecione uma loja.");
                      const report = await apiRequest<CloseoutReport>(
                        `/dashboard/closeout?company_id=${selectedCompany}&store_id=${selectedStore}&business_date=${selectedDate}`,
                      );
                      setCloseout(report);
                    }, "Relatório diário de fechamento gerado.")
                  }
                  disabled={loading || !selectedCompany || !selectedStore}
                >
                  Gerar fechamento
                </Button>

                <Button
                  variant="outline"
                  onClick={() =>
                    void handleAction(async () => {
                      if (!selectedStore) throw new Error("Selecione uma loja.");
                      const summary = await apiRequest<AiSummary>(
                        `/dashboard/ai-summary?company_id=${selectedCompany}&store_id=${selectedStore}&business_date=${selectedDate}`,
                      );
                      setAiSummary(summary);
                    }, "Resumo IA gerado.")
                  }
                  disabled={loading || !selectedCompany || !selectedStore}
                >
                  <ShieldAlert className="mr-2 h-4 w-4" />
                  Gerar resumo IA
                </Button>
              </div>

              {closeout ? (
                <div className="rounded-2xl border border-border/70 bg-white/80 p-4 text-sm">
                  <p className="font-semibold">
                    Fechamento: {money(closeout.totals.expected_total_cents)} esperado vs{" "}
                    {money(closeout.totals.received_total_cents)} recebido
                  </p>
                  <p className="text-muted-foreground">
                    Diferença: {money(closeout.totals.difference_cents)} ·{" "}
                    {closeout.totals.divergent_sales_count} vendas divergentes
                  </p>
                  {closeout.recommendations.length > 0 ? (
                    <ul className="mt-2 list-disc pl-5 text-muted-foreground">
                      {closeout.recommendations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}

              {aiSummary ? (
                <div className="rounded-2xl border border-border/70 bg-white/80 p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="font-semibold">Resumo IA</p>
                    <Badge variant={riskVariant}>{aiSummary.risk_level}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">{aiSummary.summary}</p>
                  {aiSummary.action_items.length > 0 ? (
                    <ul className="mt-2 list-disc pl-5 text-sm text-muted-foreground">
                      {aiSummary.action_items.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
