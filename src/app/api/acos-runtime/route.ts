import { NextResponse } from "next/server";
import { execSync } from "child_process";
import path from "path";

const READ_DB_SCRIPT = "/home/z/my-project/acos-runtime/read_db.py";

export async function GET() {
  try {
    const result = execSync(`python3 "${READ_DB_SCRIPT}"`, {
      encoding: "utf-8",
      timeout: 15000,
    });

    const data = JSON.parse(result.trim());
    return NextResponse.json(data);
  } catch (error) {
    console.error("ACOS Runtime data error:", error);
    return NextResponse.json(
      {
        error: "Failed to read ACOS Runtime data",
        concepts: [],
        entities: [],
        relationships: [],
        beliefs: [],
        goals: [],
        cognitiveState: null,
        semanticConcepts: [],
        semanticRelationships: [],
        stats: {
          totalConcepts: 0,
          totalEntities: 0,
          totalRelationships: 0,
          activeBeliefs: 0,
          weakenedBeliefs: 0,
          totalBeliefs: 0,
          activeGoals: 0,
          completedGoals: 0,
          pausedGoals: 0,
          totalGoals: 0,
          avgBeliefConfidence: 0,
          avgGoalProgress: 0,
          overallConfidence: 0,
          sessionCount: 0,
          relationshipTypes: {},
          conceptTypes: {},
        },
        version: "0.2.0",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
