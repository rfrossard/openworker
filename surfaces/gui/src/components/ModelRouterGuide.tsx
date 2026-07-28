import { useEffect, useMemo, useState } from "react";
import { getUsageModels } from "../api";
import type { Attachment } from "../types";
import { Icon } from "./Icon";

export type DashboardModels = Awaited<ReturnType<typeof getUsageModels>>;
export type Strategy = "quality" | "balanced" | "cost";
export type RoutingMode = "manual" | "shadow" | "automatic";
export type RoutingConfidence = 60 | 70 | 80;
export type RoutingCostLimit = 0 | 0.01 | 0.05 | 0.25;
export type RoutingOutcome = "applied" | "below_confidence" | "unknown_cost" | "above_cost";
export type RoutingFeedback = "good" | "wrong_model" | "too_slow" | "too_expensive" | "poor_result";
export type RoutingEvent = {
  id: string;
  timestamp: string;
  strategy: Strategy;
  model: string;
  label: string;
  local: boolean;
  taskTypes: string[];
  estimatedCost?: number;
  qualityScore: number;
  confidence: number;
  sessionId?: string;
  feedback?: RoutingFeedback;
  outcome?: RoutingOutcome;
  actualModel?: string;
  mode?: RoutingMode;
};

const ROUTING_HISTORY_KEY = "openworker.modelRouter.history";
export const ROUTING_AUTO_KEY = "openworker.modelRouter.auto";
export const ROUTING_STRATEGY_KEY = "openworker.modelRouter.strategy";
export const ROUTING_LIMIT_KEY = "openworker.modelRouter.historyLimit";
export const ROUTING_MIN_CONFIDENCE_KEY = "openworker.modelRouter.minimumConfidence";
export const ROUTING_COST_LIMIT_KEY = "openworker.modelRouter.maximumEstimatedCost";
export const ROUTING_MODE_KEY = "openworker.modelRouter.mode";

export function loadRoutingLimit(): 25 | 50 | 100 {
  const value = Number(localStorage.getItem(ROUTING_LIMIT_KEY) || 50);
  return value === 25 || value === 100 ? value : 50;
}

export function loadRoutingMinConfidence(): RoutingConfidence {
  const value = Number(localStorage.getItem(ROUTING_MIN_CONFIDENCE_KEY) || 70);
  return value === 60 || value === 80 ? value : 70;
}

export function loadRoutingCostLimit(): RoutingCostLimit {
  const value = Number(localStorage.getItem(ROUTING_COST_LIMIT_KEY) ?? 0.05);
  return value === 0 || value === 0.01 || value === 0.25 ? value : 0.05;
}

export function loadRoutingMode(): RoutingMode {
  const value = localStorage.getItem(ROUTING_MODE_KEY);
  if (value === "manual" || value === "shadow" || value === "automatic") return value;
  return localStorage.getItem(ROUTING_AUTO_KEY) === "true" ? "automatic" : "manual";
}

export function saveRoutingMode(mode: RoutingMode) {
  localStorage.setItem(ROUTING_MODE_KEY, mode);
  localStorage.setItem(ROUTING_AUTO_KEY, String(mode === "automatic"));
}

export function evaluateRoutingGuardrails(
  choice: { confidence: number; local: boolean; estimatedCost?: number },
  minimumConfidence: RoutingConfidence,
  maximumEstimatedCost: RoutingCostLimit,
): RoutingOutcome {
  if (choice.confidence < minimumConfidence) return "below_confidence";
  if (choice.local || maximumEstimatedCost === 0) return "applied";
  if (choice.estimatedCost == null) return "unknown_cost";
  return choice.estimatedCost <= maximumEstimatedCost ? "applied" : "above_cost";
}

export function loadRoutingEvents(): RoutingEvent[] {
  try {
    const value = JSON.parse(localStorage.getItem(ROUTING_HISTORY_KEY) || "[]");
    return Array.isArray(value) ? value.slice(0, loadRoutingLimit()) : [];
  } catch {
    return [];
  }
}

export function saveRoutingEvent(event: RoutingEvent) {
  localStorage.setItem(ROUTING_HISTORY_KEY, JSON.stringify([event, ...loadRoutingEvents()].slice(0, loadRoutingLimit())));
  window.dispatchEvent(new CustomEvent("openworker:routing-event"));
}

export function updateRoutingFeedback(id: string, feedback: RoutingFeedback) {
  const updated = loadRoutingEvents().map((event) => event.id === id ? { ...event, feedback } : event);
  localStorage.setItem(ROUTING_HISTORY_KEY, JSON.stringify(updated));
  window.dispatchEvent(new CustomEvent("openworker:routing-event"));
}

export function summarizeRoutingEvents(events: RoutingEvent[]) {
  const automaticEvents = events.filter((event) => event.mode !== "shadow");
  const shadow = events.length - automaticEvents.length;
  const applied = automaticEvents.filter((event) => !event.outcome || event.outcome === "applied").length;
  const blockedByConfidence = automaticEvents.filter((event) => event.outcome === "below_confidence").length;
  const blockedByCost = automaticEvents.filter((event) => event.outcome === "above_cost").length;
  const blockedByUnknownCost = automaticEvents.filter((event) => event.outcome === "unknown_cost").length;
  const rated = events.filter((event) => event.feedback);
  const positive = rated.filter((event) => event.feedback === "good").length;
  return {
    total: events.length,
    automatic: automaticEvents.length,
    shadow,
    applied,
    blocked: automaticEvents.length - applied,
    blockedByConfidence,
    blockedByCost,
    blockedByUnknownCost,
    rated: rated.length,
    positive,
    negative: rated.length - positive,
    appliedRate: automaticEvents.length ? Math.round(applied / automaticEvents.length * 100) : null,
    positiveRate: rated.length ? Math.round(positive / rated.length * 100) : null,
  };
}

const STRATEGIES: { key: Strategy; label: string; description: string }[] = [
  { key: "quality", label: "Best quality", description: "Prioritizes task fit and published evaluations." },
  { key: "balanced", label: "Balanced", description: "Balances capability, estimated API cost, and locality." },
  { key: "cost", label: "Lowest cost", description: "Prefers local or lower-priced models that fit the task." },
];

const normalize = (value: string) =>
  value.toLowerCase().replace(/^.*?:/, "").replace(/preview|latest/g, "").replace(/[^a-z0-9]/g, "");

function relatedEntry<T>(model: string, entries: Record<string, T>): [string, T] | undefined {
  if (entries[model]) return [model, entries[model]];
  const target = normalize(model);
  return Object.entries(entries).find(([name]) => {
    const candidate = normalize(name);
    return candidate === target || (candidate.length > 7 && (candidate.includes(target) || target.includes(candidate)));
  });
}

function taskProfile(prompt: string, attachments: Attachment[]) {
  const text = prompt.toLowerCase();
  const has = (words: string[]) => words.some((word) => text.includes(word));
  const vision = attachments.some((item) => item.kind === "image") ||
    has(["image", "photo", "screenshot", "diagram", "imagem", "foto"]);
  const coding = has(["code", "bug", "repository", "function", "api", "typescript", "python", "código", "erro"]);
  const tools = has(["send", "calendar", "email", "slack", "github", "update", "schedule", "enviar", "agenda"]);
  const longContext = attachments.length >= 3 ||
    has(["many files", "documents", "entire folder", "long report", "documentos", "pasta inteira"]);
  const reasoning = !coding && !vision && !tools || has(["analyze", "compare", "strategy", "research", "reason", "analise"]);
  const metrics = [
    ...(coding ? ["livecodebench", "swe_verified", "swe_pro", "aa_coding"] : []),
    ...(tools ? ["tau2", "toolathlon"] : []),
    ...(vision ? ["mmmu"] : []),
    ...(longContext ? ["mrcr"] : []),
    ...(reasoning ? ["gpqa"] : []),
  ];
  const labels = [
    ...(coding ? ["coding"] : []),
    ...(tools ? ["tool use"] : []),
    ...(vision ? ["vision"] : []),
    ...(longContext ? ["long context"] : []),
    ...(reasoning ? ["reasoning"] : []),
  ];
  return { metrics: metrics.length ? metrics : ["gpqa"], labels: labels.length ? labels : ["general work"], vision };
}

function fallbackQuality(model: string) {
  const name = model.toLowerCase();
  if (/5\.6-sol|opus|fable|3\.1-pro|glm-5\.2/.test(name)) return 88;
  if (/terra|sonnet|pro|70b|31b|large/.test(name)) return 76;
  if (/luna|flash|haiku|20b|8b|mini/.test(name)) return 62;
  return 55;
}

export function feedbackInfluence(
  model: string,
  strategy: Strategy,
  taskTypes: string[],
  history: RoutingEvent[],
) {
  const relevant = history
    .filter((event) =>
      event.model === model &&
      event.feedback &&
      event.taskTypes.some((task) => taskTypes.includes(task)),
    )
    .slice(0, 20);
  const raw = relevant.reduce((total, event, index) => {
    const recency = Math.max(0.5, 1 - index * 0.04);
    const strategyMatch = event.strategy === strategy ? 1 : 0.65;
    const weight = event.feedback === "good"
      ? 2
      : event.feedback === "wrong_model"
        ? -4
        : event.feedback === "poor_result"
          ? -3.5
          : event.feedback === "too_slow"
            ? -2.5
            : strategy === "cost"
              ? -4
              : strategy === "balanced"
                ? -2.5
                : -1;
    return total + weight * recency * strategyMatch;
  }, 0);
  return {
    adjustment: Math.max(-8, Math.min(8, raw)),
    samples: relevant.length,
  };
}

export function buildModelRecommendations(
  models: string[],
  labels: Record<string, string>,
  dashboard: DashboardModels,
  prompt: string,
  attachments: Attachment[],
  history: RoutingEvent[] = [],
) {
  const profile = taskProfile(prompt, attachments);
  const inputTokens = Math.ceil(prompt.length / 4) + attachments.reduce((sum, item) => {
    if (item.kind === "text") return sum + Math.ceil((item.text?.length || 0) / 4);
    return sum + 1_000;
  }, 0);
  const expectedOutputTokens = 700;
  const candidates = models.map((model) => {
    const registryEntry = relatedEntry(model, dashboard.registry || {});
    const benchmarkEntry = relatedEntry(model, dashboard.benchmarks || {});
    const spec: any = registryEntry?.[1] || {};
    const scores: Record<string, number> = benchmarkEntry?.[1] || {};
    const relevant = profile.metrics.map((metric) => scores[metric]).filter((score) => score != null);
    const quality = relevant.length
      ? relevant.reduce((sum, score) => sum + score, 0) / relevant.length
      : fallbackQuality(model);
    const local = spec.local === true || (model.startsWith("ollama:") && !model.endsWith(":cloud"));
    const knownPrice = spec.pricing_known !== false && (spec.input_per_1m != null || spec.output_per_1m != null);
    const blendedPrice = local ? 0 : knownPrice
      ? Number(spec.input_per_1m || 0) * 0.67 + Number(spec.output_per_1m || 0) * 0.33
      : 12;
    const affordability = local ? 100 : Math.max(0, 100 - blendedPrice * 4);
    const visionPenalty = profile.vision && !/gpt|claude|gemini|gemma4/.test(model.toLowerCase()) ? 25 : 0;
    const estimatedCost = local ? 0 : knownPrice
      ? (inputTokens * Number(spec.input_per_1m || 0) + expectedOutputTokens * Number(spec.output_per_1m || 0)) / 1_000_000
      : undefined;
    return {
      model,
      label: labels[model] || model.replace(/^.*?:/, ""),
      local,
      quality: Math.max(0, quality - visionPenalty),
      affordability,
      priced: knownPrice || local,
      taskTypes: profile.labels,
      estimatedCost,
      evidenceCount: relevant.length,
    };
  });

  const choose = (strategy: Strategy, used: Set<string>) => {
    const ranked = candidates
      .filter((item) => !used.has(item.model))
      .map((item) => {
        const feedback = feedbackInfluence(item.model, strategy, item.taskTypes, history);
        const baseRank = strategy === "quality"
          ? item.quality
          : strategy === "balanced"
            ? item.quality * 0.68 + item.affordability * 0.22 + (item.local ? 10 : 0)
            : item.affordability * 0.72 + item.quality * 0.18 + (item.local ? 10 : 0);
        return {
          ...item,
          rank: baseRank + feedback.adjustment,
          feedbackAdjustment: feedback.adjustment,
          feedbackSamples: feedback.samples,
        };
      })
      .sort((a, b) => b.rank - a.rank);
    const top = ranked[0];
    if (!top) return undefined;
    const gap = top.rank - (ranked[1]?.rank ?? top.rank - 12);
    const confidence = Math.round(Math.max(45, Math.min(96,
      55 + gap * 1.4 + Math.min(top.evidenceCount * 7, 21) + (top.priced ? 4 : 0),
    )));
    used.add(top.model);
    return { ...top, confidence };
  };

  const used = new Set<string>();
  return STRATEGIES.map((strategy) => {
    const choice = choose(strategy.key, used) || choose(strategy.key, new Set());
    const feedbackReason = choice?.feedbackSamples
      ? ` · ${choice.feedbackSamples} relevant feedback ${choice.feedbackSamples === 1 ? "rating" : "ratings"} applied (${choice.feedbackAdjustment >= 0 ? "+" : ""}${choice.feedbackAdjustment.toFixed(1)})`
      : "";
    const reason = choice
      ? `${choice.local ? "Runs locally" : choice.priced ? "Uses configured API pricing" : "Available through a configured provider"} · strong fit for ${profile.labels.join(", ")}${feedbackReason}`
      : "No compatible model is currently available.";
    return { ...strategy, choice, reason };
  });
}

export function ModelRouterGuide({ prompt, attachments, models, labels, current, strategy, routingMode, onStrategyChange, onRoutingModeChange, onSelect, onClose }: {
  prompt: string;
  attachments: Attachment[];
  models: string[];
  labels: Record<string, string>;
  current: string;
  strategy: Strategy;
  routingMode: RoutingMode;
  onStrategyChange: (strategy: Strategy) => void;
  onRoutingModeChange: (mode: RoutingMode) => void;
  onSelect: (model: string) => void;
  onClose: () => void;
}) {
  const [dashboard, setDashboard] = useState<DashboardModels | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getUsageModels().then(setDashboard).catch(() => setFailed(true));
  }, []);

  const options = useMemo(
    () => dashboard ? buildModelRecommendations(models, labels, dashboard, prompt, attachments, loadRoutingEvents()) : [],
    [models, labels, dashboard, prompt, attachments],
  );

  return <div className="max-w-3xl mx-auto mb-2 rounded-xl2 border border-line bg-panel shadow-lg overflow-hidden">
    <div className="flex items-start justify-between gap-3 px-4 py-3 border-b border-line">
      <div>
        <div className="flex items-center gap-2 text-[13px] font-semibold text-ink">
          <Icon name="sparkle" size={14} className="text-accent" />
          Model advisor
          <span className="px-1.5 py-0.5 rounded bg-paper text-[9px] font-medium text-faint">MANUAL</span>
        </div>
        <p className="text-[10.5px] text-faint mt-1">
          Recommendations use your draft, configured models, pricing, locality, Dashboard evaluations, and your explicit feedback.
        </p>
      </div>
      <button className="w-7 h-7 grid place-items-center rounded-md text-faint hover:text-ink hover:bg-paper" onClick={onClose} aria-label="Close model advisor">
        <Icon name="x" size={15} />
      </button>
    </div>
    {!prompt.trim() && !attachments.length && <div className="px-4 py-2 bg-paper text-[10.5px] text-muted">
      Add a prompt or attachment for task-specific recommendations. General recommendations are shown for now.
    </div>}
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 border-b border-line bg-paper">
      <div className="inline-flex rounded-lg border border-line bg-panel p-0.5">
        {STRATEGIES.map((item) => <button
          key={item.key}
          className={`px-2.5 py-1 rounded-md text-[10px] ${
            strategy === item.key ? "bg-paper text-ink shadow-sm" : "text-muted hover:text-ink"
          }`}
          onClick={() => onStrategyChange(item.key)}
        >
          {item.label}
        </button>)}
      </div>
      <select
        className="px-2.5 py-1.5 rounded-lg border border-line bg-panel text-[10.5px] text-ink"
        value={routingMode}
        onChange={(event) => onRoutingModeChange(event.target.value as RoutingMode)}
        aria-label="Routing mode"
      >
        <option value="manual">Manual</option>
        <option value="shadow">Shadow · observe only</option>
        <option value="automatic">Automatic</option>
      </select>
    </div>
    <div className="grid md:grid-cols-3 gap-2 p-3">
      {!dashboard && !failed && <div className="md:col-span-3 p-4 text-[11.5px] text-muted">Analyzing available models…</div>}
      {failed && <div className="md:col-span-3 p-4 text-[11.5px] text-muted">The Dashboard data could not be loaded.</div>}
      {options.map((option) => <div key={option.key} className={`rounded-lg border bg-paper p-3 flex flex-col min-w-0 ${
        strategy === option.key ? "border-accent" : "border-line"
      }`}>
        <div className="text-[11.5px] font-semibold text-ink">{option.label}</div>
        <div className="text-[9.5px] text-faint mt-0.5">{option.description}</div>
        <div className="text-[12px] font-medium text-ink mt-3 truncate" title={option.choice?.label}>
          {option.choice?.label || "Unavailable"}
        </div>
        <div className="text-[9.5px] text-muted mt-1 min-h-[30px]">{option.reason}</div>
        {option.choice && <div className="mt-2 text-[9.5px] text-faint">
          {option.choice.confidence}% confidence
        </div>}
        {option.choice && <button
          className={`mt-3 w-full rounded-lg border px-2.5 py-1.5 text-[10.5px] font-medium ${
            current === option.choice.model
              ? "border-line text-faint bg-panel cursor-default"
              : "border-accent text-accent hover:bg-accentSoft"
          }`}
          disabled={current === option.choice.model}
          onClick={() => onSelect(option.choice!.model)}
        >
          {current === option.choice.model ? "Currently selected" : "Use this model"}
        </button>}
      </div>)}
    </div>
    <div className="px-4 py-2.5 border-t border-line text-[9.5px] text-faint">
      {routingMode === "automatic"
        ? `${STRATEGIES.find((item) => item.key === strategy)?.label} will be applied only at ${loadRoutingMinConfidence()}%+ confidence${loadRoutingCostLimit() ? ` and up to $${loadRoutingCostLimit().toFixed(2)} estimated API cost` : ""}.`
        : routingMode === "shadow"
          ? "Shadow mode records what the router would do without changing your selected model."
          : "Nothing changes until you choose a model."} Published evaluations are guidance, not a guarantee for your specific task.
    </div>
  </div>;
}
