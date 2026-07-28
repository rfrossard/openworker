import { useEffect, useState } from "react";
import {
  getUsageDashboard,
  getUsageModels,
  getUsageAccounts,
  type DashboardData,
  type ProviderAccount,
} from "../api";
import { PanelHead } from "./IntegrationsView";
import {
  loadRoutingEvents,
  loadRoutingCostLimit,
  loadRoutingLimit,
  loadRoutingMinConfidence,
  loadRoutingMode,
  ROUTING_COST_LIMIT_KEY,
  ROUTING_LIMIT_KEY,
  ROUTING_MIN_CONFIDENCE_KEY,
  ROUTING_STRATEGY_KEY,
  saveRoutingMode,
  summarizeRoutingEvents,
  updateRoutingFeedback,
  type RoutingEvent,
  type RoutingFeedback,
  type RoutingConfidence,
  type RoutingCostLimit,
  type RoutingMode,
  type Strategy,
} from "./ModelRouterGuide";

const CARD = "rounded-xl2 border border-line bg-panel";
const COLORS = ["#3670b2", "#d08a32", "#5b9b70", "#9a6ab0", "#c65f55", "#55a3a3", "#7c8799"];
const API_MODEL_COLOR = "var(--accent)";
const LOCAL_MODEL_COLOR = "#5b9b70";
const money = (n: number, digits = 4) => `$${n.toFixed(digits)}`;
const count = (n: number) => new Intl.NumberFormat().format(n);

export function UsageDashboardView() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [models, setModels] = useState<any>(null);
  const [accounts, setAccounts] = useState<Record<string, ProviderAccount>>({});
  const [tab, setTab] = useState<"usage" | "models" | "providers" | "benchmarks" | "routing">("usage");
  const [modelScope, setModelScope] = useState<"all" | "configured">("configured");
  const [routingEvents, setRoutingEvents] = useState<RoutingEvent[]>(() => loadRoutingEvents());

  const loadUsage = () => getUsageDashboard().then(setData).catch(() => {});
  const loadAccounts = () => getUsageAccounts().then((value) => setAccounts(value.accounts)).catch(() => {});
  const load = () => {
    Promise.all([getUsageDashboard(), getUsageModels(), getUsageAccounts()])
      .then(([d, m, a]) => { setData(d); setModels(m); setAccounts(a.accounts); })
      .catch(() => {});
  };

  useEffect(() => {
    load();
    const refreshRouting = () => setRoutingEvents(loadRoutingEvents());
    const refreshVisible = () => {
      if (document.visibilityState === "visible") {
        loadUsage();
        loadAccounts();
      }
    };
    window.addEventListener("openworker:routing-event", refreshRouting);
    const refreshOnFocus = () => {
      loadUsage();
      loadAccounts();
    };
    window.addEventListener("focus", refreshOnFocus);
    document.addEventListener("visibilitychange", refreshVisible);
    const timer = setInterval(loadUsage, 5_000);
    const accountTimer = setInterval(loadAccounts, 30_000);
    return () => {
      clearInterval(timer);
      clearInterval(accountTimer);
      window.removeEventListener("openworker:routing-event", refreshRouting);
      window.removeEventListener("focus", refreshOnFocus);
      document.removeEventListener("visibilitychange", refreshVisible);
    };
  }, []);

  return (
    <main className="flex-1 min-w-0 flex bg-paper">
      <div className="flex-1 min-w-0 overflow-y-auto hairline-scroll">
        <div className="max-w-4xl mx-auto px-7 py-6">
          <PanelHead title="Usage" sub="Live model usage and estimated cost by day and OpenWorker session." />
          <div className="flex gap-5 border-b border-line mb-5">
            {(["usage", "models", "providers", "benchmarks", "routing"] as const).map((name) => (
              <button
                key={name}
                className={`pb-2 text-[13px] capitalize border-b-2 -mb-px ${
                  tab === name ? "border-accent text-ink font-medium" : "border-transparent text-muted"
                }`}
                onClick={() => { setTab(name); load(); setRoutingEvents(loadRoutingEvents()); }}
              >
                {name}
              </button>
            ))}
          </div>
          {!data || !models ? (
            <div className={`${CARD} p-5 text-[13px] text-muted`}>Loading usage data…</div>
          ) : <>
            {tab !== "providers" && tab !== "routing" && <ModelScopeFilter registry={models.registry} value={modelScope} onChange={setModelScope} />}
            {tab === "usage" ? (
            <UsageTab data={data} registry={filterRegistry(models.registry, modelScope)} accounts={accounts} media={models.media_capacity || []} />
          ) : tab === "models" ? (
            <ModelsTab registry={filterRegistry(models.registry, modelScope)} />
          ) : tab === "providers" ? (
            <ProvidersTab providers={models.provider_summary} accounts={accounts} />
          ) : tab === "benchmarks" ? (
            <BenchmarksTab
              data={filterBenchmarks(models.benchmarks || {}, models.registry, modelScope)}
              registry={filterRegistry(models.registry, modelScope)}
              meta={models.benchmark_meta || {}}
              updated={models.benchmarks_updated_at}
            />
          ) : (
            <RoutingTab events={routingEvents} sessions={data.sessions} />
          )}</>}
        </div>
      </div>
    </main>
  );
}

function RoutingTab({ events, sessions }: { events: RoutingEvent[]; sessions: DashboardData["sessions"] }) {
  const [routingMode, setRoutingMode] = useState<RoutingMode>(() => loadRoutingMode());
  const [strategy, setStrategy] = useState<Strategy>(() => {
    const value = localStorage.getItem(ROUTING_STRATEGY_KEY);
    return value === "quality" || value === "cost" ? value : "balanced";
  });
  const [historyLimit, setHistoryLimit] = useState<25 | 50 | 100>(() => loadRoutingLimit());
  const [minimumConfidence, setMinimumConfidence] = useState<RoutingConfidence>(() => loadRoutingMinConfidence());
  const [maximumEstimatedCost, setMaximumEstimatedCost] = useState<RoutingCostLimit>(() => loadRoutingCostLimit());
  const routingPerformance = summarizeRoutingEvents(events);
  const localCount = events.filter((event) => event.local).length;
  const estimatedSpend = events.reduce((sum, event) => sum + (event.estimatedCost || 0), 0);
  const sessionsById = new Map(sessions.map((session) => [session.id, session]));
  const linkedSessionIds = Array.from(new Set(events.map((event) => event.sessionId).filter(Boolean) as string[]));
  const linkedSessions = linkedSessionIds.map((id) => sessionsById.get(id)).filter(Boolean) as DashboardData["sessions"];
  const observedSpend = linkedSessions.reduce((sum, session) => sum + session.cost_usd, 0);
  const strategyCounts = events.reduce<Record<string, number>>((all, event) => {
    all[event.strategy] = (all[event.strategy] || 0) + 1;
    return all;
  }, {});
  const topStrategy = Object.entries(strategyCounts).sort((a, b) => b[1] - a[1])[0]?.[0];
  const strategyLabel = (strategy?: string) =>
    strategy === "quality" ? "Best quality" : strategy === "cost" ? "Lowest cost" : strategy === "balanced" ? "Balanced" : "—";
  return <div className="space-y-4">
    <section className={`${CARD} p-4`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-[13px] font-semibold">Routing configuration</h2>
          <p className="text-[10.5px] text-faint mt-0.5">These settings are stored locally and also apply to the Model advisor.</p>
        </div>
        <div className="inline-flex rounded-lg border border-line bg-paper p-0.5" aria-label="Routing mode">
          {([["manual", "Manual"], ["shadow", "Shadow"], ["automatic", "Automatic"]] as const).map(([key, label]) =>
            <button key={key} onClick={() => {
              setRoutingMode(key);
              saveRoutingMode(key);
            }} className={`px-2.5 py-1 rounded-md text-[10.5px] ${routingMode === key ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink"}`}>
              {label}
            </button>)}
        </div>
      </div>
      <div className="grid md:grid-cols-[1fr_auto_auto_auto] gap-4 mt-4 pt-4 border-t border-line">
        <div>
          <div className="text-[10px] text-faint mb-2">Default strategy</div>
          <div className="inline-flex rounded-lg border border-line bg-paper p-0.5">
            {([["quality", "Best quality"], ["balanced", "Balanced"], ["cost", "Lowest cost"]] as const).map(([key, label]) =>
              <button key={key} onClick={() => {
                setStrategy(key);
                localStorage.setItem(ROUTING_STRATEGY_KEY, key);
              }} className={`px-2.5 py-1 rounded-md text-[10.5px] ${strategy === key ? "bg-panel text-ink shadow-sm" : "text-muted hover:text-ink"}`}>
                {label}
              </button>)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-faint mb-2">Minimum confidence</div>
          <select
            className="px-2.5 py-1.5 rounded-lg border border-line bg-paper text-[10.5px] text-ink"
            value={minimumConfidence}
            onChange={(event) => {
              const value = Number(event.target.value) as RoutingConfidence;
              setMinimumConfidence(value);
              localStorage.setItem(ROUTING_MIN_CONFIDENCE_KEY, String(value));
            }}
          >
            <option value={60}>60% · Exploratory</option>
            <option value={70}>70% · Recommended</option>
            <option value={80}>80% · Conservative</option>
          </select>
        </div>
        <div>
          <div className="text-[10px] text-faint mb-2">Maximum API cost</div>
          <select
            className="px-2.5 py-1.5 rounded-lg border border-line bg-paper text-[10.5px] text-ink"
            value={maximumEstimatedCost}
            onChange={(event) => {
              const value = Number(event.target.value) as RoutingCostLimit;
              setMaximumEstimatedCost(value);
              localStorage.setItem(ROUTING_COST_LIMIT_KEY, String(value));
            }}
          >
            <option value={0.01}>$0.01 / send</option>
            <option value={0.05}>$0.05 / send · Recommended</option>
            <option value={0.25}>$0.25 / send</option>
            <option value={0}>No limit</option>
          </select>
        </div>
        <div>
          <div className="text-[10px] text-faint mb-2">Keep routing history</div>
          <select
            className="px-2.5 py-1.5 rounded-lg border border-line bg-paper text-[10.5px] text-ink"
            value={historyLimit}
            onChange={(event) => {
              const limit = Number(event.target.value) as 25 | 50 | 100;
              setHistoryLimit(limit);
              localStorage.setItem(ROUTING_LIMIT_KEY, String(limit));
              window.dispatchEvent(new CustomEvent("openworker:routing-event"));
            }}
          >
            <option value={25}>Latest 25</option>
            <option value={50}>Latest 50</option>
            <option value={100}>Latest 100</option>
          </select>
        </div>
      </div>
    </section>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Kpi label="Routing Decisions" value={count(events.length)} />
      <Kpi label="Linked Sessions" value={`${linkedSessions.length} / ${events.length}`} />
      <Kpi label="Estimated API Cost" value={money(estimatedSpend)} />
      <Kpi label="Observed Session Cost" value={money(observedSpend)} />
    </div>
    <section className={`${CARD} p-4`}>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div>
          <h2 className="text-[13px] font-semibold">Routing performance</h2>
          <p className="text-[10.5px] text-faint mt-0.5">Decision outcomes and explicit ratings from the locally stored history.</p>
        </div>
        <span className="text-[10px] text-faint">{routingPerformance.rated} rated decision{routingPerformance.rated === 1 ? "" : "s"}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RoutingMetric label="Applied rate" value={routingPerformance.appliedRate == null ? "—" : `${routingPerformance.appliedRate}%`} detail={`${routingPerformance.applied} applied`} />
        <RoutingMetric label="Guardrail blocks" value={count(routingPerformance.blocked)} detail={`${routingPerformance.automatic} automatic attempts`} />
        <RoutingMetric label="Positive feedback" value={routingPerformance.positiveRate == null ? "—" : `${routingPerformance.positiveRate}%`} detail={`${routingPerformance.positive} good choices`} />
        <RoutingMetric label="Needs improvement" value={count(routingPerformance.negative)} detail={`${routingPerformance.rated} rated`} />
      </div>
      <div className="mt-3 pt-3 border-t border-line flex flex-wrap gap-x-5 gap-y-1 text-[10px] text-faint">
        <span>Low confidence <strong className="text-ink font-medium">{routingPerformance.blockedByConfidence}</strong></span>
        <span>Over cost limit <strong className="text-ink font-medium">{routingPerformance.blockedByCost}</strong></span>
        <span>Unknown cost <strong className="text-ink font-medium">{routingPerformance.blockedByUnknownCost}</strong></span>
        <span>Shadow observations <strong className="text-ink font-medium">{routingPerformance.shadow}</strong></span>
      </div>
    </section>
    <div className={`${CARD} px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-[10.5px]`}>
      <span className="text-faint">Local selection <strong className="text-ink font-medium">{events.length ? `${Math.round(localCount / events.length * 100)}%` : "—"}</strong></span>
      <span className="text-faint">Most used strategy <strong className="text-ink font-medium">{strategyLabel(topStrategy)}</strong></span>
      <span className="text-faint">Responded sessions <strong className="text-ink font-medium">{linkedSessions.filter((session) => session.output_tokens > 0).length}</strong></span>
    </div>
    <section className={`${CARD} overflow-hidden`}>
      <div className="px-4 py-3 border-b border-line">
        <h2 className="text-[13px] font-semibold">Routing history</h2>
        <p className="text-[10.5px] text-faint mt-0.5">Stored locally on this device. Showing the latest {historyLimit} Shadow and Automatic decisions.</p>
      </div>
      {events.length ? <div className="overflow-x-auto">
        <table className="w-full text-left text-[11px]">
          <thead className="text-faint bg-paper"><tr>
            {["Time", "Strategy", "Recommendation", "Confidence", "Guardrail", "Task fit", "Execution", "Estimated", "Observed", "Status", "Feedback"].map((header) =>
              <th key={header} className="px-3 py-2 font-medium whitespace-nowrap">{header}</th>)}
          </tr></thead>
          <tbody>{events.map((event) => <tr key={event.id} className="border-t border-line">
            <td className="px-3 py-2 text-faint whitespace-nowrap">{new Date(event.timestamp).toLocaleString()}</td>
            <td className="px-3 py-2 text-muted whitespace-nowrap">{strategyLabel(event.strategy)}</td>
            <td className="px-3 py-2 text-ink max-w-[210px] truncate" title={event.label}>{event.label}</td>
            <td className="px-3 py-2 text-muted tabular-nums">{event.confidence != null ? `${event.confidence}%` : "—"}</td>
            <td className="px-3 py-2 whitespace-nowrap">
              {event.mode === "shadow"
                ? <span className="text-[#d08a32]">Shadow · {event.outcome === "applied" ? "would apply" : event.outcome === "below_confidence" ? "low confidence" : event.outcome === "above_cost" ? "over cost" : "cost unknown"}</span>
                : event.outcome === "below_confidence"
                ? <span className="text-[#d08a32]" title={`Kept ${event.actualModel || "the current model"}`}>Kept current</span>
                : event.outcome === "unknown_cost"
                  ? <span className="text-[#d08a32]" title={`Kept ${event.actualModel || "the current model"}`}>Cost unknown</span>
                  : event.outcome === "above_cost"
                    ? <span className="text-[#d08a32]" title={`Kept ${event.actualModel || "the current model"}`}>Over cost limit</span>
                : <span className="text-[#5b9b70]">Applied</span>}
            </td>
            <td className="px-3 py-2 text-muted">{event.taskTypes.join(", ")}</td>
            <td className="px-3 py-2 whitespace-nowrap">
              <span className={event.local ? "text-[#5b9b70]" : "text-accent"}>{event.local ? "Local Ollama" : "Paid / API"}</span>
            </td>
            <td className="px-3 py-2 text-muted tabular-nums">
              {event.estimatedCost == null ? "Unavailable" : money(event.estimatedCost)}
            </td>
            <td className="px-3 py-2 text-muted tabular-nums">
              {event.sessionId && sessionsById.get(event.sessionId)
                ? money(sessionsById.get(event.sessionId)!.cost_usd)
                : "Pending"}
            </td>
            <td className="px-3 py-2 whitespace-nowrap">
              {event.sessionId && sessionsById.get(event.sessionId)?.output_tokens
                ? <span className="text-[#5b9b70]">Responded</span>
                : <span className="text-faint">Pending</span>}
            </td>
            <td className="px-3 py-2">
              {event.mode === "shadow" || (event.outcome && event.outcome !== "applied") ? <span className="text-faint">Not applied</span> : <RoutingFeedbackControl event={event} />}
            </td>
          </tr>)}</tbody>
        </table>
      </div> : <div className="p-6 text-center">
        <div className="text-[12px] text-muted">No automatic routing decisions yet.</div>
        <div className="text-[10.5px] text-faint mt-1">Choose Shadow or Automatic routing to start building routing history.</div>
      </div>}
    </section>
    <div className={`${CARD} p-4 text-[10.5px] text-muted`}>
      Estimated cost uses the draft size, attachments, expected output, and Dashboard pricing. Observed cost and tokens are session-level estimates and may include multiple turns.
    </div>
  </div>;
}

function RoutingMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="rounded-lg border border-line bg-paper px-3 py-2.5">
    <div className="text-[9.5px] text-faint">{label}</div>
    <div className="text-[18px] font-semibold text-ink mt-0.5 tabular-nums">{value}</div>
    <div className="text-[9.5px] text-muted mt-0.5">{detail}</div>
  </div>;
}

const ROUTING_FEEDBACK_OPTIONS: { value: RoutingFeedback; label: string }[] = [
  { value: "good", label: "Good choice" },
  { value: "wrong_model", label: "Wrong model" },
  { value: "too_slow", label: "Too slow" },
  { value: "too_expensive", label: "Too expensive" },
  { value: "poor_result", label: "Poor result" },
];

function RoutingFeedbackControl({ event }: { event: RoutingEvent }) {
  return <select
    className="max-w-[125px] px-2 py-1 rounded-md border border-line bg-paper text-[10px] text-muted"
    value={event.feedback || ""}
    onChange={(change) => updateRoutingFeedback(event.id, change.target.value as RoutingFeedback)}
    aria-label={`Feedback for ${event.label}`}
  >
    <option value="" disabled>Rate decision</option>
    {ROUTING_FEEDBACK_OPTIONS.map((option) =>
      <option key={option.value} value={option.value}>{option.label}</option>)}
  </select>;
}

function filterRegistry(registry: Record<string, any>, scope: "all" | "configured") {
  return Object.fromEntries(Object.entries(registry).filter(([, model]) => scope === "all" || model.configured));
}

function filterBenchmarks(data: Record<string, any>, registry: Record<string, any>, scope: "all" | "configured") {
  return Object.fromEntries(Object.entries(data).filter(([name]) => scope === "all" || registry[name]?.configured));
}

function ModelScopeFilter({ registry, value, onChange }: {
  registry: Record<string, any>;
  value: "all" | "configured";
  onChange: (value: "all" | "configured") => void;
}) {
  const all = Object.keys(registry).length;
  const configured = Object.values(registry).filter((m: any) => m.configured).length;
  return <div className="flex items-center justify-between gap-3 mb-4">
    <span className="text-[11px] text-faint">Show models</span>
    <div className="inline-flex rounded-lg border border-line bg-panel p-0.5">
      {([["configured", `Configured (${configured})`], ["all", `All (${all})`]] as const).map(([key, label]) =>
        <button key={key} onClick={() => onChange(key)}
          className={`px-2.5 py-1 rounded-md text-[10.5px] ${value === key ? "bg-paper text-ink shadow-sm" : "text-muted hover:text-ink"}`}>
          {label}
        </button>)}
    </div>
  </div>;
}

function UsageTab({
  data, registry, accounts, media,
}: {
  data: DashboardData;
  registry: Record<string, any>;
  accounts: Record<string, ProviderAccount>;
  media: any[];
}) {
  const a = data.aggregates;
  const modelEntries = Object.entries(a.by_model);
  const today = new Date().toLocaleDateString("en-CA");
  const todayUsage = a.daily[today] || { cost: 0, tokens: 0, sessions: 0 };
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 text-[10px] text-faint">
        <span>Automatically refreshes every 5 seconds</span>
        <span>{a.updated_at ? `Updated ${new Date(a.updated_at).toLocaleTimeString()}` : ""}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Today's Cost" value={money(todayUsage.cost)} />
        <Kpi label="Today's Tokens" value={count(todayUsage.tokens)} />
        <Kpi label="Total Cost" value={money(a.total_cost_usd)} />
        <Kpi label="Avg / Session" value={money(a.session_count ? a.total_cost_usd / a.session_count : 0)} />
      </div>
      <CapacityPlanner registry={registry} accounts={accounts} media={media} />
      <OperationUsage operations={a.operation_models || {}} />
      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="Cost by Provider">
          <DonutChart values={Object.entries(a.by_provider).map(([label, v]) => ({ label, value: v.cost }))} />
        </ChartCard>
        <ChartCard title="Daily Cost Trend">
          <BarChart values={Object.entries(a.daily).map(([label, v]) => ({ label, value: v.cost }))} valueLabel={money} />
        </ChartCard>
        <ChartCard title="Cost by Model">
          <BarChart
            values={modelEntries.map(([label, v]) => ({
              label, value: v.cost, color: registry[label]?.local ? LOCAL_MODEL_COLOR : API_MODEL_COLOR,
            }))}
            valueLabel={money}
            modelLegend
          />
        </ChartCard>
        <ChartCard title="Tokens by Model">
          <BarChart
            values={modelEntries.map(([label, v]) => ({
              label, value: v.tokens, color: registry[label]?.local ? LOCAL_MODEL_COLOR : API_MODEL_COLOR,
            }))}
            valueLabel={count}
            modelLegend
          />
        </ChartCard>
      </div>
      <section className={`${CARD} overflow-hidden`}>
        <h2 className="px-4 py-3 text-[13px] font-semibold border-b border-line">Session history</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11.5px]">
            <thead className="text-faint bg-paper"><tr>
              {["Session", "Model", "Calls", "Paid operations", "Input", "Output", "Cost", "Source", "Updated"].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
            </tr></thead>
            <tbody>
              {data.sessions.map((s) => <tr key={s.id} className="border-t border-line">
                <td className="px-3 py-2 text-ink max-w-[190px] truncate" title={s.title}>{s.title}</td>
                <td className="px-3 py-2 text-muted whitespace-nowrap">{s.model}</td>
                <td className="px-3 py-2 text-muted">{s.model_calls}</td>
                <td className="px-3 py-2 text-muted whitespace-nowrap">
                  {Object.entries(s.operations || {}).map(([kind, units]) => `${units} ${kind}`).join(", ") || "—"}
                </td>
                <td className="px-3 py-2 text-muted">{count(s.input_tokens)}</td>
                <td className="px-3 py-2 text-muted">{count(s.output_tokens)}</td>
                <td className="px-3 py-2 text-ink">{money(s.cost_usd)}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className={s.measurement === "reported" ? "text-[#5b9b70]" : s.measurement === "mixed" ? "text-[#d08a32]" : "text-faint"}>
                    {s.measurement === "reported" ? "Provider reported" : s.measurement === "mixed" ? "Mixed" : "Estimated"}
                  </span>
                </td>
                <td className="px-3 py-2 text-faint whitespace-nowrap">{s.datetime ? new Date(`${s.datetime.replace(" ", "T")}Z`).toLocaleDateString() : "—"}</td>
              </tr>)}
            </tbody>
          </table>
          {!data.sessions.length && <div className="p-4 text-[12px] text-muted">No sessions yet.</div>}
        </div>
      </section>
      <p className="text-[11px] text-faint">Provider-reported token counts are used when available. Older sessions and providers without usage metadata use a clearly labeled local estimate.</p>
    </div>
  );
}

export function OperationUsage({ operations }: {
  operations: DashboardData["aggregates"]["operation_models"];
}) {
  const entries = Object.entries(operations).sort(([, a], [, b]) => b.cost - a.cost);
  return <section className={`${CARD} overflow-hidden`}>
    <div className="px-4 py-3 border-b border-line">
      <h2 className="text-[13px] font-semibold">Generated media costs</h2>
      <p className="text-[10px] text-faint mt-0.5">
        Successful paid generations recorded by OpenWorker. Estimates are separate from official provider balances.
      </p>
    </div>
    {entries.length ? <div className="overflow-x-auto">
      <table className="w-full text-left text-[11.5px]">
        <thead className="text-faint bg-paper"><tr>
          {["Type", "Provider", "Model", "Quantity", "Cost", "Source"].map((h) =>
            <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
        </tr></thead>
        <tbody>
          {entries.map(([name, item]) => <tr key={`${item.provider}-${item.model_id}`} className="border-t border-line">
            <td className="px-3 py-2 text-muted capitalize">{item.type}</td>
            <td className="px-3 py-2 text-muted">{item.provider}</td>
            <td className="px-3 py-2 text-ink" title={item.model_id}>{name}</td>
            <td className="px-3 py-2 text-muted">{count(item.units)}</td>
            <td className="px-3 py-2 text-ink">{money(item.cost)}</td>
            <td className="px-3 py-2 text-faint capitalize">{item.measurement}</td>
          </tr>)}
        </tbody>
      </table>
    </div> : <div className="p-4 text-[11.5px] text-muted">
      No billed image or audio generations have been recorded yet. A Gemini row appears after a successful, approved image generation.
    </div>}
  </section>;
}

const WORKLOADS = [
  { key: "prompt", label: "Average prompt", detail: "1K input · 500 output", input: 1_000, output: 500 },
  { key: "small", label: "Small app", detail: "8K input · 2K output", input: 8_000, output: 2_000 },
  { key: "medium", label: "Medium app", detail: "30K input · 8K output", input: 30_000, output: 8_000 },
  { key: "large", label: "Large app", detail: "100K input · 25K output", input: 100_000, output: 25_000 },
];

function CapacityPlanner({ registry, accounts, media }: {
  registry: Record<string, any>;
  accounts: Record<string, ProviderAccount>;
  media: any[];
}) {
  const names = Object.keys(registry);
  const [selected, setSelected] = useState(names.includes("deepseek-v4-flash") ? "deepseek-v4-flash" : names[0]);
  const activeName = registry[selected] ? selected : names[0];
  const model = registry[activeName] || {};
  const official = accounts[model.provider]?.balances?.find((b) => b.currency === "USD");
  const budget = official?.total || 1;
  const scope = official ? `With a US$ ${official.total.toFixed(2)} balance` : "Per US$ 1";
  const estimate = (input: number, output: number) => {
    const cost = (input * model.input_per_1m + output * model.output_per_1m) / 1_000_000;
    return cost > 0 ? Math.floor(budget / cost) : 0;
  };
  if (!names.length) return <section className={`${CARD} p-4 text-[12px] text-muted`}>No models configured. Add an API key or start Ollama.</section>;
  return <section className={`${CARD} p-4`}>
    <div className="flex items-start justify-between gap-3 mb-4">
      <div><h2 className="text-[13px] font-semibold">How much can I create?</h2>
        <p className="text-[10.5px] text-faint mt-0.5">{scope} · estimate based on typical token volume</p></div>
      <select className="max-w-[230px] px-2.5 py-1.5 rounded-lg border border-line bg-paper text-[11.5px] text-ink" value={activeName} onChange={(e) => setSelected(e.target.value)}>
        {names.map((name) => <option key={name} value={name}>{name}</option>)}
      </select>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {WORKLOADS.map((w) => <div key={w.key} className="rounded-lg bg-paper border border-line p-3">
        <div className="text-[10.5px] text-faint">{w.label}</div>
        <div className="text-[18px] font-semibold mt-0.5">
          {model.local ? "No API cost" : !model.pricing_known ? "Pricing unavailable" : `≈ ${count(estimate(w.input, w.output))}`}
        </div>
        <div className="text-[9.5px] text-faint mt-1">{w.detail}</div>
      </div>)}
    </div>
    <div className="grid md:grid-cols-3 gap-2 mt-3">
      {media.map((item) => <div key={`${item.provider}-${item.model}`} className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2.5">
        <div className="min-w-0"><div className="text-[10.5px] font-medium truncate">{item.model}</div><div className="text-[9.5px] text-faint capitalize">{item.kind} · {item.unit}</div></div>
        <div className="text-[13px] font-semibold whitespace-nowrap">≈ {count(Math.floor(1 / item.cost_per_unit))}<span className="text-[9px] text-faint font-normal"> / US$1</span></div>
      </div>)}
    </div>
    <p className="text-[9.5px] text-faint mt-3">Small, medium, and large apps are comparison scenarios, not limits. Caching, internal reasoning, tools, and files affect actual usage.</p>
  </section>;
}

const BENCHMARK_GROUPS = [
  { key: "reasoning", label: "Reasoning", metrics: ["gpqa"] },
  { key: "coding", label: "Coding", metrics: ["livecodebench", "swe_verified", "swe_pro", "aa_coding"] },
  { key: "tools", label: "Tools", metrics: ["tau2", "toolathlon"] },
  { key: "vision", label: "Vision", metrics: ["mmmu"] },
  { key: "context", label: "Long context", metrics: ["mrcr"] },
] as const;

function BenchmarksTab({ data, registry, meta, updated }: {
  data: Record<string, Record<string, number>>;
  registry: Record<string, any>;
  meta: Record<string, any>;
  updated: string;
}) {
  const [group, setGroup] = useState("reasoning");
  const activeGroup = BENCHMARK_GROUPS.find((item) => item.key === group) || BENCHMARK_GROUPS[0];
  const metrics = activeGroup.metrics.filter((key) => meta[key]);
  return <div className="space-y-4">
    <div className={`${CARD} overflow-hidden`}>
      <div className="p-4 border-b border-line">
        <div className="flex gap-2 flex-wrap">
          {BENCHMARK_GROUPS.map((item) => <button key={item.key} onClick={() => setGroup(item.key)}
            className={`px-2.5 py-1.5 rounded-lg text-[11px] border ${group === item.key ? "bg-accent text-white border-accent" : "bg-paper text-muted border-line"}`}>
            {item.label}
          </button>)}
        </div>
        <div className="mt-4">
          <ModelTypeLegend />
        </div>
      </div>
      {metrics.map((metric, index) =>
        <BenchmarkSection
          key={metric}
          metric={metric}
          data={data}
          registry={registry}
          meta={meta}
          divided={index > 0}
        />)}
    </div>
    <div className={`${CARD} p-4 text-[10.5px] text-muted`}>
      Published results available as of {updated}. Evaluations in the same category are grouped together, while each chart retains its own methodology and scale. For Ollama models, scores come from the equivalent official checkpoint and may vary with local quantization.
    </div>
  </div>;
}

function BenchmarkSection({ metric, data, registry, meta, divided }: {
  metric: string;
  data: Record<string, Record<string, number>>;
  registry: Record<string, any>;
  meta: Record<string, any>;
  divided: boolean;
}) {
  const values = Object.entries(data)
    .filter(([name]) => registry[name])
    .filter(([, scores]) => scores[metric] != null)
    .map(([label, scores]) => ({ label, value: scores[metric] }))
    .sort((a, b) => b.value - a.value);
  const best = values[0];
  return <section className={`p-4 ${divided ? "border-t border-line" : ""}`}>
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-[12.5px] font-semibold text-ink">{meta[metric]?.metric}</h3>
          <p className="text-[10px] text-faint mt-0.5">Higher is better</p>
        </div>
        <span className="text-[10.5px] text-faint whitespace-nowrap">{values.length} models evaluated</span>
      </div>
      <div className="grid md:grid-cols-[1fr_170px] gap-5">
        <div>
          {values.length
            ? <BarChart
                values={values.map((item) => ({
                  ...item,
                  label: item.label.replace(/^ollama:/, ""),
                  color: registry[item.label]?.local ? LOCAL_MODEL_COLOR : API_MODEL_COLOR,
                }))}
                valueLabel={(n) => n.toFixed(1)}
              />
            : <div className="py-8 text-[11px] text-muted">None of the displayed models has a published result for this evaluation.</div>}
        </div>
        <div className="rounded-xl2 bg-accentSoft border border-line p-4 self-start">
          <div className="text-[10px] text-muted uppercase tracking-wide">Best in this evaluation</div>
          <div className="text-[14px] font-semibold mt-1">{best?.label.replace(/^ollama:/, "") || "No data"}</div>
          {best && <div className="text-[24px] font-semibold text-accent mt-2">{best.value.toFixed(1)}</div>}
          <div className="text-[10px] text-faint mt-2">{meta[metric]?.metric}</div>
        </div>
      </div>
  </section>;
}

function ModelsTab({ registry }: { registry: Record<string, any> }) {
  return <DataTable
    headers={["Model", "Provider", "Family", "Input $/1M", "Output $/1M", "Status", "Tested", "Frontier", "Context"]}
    rows={Object.entries(registry).map(([name, m]) => [
      <span className="font-medium text-ink">{name}</span>, m.provider, m.family,
      m.pricing_known ? money(m.input_per_1m, 2) : "—",
      m.pricing_known ? money(m.output_per_1m, 2) : "—",
      <span className={m.status === "active" ? "text-[#47845d]" : "text-[#b44d45]"}>● {m.status}</span>,
      m.tested ? "✓" : "—",
      m.frontier ? <span className="px-1.5 py-0.5 rounded bg-[#d08a32]/15 text-[#b27424] text-[10px] font-semibold">FRONTIER</span> : "—",
      m.context,
    ])}
  />;
}

function ProvidersTab({ providers, accounts }: { providers: Record<string, any>; accounts: Record<string, ProviderAccount> }) {
  return <div className="space-y-4">
    <section>
      <h2 className="text-[13px] font-semibold mb-2">Provider balance & recorded usage</h2>
      <div className="grid md:grid-cols-2 gap-3">
        {Object.entries(accounts).map(([name, account]) => <AccountCard key={name} name={name} account={account} />)}
        {!Object.keys(accounts).length && <div className={`${CARD} p-4 text-[12px] text-muted`}>No configured provider exposes account billing data.</div>}
      </div>
      <p className="text-[10.5px] text-faint mt-2">Official balances and locally recorded estimates are labeled separately. This view refreshes every 30 seconds while Usage is open; credentials stay in the local server.</p>
    </section>
    <DataTable
      headers={["Provider", "Models", "Avg Input $/1M", "Avg Output $/1M", "Frontier Model", "Frontier Input", "Frontier Output", "Active"]}
      rows={Object.entries(providers).map(([name, p]) => [
        <span className="font-medium text-ink">{name}</span>, p.models,
        money(p.avg_input_cost, 2), money(p.avg_output_cost, 2), p.frontier_model,
        <span className="text-[#b27424]">{money(p.frontier_input, 2)}</span>,
        <span className="text-[#b27424]">{money(p.frontier_output, 2)}</span>, p.active_count,
      ])}
    />
  </div>;
}

export function formatAccountUpdatedAt(value?: string): string {
  if (!value) return "Update time unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Update time unavailable";
  return `Last updated ${new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(parsed)}`;
}

export function AccountCard({ name, account }: { name: string; account: ProviderAccount }) {
  const balance = account.balances?.[0];
  const good = account.status === "available" || account.status === "usage_available";
  return <div className={`${CARD} p-4`}>
    <div className="flex items-center justify-between">
      <span className="font-semibold text-[13px]">{name}</span>
      <span className={`text-[10.5px] ${good ? "text-[#47845d]" : "text-[#b27424]"}`}>
        ● {account.status.replace(/_/g, " ")}
      </span>
    </div>
    {balance ? <div className="mt-2">
      <div className="text-[22px] font-semibold">{balance.currency} {balance.total.toFixed(2)}</div>
      <div className="text-[10.5px] text-faint">Granted {balance.granted.toFixed(2)} · Topped up {balance.topped_up.toFixed(2)}</div>
    </div> : account.month_spend != null ? <div className="mt-2">
      <div className="text-[22px] font-semibold">{account.currency || "USD"} {account.month_spend.toFixed(2)}</div>
      <div className="text-[10.5px] text-faint">Official spend this month</div>
    </div> : account.local_spend != null && (account.units || 0) > 0 ? <div className="mt-2">
      <div className="text-[22px] font-semibold">USD {account.local_spend.toFixed(4)}</div>
      <div className="text-[10.5px] text-faint">
        {account.units} {account.unit_kind}{account.units === 1 ? "" : "s"} · locally recorded estimate
      </div>
      {account.message && <div className="text-[10.5px] text-muted mt-1">{account.message}</div>}
    </div> : <div className="text-[11.5px] text-muted mt-2">{account.message || "No financial data available."}</div>}
    <div className="text-[10px] text-faint mt-2" title={account.updated_at || undefined}>
      {formatAccountUpdatedAt(account.updated_at)}
    </div>
  </div>;
}

function DataTable({ headers, rows }: { headers: string[]; rows: any[][] }) {
  return <div className={`${CARD} overflow-x-auto`}>
    <table className="w-full text-left text-[11.5px]">
      <thead className="text-faint bg-paper"><tr>{headers.map((h) => <th key={h} className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>)}</tr></thead>
      <tbody>{rows.map((row, i) => <tr key={i} className="border-t border-line">{row.map((cell, j) => <td key={j} className="px-3 py-2 text-muted whitespace-nowrap">{cell}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

function Kpi({ label, value }: { label: string; value: string }) {
  return <div className={`${CARD} p-3.5`}><div className="text-[11px] text-faint">{label}</div><div className="mt-1 text-[19px] font-semibold text-ink">{value}</div></div>;
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className={`${CARD} p-4 min-h-[220px]`}><h2 className="text-[12.5px] font-semibold mb-3">{title}</h2>{children}</section>;
}

function ModelTypeLegend() {
  return <div className="flex items-center gap-4 mb-3 text-[9.5px] text-faint">
    <span className="inline-flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full" style={{ background: LOCAL_MODEL_COLOR }} />
      Local Ollama
    </span>
    <span className="inline-flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full" style={{ background: API_MODEL_COLOR }} />
      Paid / API
    </span>
  </div>;
}

function BarChart({ values, valueLabel, modelLegend = false }: {
  values: { label: string; value: number; color?: string }[];
  valueLabel: (n: number) => string;
  modelLegend?: boolean;
}) {
  const shown = [...values].sort((a, b) => b.value - a.value).slice(0, 7);
  const max = Math.max(...shown.map((v) => v.value), 0);
  return <div>
    {modelLegend && <ModelTypeLegend />}
    <div className="space-y-2">
    {shown.map((v) => <div key={v.label} className="grid grid-cols-[90px_1fr_auto] items-center gap-2 text-[10.5px]">
      <span className="truncate text-muted" title={v.label}>{v.label}</span>
      <svg viewBox="0 0 100 8" className="w-full h-2" preserveAspectRatio="none">
        <rect width="100" height="8" rx="4" fill="var(--paper)" />
        <rect width={max ? Math.max(1, v.value / max * 100) : 0} height="8" rx="4" fill={v.color || API_MODEL_COLOR} />
      </svg>
      <span className="text-faint tabular-nums">{valueLabel(v.value)}</span>
    </div>)}
    {!shown.length && <div className="text-[12px] text-muted">No data yet.</div>}
    </div>
  </div>;
}

function DonutChart({ values }: { values: { label: string; value: number }[] }) {
  const total = values.reduce((sum, v) => sum + v.value, 0);
  let offset = 0;
  return <div className="flex items-center gap-5">
    <svg viewBox="0 0 42 42" className="w-28 h-28 -rotate-90">
      <circle cx="21" cy="21" r="15.9" fill="none" stroke="var(--paper)" strokeWidth="7" />
      {values.map((v, i) => {
        const size = total ? v.value / total * 100 : 0;
        const node = <circle key={v.label} cx="21" cy="21" r="15.9" fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth="7" strokeDasharray={`${size} ${100 - size}`} strokeDashoffset={-offset} />;
        offset += size;
        return node;
      })}
    </svg>
    <div className="space-y-1.5 min-w-0">
      {values.map((v, i) => <div key={v.label} className="flex items-center gap-2 text-[10.5px]">
        <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
        <span className="text-muted truncate">{v.label}</span><span className="text-faint">{money(v.value)}</span>
      </div>)}
      {!values.length && <span className="text-[12px] text-muted">No data yet.</span>}
    </div>
  </div>;
}
