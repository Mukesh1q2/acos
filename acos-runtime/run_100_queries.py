"""
ACOS Runtime Activation Script — Run 100 Real Queries

Executes 100 diverse queries through the CognitiveKernel to:
1. Populate all database tables
2. Generate trace logs
3. Exercise the full cognitive pipeline
4. Measure real LLM usage

DO NOT add new modules.
DO NOT add new schemas.
Only activate what exists.
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone

from acos.kernel import CognitiveKernel
from acos.schemas.v2_models import QueryRequestV2


# 100 diverse queries covering different cognitive domains
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
    "Create a plan for implementing authentication and authorization",
    "How to approach building a recommendation engine",
    "Plan for optimizing database query performance",
    "Design a message queue architecture for async processing",
    "How to build a feature flag system",
    "Plan for implementing rate limiting in an API",
    "Design a logging and observability strategy",
    "How to approach building a search engine for documentation",

    # Analysis (20)
    "Analyze the trade-offs between SQL and NoSQL databases",
    "What are the advantages and disadvantages of microservices",
    "Compare REST vs GraphQL for API design",
    "Analyze the impact of technical debt on software quality",
    "What are the key factors in choosing a cloud provider",
    "Compare different approaches to state management in web apps",
    "Analyze the benefits of containerization for deployment",
    "What are the risks of vendor lock-in in cloud computing",
    "Compare server-side rendering vs client-side rendering",
    "Analyze the impact of code complexity on maintainability",
    "What are the trade-offs between performance and readability",
    "Compare event-driven vs request-response architectures",
    "Analyze the benefits and risks of open source dependencies",
    "What are the key considerations for API versioning",
    "Compare horizontal vs vertical scaling strategies",
    "Analyze the impact of test coverage on software reliability",
    "What are the advantages of functional programming",
    "Compare synchronous vs asynchronous communication patterns",
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
    "Validate that a database schema is properly normalized",
    "How to verify authentication is working correctly",
    "Check that logging captures sufficient information",
    "Validate input sanitization prevents injection attacks",
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
    "Brainstorm ideas for improving developer productivity tools",
    "Design an innovative user interface for data exploration",
    "Create a concept for an AI-assisted code review system",
    "Imagine how programming languages might evolve in 10 years",
    "Invent a new debugging technique for distributed systems",
    "Brainstorm features for an intelligent documentation system",
    "Design a novel approach to API discoverability",
    "Create a concept for adaptive user interfaces",
    "Imagine a new paradigm for configuration management",
    "Invent a creative solution for managing environment variables",
    "Brainstorm approaches to zero-downtime deployments",
    "Design an innovative way to handle API backwards compatibility",
    "Create a concept for self-healing software systems",
    "Imagine how monitoring could be more proactive",
    "Invent a new approach to dependency management",
    "Brainstorm ideas for making error messages more helpful",
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
    """Run 100 queries through the ACOS runtime."""
    print("=" * 70)
    print("ACOS RUNTIME ACTIVATION — 100 REAL QUERIES")
    print("=" * 70)
    print(f"Start time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Initialize kernel
    print("[1/4] Initializing CognitiveKernel...")
    kernel = CognitiveKernel()
    await kernel.initialize()
    print("  ✅ Kernel initialized")

    # Check model availability
    models = await kernel._router.get_available_models()
    print(f"\n[2/4] Available models: {[(m.name, m.is_available) for m in models]}")
    print(f"  Default backend: {kernel._router._default_backend}")

    if kernel._router._default_backend == "mock":
        print("  ⚠️  WARNING: Using MockBackend — no real LLM inference!")

    # Run queries — serialize to avoid overwhelming the LLM API
    print(f"\n[3/4] Running {len(QUERIES)} queries (serialized for real LLM usage)...")
    print("-" * 70)

    results = []
    successful = 0
    failed = 0
    total_time = 0
    real_llm_calls = 0

    for i, query in enumerate(QUERIES, 1):
        start = time.monotonic()
        try:
            response = await kernel.process_query_v2(
                QueryRequestV2(query=query, priority=5)
            )
            elapsed = (time.monotonic() - start) * 1000
            total_time += elapsed

            # Count real LLM usage from router stats
            router_perf = kernel._router.get_performance_stats()
            zai_stats = router_perf.get("z-ai-api", {})
            real_llm_calls = zai_stats.get("call_count", 0)

            result = {
                "index": i,
                "query": query[:60],
                "session_id": response.session_id,
                "threads": len(response.threads),
                "agent_outputs": len(response.agent_outputs),
                "reflections": len(response.reflections),
                "verifications": len(response.verifications),
                "beliefs_affected": len(response.beliefs_affected),
                "goals_affected": len(response.goals_affected),
                "time_ms": elapsed,
                "success": True,
                "real_llm_calls_so_far": real_llm_calls,
            }
            results.append(result)
            successful += 1

            # Progress indicator
            llm_indicator = f"LLM:{real_llm_calls}" if real_llm_calls > 0 else "mock"
            status = "✅"
            print(f"  {status} [{i:3d}/100] {elapsed:8.0f}ms ({llm_indicator}) — {query[:45]}")

            # Small delay between queries to let LLM API recover
            if i % 10 == 0:
                await asyncio.sleep(1)

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            total_time += elapsed
            failed += 1
            results.append({
                "index": i,
                "query": query[:60],
                "error": str(e)[:100],
                "time_ms": elapsed,
                "success": False,
            })
            print(f"  ❌ [{i:3d}/100] {elapsed:8.0f}ms — ERROR: {str(e)[:50]}")

    # Generate database report
    print(f"\n[4/4] Database Population Report")
    print("-" * 70)

    db = sqlite3.connect(kernel._storage.db_path)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    populated_tables = 0
    empty_tables = 0
    total_rows = 0

    for table in tables:
        tname = table["name"]
        if tname.startswith("sqlite_"):
            continue
        cursor.execute(f"SELECT COUNT(*) as cnt FROM [{tname}]")
        count = cursor.fetchone()["cnt"]
        total_rows += count
        if count > 0:
            populated_tables += 1
            print(f"  ✅ {tname}: {count} rows")
        else:
            empty_tables += 1

    db.close()

    # Summary
    print()
    print("=" * 70)
    print("ACTIVATION SUMMARY")
    print("=" * 70)
    print(f"Queries executed:    {successful}/{len(QUERIES)} successful, {failed} failed")
    print(f"Total time:          {total_time/1000:.1f}s")
    print(f"Avg query time:      {total_time/1000/len(QUERIES):.1f}s")
    print(f"Tables populated:    {populated_tables}/{populated_tables + empty_tables}")
    print(f"Empty tables:        {empty_tables}")
    print(f"Total DB rows:       {total_rows}")
    print(f"Default LLM:         {kernel._router._default_backend}")
    print()

    # Get trace stats
    trace_stats = await kernel._trace_logger.get_trace_stats()
    print("TRACE STATISTICS:")
    print(f"  Total traces: {trace_stats.get('total_traces', 0)}")
    if 'phase_counts' in trace_stats:
        for phase, count in sorted(trace_stats['phase_counts'].items()):
            print(f"    {phase}: {count}")

    # Get model performance
    perf = kernel._router.get_performance_stats()
    print("\nLLM PERFORMANCE:")
    for model, stats in perf.items():
        print(f"  {model}: avg={stats['avg_latency']:.2f}s, calls={stats['call_count']}")

    # Save activation results
    activation_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queries_total": len(QUERIES),
        "queries_successful": successful,
        "queries_failed": failed,
        "total_time_s": total_time / 1000,
        "avg_query_time_s": total_time / 1000 / len(QUERIES),
        "tables_populated": populated_tables,
        "tables_empty": empty_tables,
        "total_db_rows": total_rows,
        "default_llm": kernel._router._default_backend,
        "model_stats": perf,
        "trace_stats": trace_stats,
        "results": results,
    }

    report_path = "/home/z/my-project/acos-runtime/data/activation_report.json"
    with open(report_path, "w") as f:
        json.dump(activation_report, f, indent=2, default=str)
    print(f"\nActivation report saved to: {report_path}")

    await kernel.shutdown()
    print("\nDone. Kernel shut down.")


if __name__ == "__main__":
    asyncio.run(run_activation())
