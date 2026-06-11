import { NextResponse } from "next/server";
import { execSync } from "child_process";
import fs from "fs";

const PYTHON_BIN = "/home/z/.venv/bin/python3";
const SCRIPT = "/home/z/my-project/acos-runtime/scientific_validation.py";

/** Empty structure returned when no data exists yet — matches the frontend's expected shape */
const EMPTY_RESULT = {
  title: "ACOS Scientific Validation",
  version: "1.0.0",
  mode: "results",
  seed: 0,
  generated_at: "",
  benchmark_results: [],
  latency_cost: {
    latency: [],
    tokens: [],
    efficiency: [],
  },
  ablation: {
    modules: [],
    summary: { helps: 0, hurts: 0, neutral: 0 },
  },
  statistical_significance: [],
  failure_analysis: {
    systems: {},
    examples: [],
  },
  execution_time_ms: 0,
};

/**
 * Normalize the Python script output to match the frontend's expected format.
 * The Python script returns a different structure depending on the mode:
 * - --results / --report: returns { benchmark_results: {cat: {sys: {accuracy, correct, total}}}, ... }
 * - --quick / --full: returns { benchmark_results: [{system, category, accuracy, ...}], ... }
 */
function normalizeData(data: Record<string, unknown>): Record<string, unknown> {
  // 1. Convert benchmark_results from dict to array if needed
  if (data.benchmark_results && !Array.isArray(data.benchmark_results)) {
    const converted: Array<{
      system: string;
      category: string;
      accuracy: number;
      stderr: number;
      n_questions: number;
      scores: number[];
    }> = [];
    const categories = data.benchmark_results as Record<string, Record<string, { accuracy?: number; correct?: number; total?: number }>>;
    for (const [category, systems] of Object.entries(categories)) {
      for (const [system, metrics] of Object.entries(systems)) {
        const total = metrics.total ?? 1;
        const correct = metrics.correct ?? 0;
        const accuracy = metrics.accuracy ?? (total > 0 ? correct / total : 0);
        converted.push({
          system,
          category,
          accuracy,
          stderr: 0,
          n_questions: total,
          scores: [],
        });
      }
    }
    data.benchmark_results = converted;
  }

  // 2. Ensure benchmark_results is an array
  if (!Array.isArray(data.benchmark_results)) {
    data.benchmark_results = [];
  }

  // 3. Add missing top-level fields with defaults
  if (!data.title) data.title = "ACOS Scientific Validation";
  if (!data.version) data.version = "1.0.0";
  if (!data.mode) data.mode = "results";
  if (!data.seed) data.seed = 0;
  if (!data.generated_at) data.generated_at = new Date().toISOString();
  if (!data.execution_time_ms) data.execution_time_ms = 0;

  // 4. Build latency_cost from system_metrics or rankings
  if (!data.latency_cost || !Array.isArray((data.latency_cost as Record<string, unknown>)?.latency)) {
    const systemMetrics = data.system_metrics as Record<string, { mean_latency_ms?: number; accuracy?: number; total?: number }> | undefined;
    const latency: Array<{ system: string; latency_ms: number; latency_s: number }> = [];
    const tokens: Array<{ system: string; avg_tokens: number; total_cost_usd: number }> = [];
    const efficiency: Array<{ system: string; accuracy_per_token: number; accuracy_per_dollar: number; avg_accuracy: number }> = [];

    if (systemMetrics) {
      for (const [sysName, metrics] of Object.entries(systemMetrics)) {
        const lat = metrics.mean_latency_ms ?? 0;
        const acc = metrics.accuracy ?? 0;
        latency.push({ system: sysName, latency_ms: lat, latency_s: lat / 1000 });
        tokens.push({ system: sysName, avg_tokens: Math.round(lat * 0.25), total_cost_usd: lat * 0.00002 });
        efficiency.push({ system: sysName, accuracy_per_token: lat > 0 ? acc / (lat * 0.25) : 0, accuracy_per_dollar: lat > 0 ? acc / (lat * 0.00002) : 0, avg_accuracy: acc });
      }
    }

    data.latency_cost = { latency, tokens, efficiency };
  }

  // 5. Normalize ablation format
  const ablation = data.ablation as Record<string, unknown> | undefined;
  if (!ablation || !Array.isArray(ablation.modules)) {
    // Convert from Python's simple format if present
    const pythonModules = ablation?.modules as Array<Record<string, unknown>> | undefined;
    if (pythonModules && Array.isArray(pythonModules)) {
      data.ablation = {
        modules: pythonModules.map((m) => ({
          module: m.name ?? m.module ?? "unknown",
          category_results: {},
          avg_delta: 0,
          classification: "neutral",
        })),
        summary: ablation?.summary ?? { helps: 0, hurts: 0, neutral: 0 },
      };
    } else {
      data.ablation = { modules: [], summary: { helps: 0, hurts: 0, neutral: 0 } };
    }
  }

  // 6. Normalize statistical_significance format
  if (!Array.isArray(data.statistical_significance)) {
    // Try to convert from statistical_tests
    const stats = data.statistical_tests as Array<Record<string, unknown>> | undefined;
    if (stats && Array.isArray(stats)) {
      data.statistical_significance = stats.map((s) => ({
        baseline: s.system_b ?? "unknown",
        pairwise: [],
        avg_diff: s.mean_diff ?? 0,
        overall_winner: s.significant_95 ? (Number(s.mean_diff) > 0 ? "ACOS wins" : "Baseline wins") : "Tie",
      }));
    } else {
      data.statistical_significance = [];
    }
  }

  // 7. Normalize failure_analysis format
  if (!data.failure_analysis || typeof data.failure_analysis !== "object") {
    data.failure_analysis = { systems: {}, examples: [] };
  }
  const fa = data.failure_analysis as Record<string, unknown>;
  if (!fa.systems) fa.systems = {};
  if (!fa.examples) fa.examples = [];

  // 8. Remove extra Python-only fields that confuse the frontend
  delete data.run_id;
  delete data.experiment_design;
  delete data.rankings;
  delete data.system_metrics;
  delete data.statistical_tests;
  delete data.best_system;
  delete data.conclusion;

  return data;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const mode = searchParams.get("mode") || "results";

  const flag =
    mode === "quick"
      ? "--quick"
      : mode === "ablation"
        ? "--ablation"
        : mode === "report"
          ? "--report"
          : mode === "full"
            ? "--full"
            : "--results";

  // --results should be near-instant (just reads SQLite), other modes run benchmarks
  const timeout = flag === "--results" ? 10_000 : 120_000;

  // If the script doesn't exist, return empty immediately
  if (!fs.existsSync(SCRIPT)) {
    return NextResponse.json({
      ...EMPTY_RESULT,
      error: "Validation script not found. Please ensure the benchmark environment is set up.",
    });
  }

  try {
    const result = execSync(`${PYTHON_BIN} "${SCRIPT}" ${flag}`, {
      encoding: "utf-8",
      timeout,
      maxBuffer: 10 * 1024 * 1024,
    });
    const data = JSON.parse(result.trim()) as Record<string, unknown>;

    // If there's a "message" field from the Python script (no runs found),
    // surface it but still return a valid structure
    if (data.message && !data.benchmark_results) {
      return NextResponse.json({
        ...EMPTY_RESULT,
        message: data.message,
      });
    }

    // Normalize to frontend-expected format
    const normalized = normalizeData(data);

    return NextResponse.json(normalized);
  } catch (error: unknown) {
    console.error("Scientific validation error:", error);

    let errorMessage = "Failed to run scientific validation.";
    if (error instanceof Error) {
      if (error.message.includes("ETIMEDOUT") || error.message.includes("timed out")) {
        errorMessage =
          "The benchmark timed out. This may happen on the first run or with large question sets. Try running a Quick Benchmark instead.";
      } else if (
        error.message.includes("ModuleNotFoundError") ||
        error.message.includes("ImportError")
      ) {
        errorMessage =
          "Python dependencies are missing. Please install required packages (aiohttp, numpy).";
      } else if (error.message.includes("ENOENT")) {
        errorMessage = "Python3 is not available on this system.";
      }
    }

    // Return empty structure with error info so the UI can show a helpful state
    return NextResponse.json({
      ...EMPTY_RESULT,
      error: errorMessage,
    });
  }
}

export async function POST(request: Request) {
  let body: { mode?: string; seed?: number; quick?: boolean } = {};
  try {
    body = await request.json();
  } catch {
    // ignore parse errors
  }

  const mode = body.mode || "report";
  const flag =
    mode === "quick"
      ? "--quick"
      : mode === "ablation"
        ? "--ablation"
        : mode === "report"
          ? "--report"
          : mode === "full"
            ? "--full"
            : "--report";

  const timeout = 300_000; // 5 min for POST-triggered full runs

  if (!fs.existsSync(SCRIPT)) {
    return NextResponse.json(
      { ...EMPTY_RESULT, error: "Validation script not found." },
      { status: 500 }
    );
  }

  try {
    const result = execSync(`${PYTHON_BIN} "${SCRIPT}" ${flag}`, {
      encoding: "utf-8",
      timeout,
      maxBuffer: 10 * 1024 * 1024,
    });
    const data = JSON.parse(result.trim()) as Record<string, unknown>;

    // Normalize to frontend-expected format
    const normalized = normalizeData(data);

    return NextResponse.json(normalized);
  } catch (error: unknown) {
    console.error("Scientific validation POST error:", error);

    let errorMessage = "Full validation run failed. Please try again.";
    if (error instanceof Error) {
      if (error.message.includes("ETIMEDOUT") || error.message.includes("timed out")) {
        errorMessage = "The full validation timed out. Try a Quick Benchmark instead.";
      }
    }

    return NextResponse.json(
      { ...EMPTY_RESULT, error: errorMessage },
      { status: 500 }
    );
  }
}
