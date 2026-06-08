import { NextResponse } from "next/server";
import { execSync } from "child_process";
import fs from "fs";

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
    const result = execSync(`python3 "${SCRIPT}" ${flag}`, {
      encoding: "utf-8",
      timeout,
      maxBuffer: 10 * 1024 * 1024,
    });
    const data = JSON.parse(result.trim());

    // Normalize: if benchmark_results is an empty object {}, turn it into []
    if (data.benchmark_results && !Array.isArray(data.benchmark_results)) {
      data.benchmark_results = [];
    }

    // If there's a "message" field from the Python script (no runs found),
    // surface it but still return a valid structure
    if (data.message && !data.benchmark_results?.length) {
      return NextResponse.json({
        ...EMPTY_RESULT,
        message: data.message,
      });
    }

    return NextResponse.json(data);
  } catch (error: unknown) {
    console.error("Scientific validation error:", error);

    let errorMessage = "Failed to run scientific validation.";
    if (error instanceof Error) {
      if (error.message.includes("ETIMEDOUT") || error.message.includes("timed out")) {
        errorMessage =
          "The benchmark timed out. This may happen on the first run or with large question sets. Try running a Quick Benchmark instead.";
      } else if (
        error.message.includes("ModuleNotFoundError") ||
        error.message.includes("ImportError") ||
        error.message.includes("ModuleNotFoundError")
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
    const result = execSync(`python3 "${SCRIPT}" ${flag}`, {
      encoding: "utf-8",
      timeout,
      maxBuffer: 10 * 1024 * 1024,
    });
    const data = JSON.parse(result.trim());

    if (data.benchmark_results && !Array.isArray(data.benchmark_results)) {
      data.benchmark_results = [];
    }

    return NextResponse.json(data);
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
