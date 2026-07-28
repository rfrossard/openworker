import { describe, expect, it } from "vitest";
import {
  buildModelRecommendations,
  evaluateRoutingGuardrails,
  feedbackInfluence,
  loadRoutingCostLimit,
  loadRoutingEvents,
  loadRoutingLimit,
  loadRoutingMinConfidence,
  loadRoutingMode,
  ROUTING_AUTO_KEY,
  ROUTING_COST_LIMIT_KEY,
  ROUTING_LIMIT_KEY,
  ROUTING_MIN_CONFIDENCE_KEY,
  ROUTING_MODE_KEY,
  saveRoutingEvent,
  saveRoutingMode,
  summarizeRoutingEvents,
  updateRoutingFeedback,
  type RoutingEvent,
} from "./ModelRouterGuide";

const dashboard: any = {
  registry: {
    "gpt-5.6-sol": { local: false, pricing_known: true, input_per_1m: 5, output_per_1m: 30 },
    "ollama:gemma4:31b": { local: true, pricing_known: true, input_per_1m: 0, output_per_1m: 0 },
  },
  benchmarks: {
    "gpt-5.6-sol": { livecodebench: 92, gpqa: 95 },
    "ollama:gemma4:31b": { livecodebench: 80, gpqa: 84 },
  },
};

const models = ["gpt-5.6-sol", "ollama:gemma4:31b"];
const labels = { "gpt-5.6-sol": "GPT-5.6 Sol", "ollama:gemma4:31b": "Gemma 4 31B" };

describe("model routing recommendations", () => {
  it("prefers the strongest evaluated model for quality", () => {
    const result = buildModelRecommendations(models, labels, dashboard, "Fix this TypeScript code bug", []);
    expect(result.find((item) => item.key === "quality")?.choice?.model).toBe("gpt-5.6-sol");
  });

  it("prefers a capable local model for lowest cost", () => {
    const result = buildModelRecommendations(models, labels, dashboard, "Analyze this strategy", []);
    expect(result.find((item) => item.key === "cost")?.choice?.model).toBe("ollama:gemma4:31b");
  });

  it("returns bounded confidence and a cost estimate", () => {
    const choice = buildModelRecommendations(models, labels, dashboard, "Analyze this research", [])
      .find((item) => item.key === "quality")!.choice!;
    expect(choice.confidence).toBeGreaterThanOrEqual(45);
    expect(choice.confidence).toBeLessThanOrEqual(96);
    expect(choice.estimatedCost).toBeGreaterThan(0);
  });

  it("does not alter rankings when there is no relevant feedback", () => {
    expect(feedbackInfluence("gpt-5.6-sol", "quality", ["coding"], [])).toEqual({
      adjustment: 0,
      samples: 0,
    });
  });

  it("caps feedback influence so benchmarks remain the primary signal", () => {
    const negativeHistory = Array.from({ length: 20 }, (_, index): RoutingEvent => ({
      id: String(index),
      timestamp: "2026-07-23T00:00:00Z",
      strategy: "quality",
      model: "gpt-5.6-sol",
      label: "GPT-5.6 Sol",
      local: false,
      taskTypes: ["coding"],
      qualityScore: 95,
      confidence: 88,
      feedback: "wrong_model",
    }));
    expect(feedbackInfluence("gpt-5.6-sol", "quality", ["coding"], negativeHistory)).toEqual({
      adjustment: -8,
      samples: 20,
    });
  });

  it("uses relevant feedback to break a close evaluation result and explains the adjustment", () => {
    const closeDashboard: any = {
      registry: {
        "model-a": { local: false, pricing_known: true, input_per_1m: 2, output_per_1m: 8 },
        "model-b": { local: false, pricing_known: true, input_per_1m: 2, output_per_1m: 8 },
      },
      benchmarks: {
        "model-a": { livecodebench: 82 },
        "model-b": { livecodebench: 79 },
      },
    };
    const history: RoutingEvent[] = [{
      id: "rated",
      timestamp: "2026-07-23T00:00:00Z",
      strategy: "quality",
      model: "model-a",
      label: "Model A",
      local: false,
      taskTypes: ["coding"],
      qualityScore: 82,
      confidence: 60,
      feedback: "wrong_model",
    }];
    const result = buildModelRecommendations(
      ["model-a", "model-b"],
      {},
      closeDashboard,
      "Fix this code bug",
      [],
      history,
    ).find((item) => item.key === "quality")!;
    expect(result.choice?.model).toBe("model-b");
    expect(result.reason).not.toContain("feedback");

    const modelAResult = buildModelRecommendations(
      ["model-a"],
      {},
      closeDashboard,
      "Fix this code bug",
      [],
      history,
    ).find((item) => item.key === "quality")!;
    expect(modelAResult.reason).toContain("1 relevant feedback rating applied (-4.0)");
  });
});

describe("routing history", () => {
  const event = (id: string): RoutingEvent => ({
    id,
    timestamp: "2026-07-23T00:00:00Z",
    strategy: "balanced",
    model: "gpt-5.6-sol",
    label: "GPT-5.6 Sol",
    local: false,
    taskTypes: ["reasoning"],
    estimatedCost: 0.02,
    qualityScore: 95,
    confidence: 88,
  });

  it("defaults to the latest 50 decisions and enforces the configured limit", () => {
    expect(loadRoutingLimit()).toBe(50);
    localStorage.setItem(ROUTING_LIMIT_KEY, "25");
    for (let index = 0; index < 30; index++) saveRoutingEvent(event(String(index)));
    expect(loadRoutingEvents()).toHaveLength(25);
    expect(loadRoutingEvents()[0].id).toBe("29");
  });

  it("stores explicit feedback without changing the decision", () => {
    saveRoutingEvent(event("one"));
    updateRoutingFeedback("one", "too_expensive");
    expect(loadRoutingEvents()[0]).toMatchObject({
      id: "one",
      model: "gpt-5.6-sol",
      feedback: "too_expensive",
    });
  });

  it("defaults to the recommended confidence guardrail and persists supported levels", () => {
    expect(loadRoutingMinConfidence()).toBe(70);
    localStorage.setItem(ROUTING_MIN_CONFIDENCE_KEY, "80");
    expect(loadRoutingMinConfidence()).toBe(80);
    localStorage.setItem(ROUTING_MIN_CONFIDENCE_KEY, "75");
    expect(loadRoutingMinConfidence()).toBe(70);
  });

  it("applies an automatic recommendation only when it reaches the guardrail", () => {
    expect(evaluateRoutingGuardrails({ confidence: 69, local: true }, 70, 0.05)).toBe("below_confidence");
    expect(evaluateRoutingGuardrails({ confidence: 70, local: true }, 70, 0.05)).toBe("applied");
    expect(evaluateRoutingGuardrails({ confidence: 96, local: true }, 80, 0.05)).toBe("applied");
  });

  it("defaults to a five-cent API cost ceiling and validates stored values", () => {
    expect(loadRoutingCostLimit()).toBe(0.05);
    localStorage.setItem(ROUTING_COST_LIMIT_KEY, "0.01");
    expect(loadRoutingCostLimit()).toBe(0.01);
    localStorage.setItem(ROUTING_COST_LIMIT_KEY, "0.10");
    expect(loadRoutingCostLimit()).toBe(0.05);
  });

  it("allows local models and blocks unknown or excessive paid estimates", () => {
    expect(evaluateRoutingGuardrails({ confidence: 80, local: true }, 70, 0.01)).toBe("applied");
    expect(evaluateRoutingGuardrails({ confidence: 80, local: false }, 70, 0.05)).toBe("unknown_cost");
    expect(evaluateRoutingGuardrails({ confidence: 80, local: false, estimatedCost: 0.06 }, 70, 0.05)).toBe("above_cost");
    expect(evaluateRoutingGuardrails({ confidence: 80, local: false, estimatedCost: 0.05 }, 70, 0.05)).toBe("applied");
    expect(evaluateRoutingGuardrails({ confidence: 80, local: false }, 70, 0)).toBe("applied");
  });

  it("returns neutral performance metrics for an empty history", () => {
    expect(summarizeRoutingEvents([])).toMatchObject({
      total: 0,
      automatic: 0,
      shadow: 0,
      applied: 0,
      blocked: 0,
      rated: 0,
      appliedRate: null,
      positiveRate: null,
    });
  });

  it("treats legacy decisions as applied and separates each guardrail outcome", () => {
    const events: RoutingEvent[] = [
      { ...event("legacy"), feedback: "good" },
      { ...event("applied"), outcome: "applied", feedback: "poor_result" },
      { ...event("confidence"), outcome: "below_confidence" },
      { ...event("cost"), outcome: "above_cost" },
      { ...event("unknown"), outcome: "unknown_cost" },
    ];
    expect(summarizeRoutingEvents(events)).toEqual({
      total: 5,
      automatic: 5,
      shadow: 0,
      applied: 2,
      blocked: 3,
      blockedByConfidence: 1,
      blockedByCost: 1,
      blockedByUnknownCost: 1,
      rated: 2,
      positive: 1,
      negative: 1,
      appliedRate: 40,
      positiveRate: 50,
    });
  });

  it("migrates the legacy auto preference and persists explicit routing modes", () => {
    localStorage.setItem(ROUTING_AUTO_KEY, "true");
    expect(loadRoutingMode()).toBe("automatic");
    saveRoutingMode("shadow");
    expect(localStorage.getItem(ROUTING_MODE_KEY)).toBe("shadow");
    expect(localStorage.getItem(ROUTING_AUTO_KEY)).toBe("false");
    expect(loadRoutingMode()).toBe("shadow");
  });

  it("keeps shadow observations out of automatic application metrics", () => {
    const events: RoutingEvent[] = [
      { ...event("automatic"), outcome: "applied", mode: "automatic" },
      { ...event("shadow-apply"), outcome: "applied", mode: "shadow" },
      { ...event("shadow-block"), outcome: "below_confidence", mode: "shadow" },
    ];
    expect(summarizeRoutingEvents(events)).toMatchObject({
      total: 3,
      automatic: 1,
      shadow: 2,
      applied: 1,
      blocked: 0,
      appliedRate: 100,
    });
  });
});
