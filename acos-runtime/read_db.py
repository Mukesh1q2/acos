#!/usr/bin/env python3
"""Read ACOS Runtime SQLite database and output JSON for the Next.js API."""
import sqlite3
import json
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "acos.db")

# Limits to prevent massive JSON output that crashes Node.js JSON.parse()
MAX_RELATIONSHIPS = 200
MAX_SEMANTIC_CONCEPTS = 50
MAX_SEMANTIC_RELATIONSHIPS = 100
MAX_CONCEPTS = 200
MAX_ENTITIES = 100

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

    concepts = query(f"SELECT * FROM concepts ORDER BY name LIMIT {MAX_CONCEPTS}")
    entities = query(f"SELECT * FROM entities ORDER BY name LIMIT {MAX_ENTITIES}")
    relationships = query(
        f"""SELECT r.*, c1.name as source_name, c2.name as target_name 
           FROM relationships r 
           LEFT JOIN concepts c1 ON r.source_concept_id=c1.id 
           LEFT JOIN concepts c2 ON r.target_concept_id=c2.id 
           ORDER BY r.confidence DESC
           LIMIT {MAX_RELATIONSHIPS}"""
    )
    beliefs = query("SELECT * FROM beliefs ORDER BY confidence DESC")
    goals = query("SELECT * FROM goals ORDER BY priority DESC")
    cognitive_states = query("SELECT * FROM cognitive_states ORDER BY updated_at DESC LIMIT 1")
    semantic_concepts = query(f"SELECT * FROM semantic_concepts LIMIT {MAX_SEMANTIC_CONCEPTS}")
    semantic_relationships = query(f"SELECT * FROM semantic_relationships LIMIT {MAX_SEMANTIC_RELATIONSHIPS}")

    # Get total counts for accurate stats (without fetching all rows)
    def count(table):
        cur.execute(f"SELECT COUNT(*) FROM [{table}]")
        return cur.fetchone()[0]

    total_concepts = count("concepts")
    total_entities = count("entities")
    total_relationships = count("relationships")
    total_semantic_concepts = count("semantic_concepts")
    total_semantic_relationships = count("semantic_relationships")

    # Enrich relationships with source/target names for display
    concept_map = {c["id"]: c["name"] for c in concepts}
    for r in relationships:
        if not r.get("source_name"):
            r["source_name"] = concept_map.get(r["source_concept_id"], "Unknown")
        if not r.get("target_name"):
            r["target_name"] = concept_map.get(r["target_concept_id"], "Unknown")

    # Truncate long string fields to prevent massive JSON
    def truncate_str(val, max_len=500):
        if isinstance(val, str) and len(val) > max_len:
            return val[:max_len] + "..."
        return val

    # Parse JSON fields in beliefs and compute counts
    for b in beliefs:
        for field in ["supporting_evidence", "contradicting_evidence", "related_concept_ids"]:
            if field in b and isinstance(b[field], str):
                try:
                    b[field] = json.loads(b[field])
                except:
                    b[field] = []
        # Ensure evidence arrays are actually arrays
        supp = b.get("supporting_evidence", [])
        contra = b.get("contradicting_evidence", [])
        if not isinstance(supp, list):
            supp = []
        if not isinstance(contra, list):
            contra = []
        b["supporting_evidence"] = supp
        b["contradicting_evidence"] = contra
        b["supporting_evidence_count"] = len(supp)
        b["contradicting_evidence_count"] = len(contra)
        # Extract category from metadata or default
        cat = b.get("category")
        if not cat or (isinstance(cat, str) and not cat.strip()):
            b["category"] = "general"
        # Truncate long statement for display
        b["statement"] = truncate_str(b.get("statement", ""), 300)

    # Parse JSON fields in goals and convert priority to label
    priority_labels = {20: "CRITICAL", 15: "HIGH", 10: "NORMAL", 5: "LOW"}
    for g in goals:
        for field in ["subgoal_ids", "dependency_ids", "related_concept_ids", "related_belief_ids", "metadata"]:
            if field in g and isinstance(g[field], str):
                try:
                    g[field] = json.loads(g[field])
                except:
                    g[field] = [] if field != "metadata" else {}
        # Ensure arrays are arrays
        for field in ["subgoal_ids", "dependency_ids", "related_concept_ids", "related_belief_ids"]:
            if not isinstance(g.get(field), list):
                g[field] = []
        if not isinstance(g.get("metadata"), dict):
            g["metadata"] = {}
        # Convert integer priority to string label
        p = g.get("priority", 5)
        if isinstance(p, int):
            closest = min(priority_labels.keys(), key=lambda k: abs(k - p)) if p not in priority_labels else p
            g["priority"] = priority_labels.get(closest, "NORMAL")
        elif isinstance(p, str) and p.isdigit():
            closest = min(priority_labels.keys(), key=lambda k: abs(k - int(p))) if int(p) not in priority_labels else int(p)
            g["priority"] = priority_labels.get(closest, "NORMAL")
        elif isinstance(p, str):
            # Already a string label - normalize to uppercase
            g["priority"] = p.upper()
        else:
            g["priority"] = "NORMAL"
        # Truncate long description
        g["description"] = truncate_str(g.get("description", ""), 300)

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
        # Ensure types
        for field in ["beliefs", "goals", "active_thread_ids", "recent_memory_ids", "knowledge_graph_concept_ids"]:
            if not isinstance(cs.get(field), list):
                cs[field] = []
        for field in ["uncertainty_estimates", "metadata"]:
            if not isinstance(cs.get(field), dict):
                cs[field] = {}
        # Truncate long strings
        cs["last_query"] = truncate_str(cs.get("last_query", ""), 200)
        cs["last_synthesis"] = truncate_str(cs.get("last_synthesis", ""), 200)

    # Compute stats using total counts (not limited query results)
    active_beliefs = [b for b in beliefs if b.get("status") == "active"]
    weakened_beliefs = [b for b in beliefs if b.get("status") == "weakened"]
    active_goals_list = [g for g in goals if g.get("status") == "active"]
    completed_goals_list = [g for g in goals if g.get("status") == "completed"]
    paused_goals_list = [g for g in goals if g.get("status") == "paused"]

    avg_belief_conf = round(sum(b.get("confidence", 0) for b in active_beliefs) / max(len(active_beliefs), 1), 2)
    avg_goal_prog = round(sum(g.get("progress", 0) for g in active_goals_list) / max(len(active_goals_list), 1), 2)

    # Get relationship type distribution from full dataset
    cur.execute("SELECT relationship_type, COUNT(*) as cnt FROM relationships GROUP BY relationship_type ORDER BY cnt DESC")
    rel_types = {row[0]: row[1] for row in cur.fetchall()}

    # Get concept type distribution from full dataset
    cur.execute("SELECT concept_type, COUNT(*) as cnt FROM concepts GROUP BY concept_type ORDER BY cnt DESC")
    concept_types = {row[0]: row[1] for row in cur.fetchall()}

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
            "totalConcepts": total_concepts,
            "totalEntities": total_entities,
            "totalRelationships": total_relationships,
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

    # Use separators to reduce JSON size and ensure_ascii to avoid encoding issues
    output = json.dumps(result, default=str, ensure_ascii=True, separators=(',', ':'))
    print(output)
    conn.close()

if __name__ == "__main__":
    main()
