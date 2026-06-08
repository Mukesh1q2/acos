#!/usr/bin/env python3
"""Read ACOS Runtime SQLite database and output JSON for the Next.js API."""
import sqlite3
import json
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "acos.db")

def main():
    if not os.path.exists(DB_PATH):
        print(json.dumps({"error": f"Database not found at {DB_PATH}"}))
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def query(sql):
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]

    concepts = query("SELECT * FROM concepts ORDER BY name")
    entities = query("SELECT * FROM entities ORDER BY name")
    relationships = query(
        """SELECT r.*, c1.name as source_name, c2.name as target_name 
           FROM relationships r 
           LEFT JOIN concepts c1 ON r.source_concept_id=c1.id 
           LEFT JOIN concepts c2 ON r.target_concept_id=c2.id 
           ORDER BY r.relationship_type"""
    )
    beliefs = query("SELECT * FROM beliefs ORDER BY confidence DESC")
    goals = query("SELECT * FROM goals ORDER BY priority DESC")
    cognitive_states = query("SELECT * FROM cognitive_states ORDER BY updated_at DESC LIMIT 1")
    semantic_concepts = query("SELECT * FROM semantic_concepts LIMIT 50")
    semantic_relationships = query("SELECT * FROM semantic_relationships LIMIT 50")

    # Enrich relationships with source/target names for display
    concept_map = {c["id"]: c["name"] for c in concepts}
    for r in relationships:
        if not r.get("source_name"):
            r["source_name"] = concept_map.get(r["source_concept_id"], "Unknown")
        if not r.get("target_name"):
            r["target_name"] = concept_map.get(r["target_concept_id"], "Unknown")

    # Parse JSON fields in beliefs
    for b in beliefs:
        for field in ["supporting_evidence", "contradicting_evidence", "related_concept_ids"]:
            if field in b and isinstance(b[field], str):
                try:
                    b[field] = json.loads(b[field])
                except:
                    b[field] = []

    # Parse JSON fields in goals
    for g in goals:
        for field in ["subgoal_ids", "dependency_ids", "related_concept_ids", "related_belief_ids", "metadata"]:
            if field in g and isinstance(g[field], str):
                try:
                    g[field] = json.loads(g[field])
                except:
                    g[field] = [] if field != "metadata" else {}

    # Parse JSON fields in cognitive state
    cs = cognitive_states[0] if cognitive_states else None
    if cs:
        for field in ["beliefs", "goals", "active_thread_ids", "recent_memory_ids",
                       "uncertainty_estimates", "knowledge_graph_concept_ids", "metadata"]:
            if field in cs and isinstance(cs[field], str):
                try:
                    cs[field] = json.loads(cs[field])
                except:
                    cs[field] = {} if field in ("uncertainty_estimates", "metadata") else []

    # Compute stats
    active_beliefs = [b for b in beliefs if b.get("status") == "active"]
    weakened_beliefs = [b for b in beliefs if b.get("status") == "weakened"]
    active_goals_list = [g for g in goals if g.get("status") == "active"]
    completed_goals_list = [g for g in goals if g.get("status") == "completed"]
    paused_goals_list = [g for g in goals if g.get("status") == "paused"]

    avg_belief_conf = round(sum(b.get("confidence", 0) for b in active_beliefs) / max(len(active_beliefs), 1), 2)
    avg_goal_prog = round(sum(g.get("progress", 0) for g in active_goals_list) / max(len(active_goals_list), 1), 2)

    rel_types = {}
    for r in relationships:
        t = r.get("relationship_type", "unknown")
        rel_types[t] = rel_types.get(t, 0) + 1

    concept_types = {}
    for c in concepts:
        t = c.get("concept_type", "unknown")
        concept_types[t] = concept_types.get(t, 0) + 1

    result = {
        "concepts": concepts,
        "entities": entities,
        "relationships": relationships,
        "beliefs": beliefs,
        "goals": goals,
        "cognitiveState": cs,
        "semanticConcepts": semantic_concepts,
        "semanticRelationships": semantic_relationships,
        "stats": {
            "totalConcepts": len(concepts),
            "totalEntities": len(entities),
            "totalRelationships": len(relationships),
            "activeBeliefs": len(active_beliefs),
            "weakenedBeliefs": len(weakened_beliefs),
            "totalBeliefs": len(beliefs),
            "activeGoals": len(active_goals_list),
            "completedGoals": len(completed_goals_list),
            "pausedGoals": len(paused_goals_list),
            "totalGoals": len(goals),
            "avgBeliefConfidence": avg_belief_conf,
            "avgGoalProgress": avg_goal_prog,
            "overallConfidence": cs.get("overall_confidence", 0.5) if cs else 0.5,
            "sessionCount": cs.get("session_count", 0) if cs else 0,
            "relationshipTypes": rel_types,
            "conceptTypes": concept_types,
        },
        "version": "0.2.0",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

    print(json.dumps(result, default=str))
    conn.close()

if __name__ == "__main__":
    main()
