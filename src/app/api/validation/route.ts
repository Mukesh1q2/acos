import { NextResponse } from "next/server";
import { execSync } from "child_process";
import path from "path";

const VALIDATION_SCRIPT = "/home/z/my-project/acos-runtime/run_validation.py";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const quick = searchParams.get("quick") === "true";
    const seed = searchParams.get("seed") || "42";

    const cmd = `python3 "${VALIDATION_SCRIPT}" ${quick ? "--quick" : ""} --seed ${seed}`;

    const result = execSync(cmd, {
      encoding: "utf-8",
      timeout: 120000,
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json(data);
  } catch (error) {
    console.error("Validation Lab error:", error);
    return NextResponse.json(
      {
        error: "Failed to run Validation Lab",
        title: "ACOS Validation Lab Report",
        version: "1.0",
        conclusion: "Validation failed to execute. Please try again.",
        strengths: [],
        weaknesses: [],
        recommended_changes: [
          "Ensure Python dependencies are installed",
          "Check that the ACOS runtime is available",
        ],
        summary: {
          overall_score: null,
          conclusion: "Validation execution failed",
          strengths_count: 0,
          weaknesses_count: 0,
          recommendations_count: 2,
          execution_time_ms: 0,
          tournament_winner: null,
          rankings: [],
          emergence_score: 0,
          emergent_capabilities: [],
          health_score: 0,
          failures_detected: 0,
          acos_category_scores: {},
        },
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      quick = true,
      seed = 42,
      nTestCases,
      nAbCases,
    } = body;

    let cmd = `python3 "${VALIDATION_SCRIPT}"`;
    if (quick) cmd += " --quick";
    cmd += ` --seed ${seed}`;
    if (nTestCases) cmd += ` --n-test-cases ${nTestCases}`;
    if (nAbCases) cmd += ` --n-ab-cases ${nAbCases}`;

    const result = execSync(cmd, {
      encoding: "utf-8",
      timeout: 180000,
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json(data);
  } catch (error) {
    console.error("Validation Lab POST error:", error);
    return NextResponse.json(
      {
        error: "Failed to run Validation Lab",
        conclusion: "Validation execution failed",
        summary: {
          overall_score: null,
          conclusion: "Validation execution failed",
          execution_time_ms: 0,
        },
      },
      { status: 500 }
    );
  }
}
