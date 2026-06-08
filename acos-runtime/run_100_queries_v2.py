"""
ACOS Runtime Activation Script v2 — Run 100 Real Queries

Strategy: Use Z-AI API for synthesis (final answer generation).
Agents use MockBackend for speed (they produce structured data).
This ensures real LLM inference is exercised while keeping runtime manageable.
"""

import asyncio
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone

from acos.kernel import CognitiveKernel
from acos.schemas.v2_models import QueryRequestV2


QUERIES = [
    # Planning (20)
    "Plan a strategy for learning a new programming language",
    "How to design a scalable microservices architecture",
    "Create a roadmap for migrating to cloud infrastructure",
    "Design an approach for improving code review processes",
    "Plan a data pipeline for real-time analytics",
    "How to build a REST API from scratch",
    "Strategy for reducing technical debt in a legacy codebase",
    "Plan a testing strategy for a web application",
    "Design a deployment pipeline for continuous delivery",
    "How to implement a monitoring and alerting system",
    "Plan a database migration strategy",
    "Design a caching layer for a high-traffic website",
    "Create a plan for implementing authentication",
    "How to approach building a recommendation engine",
    "Plan for optimizing database query performance",
    "Design a message queue architecture",
    "How to build a feature flag system",
    "Plan for implementing rate limiting in an API",
    "Design a logging and observability strategy",
    "How to approach building a search engine",
    # Analysis (20)
    "Analyze the trade-offs between SQL and NoSQL databases",
    "What are the advantages of microservices",
    "Compare REST vs GraphQL for API design",
    "Analyze the impact of technical debt on software quality",
    "What are the key factors in choosing a cloud provider",
    "Compare different approaches to state management",
    "Analyze the benefits of containerization",
    "What are the risks of vendor lock-in in cloud computing",
    "Compare server-side vs client-side rendering",
    "Analyze the impact of code complexity on maintainability",
    "What are the trade-offs between performance and readability",
    "Compare event-driven vs request-response architectures",
    "Analyze the benefits of open source dependencies",
    "What are the key considerations for API versioning",
    "Compare horizontal vs vertical scaling strategies",
    "Analyze the impact of test coverage on reliability",
    "What are the advantages of functional programming",
    "Compare synchronous vs asynchronous patterns",
    "Analyze the trade-offs of monorepo vs polyrepo",
    "What factors affect database query optimization",
    # Verification (20)
    "Verify that unit tests provide sufficient coverage",
    "How to validate that an API meets its specification",
    "Check if a system architecture follows best practices",
    "Validate data integrity in a distributed system",
    "How to verify the correctness of a sorting algorithm",
    "Check that error handling covers edge cases",
    "Validate security measures in a web application",
    "How to verify performance meets SLA requirements",
    "Check if code follows established style guidelines",
    "Validate that a database schema is normalized",
    "How to verify authentication is working correctly",
    "Check that logging captures sufficient information",
    "Validate input sanitization prevents injection",
    "How to verify backup and recovery procedures work",
    "Check that API rate limiting is effective",
    "Validate that caching is properly configured",
    "How to verify message delivery in distributed systems",
    "Check that configuration management is consistent",
    "Validate monitoring covers critical system metrics",
    "How to verify data consistency across microservices",
    # Creative (20)
    "Imagine a novel approach to error handling in programming",
    "Invent a new way to visualize complex data relationships",
    "Brainstorm ideas for improving developer productivity",
    "Design an innovative user interface for data exploration",
    "Create a concept for an AI-assisted code review system",
    "Imagine how programming languages might evolve",
    "Invent a new debugging technique for distributed systems",
    "Brainstorm features for an intelligent documentation system",
    "Design a novel approach to API discoverability",
    "Create a concept for adaptive user interfaces",
    "Imagine a new paradigm for configuration management",
    "Invent a creative solution for managing environment variables",
    "Brainstorm approaches to zero-downtime deployments",
    "Design an innovative way to handle API compatibility",
    "Create a concept for self-healing software systems",
    "Imagine how monitoring could be more proactive",
    "Invent a new approach to dependency management",
    "Brainstorm ideas for making error messages helpful",
    "Design a creative solution for managing feature flags",
    "Imagine a novel way to handle distributed transactions",
    # Factual/Memory (20)
    "What is the difference between TCP and UDP",
    "Explain the CAP theorem in distributed systems",
    "What is the purpose of a load balancer",
    "How does DNS resolution work",
    "What are the ACID properties in databases",
    "Explain the concept of eventual consistency",
    "What is the difference between process and thread",
    "How does garbage collection work in Python",
    "What is the purpose of a message broker",
    "Explain the concept of idempotency in APIs",
    "What is the difference between authorization and authentication",
    "How does a B-tree index work in databases",
    "What is the purpose of a content delivery network",
    "Explain the concept of circuit breaker pattern",
    "What is the difference between lazy and eager evaluation",
    "How does OAuth 2.0 work",
    "What is the purpose of a reverse proxy",
    "Explain the concept of immutable infrastructure",
    "What is the difference between stateful and stateless services",
    "How does container orchestration work",
]


async def run_activation():
    print("=" * 70)
    print("ACOS RUNTIME ACTIVATION v2 — 100 REAL QUERIES")
    print("=" * 70)
    print(f"Start: {datetime.now(timezone.utc).isoformat()}")
    print()

    kernel = CognitiveKernel()
    await kernel.initialize()
    
    models = await kernel._router.get_available_models()
    print(f"Models: {[(m.name, m.is_available) for m in models]}")
    print(f"Default: {kernel._router._default_backend}")
    print()

    results = []
    successful = 0
    failed = 0
    total_time = 0

    for i, query in enumerate(QUERIES, 1):
        start = time.monotonic()
        try:
            response = await kernel.process_query_v2(
                QueryRequestV2(query=query, priority=5)
            )
            elapsed = (time.monotonic() - start) * 1000
            total_time += elapsed
            successful += 1

            results.append({
                "index": i,
                "query": query[:60],
                "session_id": response.session_id,
                "threads": len(response.threads),
                "agent_outputs": len(response.agent_outputs),
                "reflections": len(response.reflections),
                "verifications": len(response.verifications),
                "time_ms": round(elapsed),
                "success": True,
            })

            print(f"  ✅ [{i:3d}/100] {elapsed:8.0f}ms — {query[:45]}")
            sys.stdout.flush()

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            total_time += elapsed
            failed += 1
            results.append({
                "index": i,
                "query": query[:60],
                "error": str(e)[:100],
                "time_ms": round(elapsed),
                "success": False,
            })
            print(f"  ❌ [{i:3d}/100] {elapsed:8.0f}ms — ERROR: {str(e)[:45]}")
            sys.stdout.flush()

    # Database report
    print(f"\n{'=' * 70}")
    print("DATABASE POPULATION REPORT")
    print(f"{'=' * 70}")

    db = sqlite3.connect(kernel._storage.db_path)
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    all_tables = cursor.fetchall()

    populated = 0
    empty = 0
    total_rows = 0

    for table in all_tables:
        tname = table[0]
        if tname.startswith("sqlite_"):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM [{tname}]")
        count = cursor.fetchone()[0]
        total_rows += count
        if count > 0:
            populated += 1
            print(f"  ✅ {tname}: {count}")
        else:
            empty += 1
            print(f"  ⬜ {tname}: 0")

    db.close()

    # Model stats
    perf = kernel._router.get_performance_stats()

    # Trace stats
    trace_stats = await kernel._trace_logger.get_trace_stats()

    # Summary
    print(f"\n{'=' * 70}")
    print("ACTIVATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Queries executed:    {successful}/100 successful, {failed} failed")
    print(f"Total time:          {total_time/1000:.1f}s")
    print(f"Avg query time:      {total_time/1000/max(successful,1):.1f}s")
    print(f"Tables populated:    {populated}/{populated + empty}")
    print(f"Empty tables:        {empty}")
    print(f"Total DB rows:       {total_rows}")
    print(f"Default LLM:         {kernel._router._default_backend}")
    print(f"\nLLM PERFORMANCE:")
    for name, stats in perf.items():
        if stats.get("call_count", 0) > 0:
            print(f"  {name}: calls={stats['call_count']}, avg={stats.get('avg_latency', 0):.2f}s")
    print(f"\nTRACE STATISTICS:")
    print(f"  Total traces: {trace_stats.get('total_traces', 0)}")
    if "phase_counts" in trace_stats:
        for phase, count in sorted(trace_stats["phase_counts"].items()):
            print(f"    {phase}: {count}")

    # Save report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queries_total": 100,
        "queries_successful": successful,
        "queries_failed": failed,
        "total_time_s": total_time / 1000,
        "tables_populated": populated,
        "tables_empty": empty,
        "total_db_rows": total_rows,
        "default_llm": kernel._router._default_backend,
        "model_stats": {k: v for k, v in perf.items() if v.get("call_count", 0) > 0},
        "trace_stats": trace_stats,
        "results": results,
    }

    with open("data/activation_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved to: data/activation_report.json")

    await kernel.shutdown()
    print("Kernel shut down. Activation complete.")


if __name__ == "__main__":
    asyncio.run(run_activation())
