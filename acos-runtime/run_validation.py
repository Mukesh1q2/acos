#!/usr/bin/env python3
"""Run ACOS Validation Lab and output JSON results for the API.

Usage: python3 run_validation.py [--quick] [--seed SEED]
"""

import argparse
import json
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acos.validation import ValidationLab, ValidationConfig
from acos.validation.models import SystemType


def main():
    parser = argparse.ArgumentParser(description="Run ACOS Validation Lab")
    parser.add_argument("--quick", action="store_true", help="Quick run with fewer test cases")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n-test-cases", type=int, default=None, help="Override test case count")
    parser.add_argument("--n-ab-cases", type=int, default=None, help="Override A/B test case count")
    args = parser.parse_args()

    if args.quick:
        config = ValidationConfig(
            n_test_cases=args.n_test_cases or 5,
            n_cases_ab_test=args.n_ab_cases or 5,
            include_baselines=[SystemType.DIRECT_LLM, SystemType.MEMORY_RAG],
            seed=args.seed,
        )
    else:
        config = ValidationConfig(
            n_test_cases=args.n_test_cases or 50,
            n_cases_ab_test=args.n_ab_cases or 100,
            seed=args.seed,
        )

    lab = ValidationLab(config)
    report = lab.run()

    # Convert to JSON-serializable dict
    result = report.model_dump(mode="json")

    # Add summary
    result["summary"] = {
        "overall_score": report.overall_score if hasattr(report, 'overall_score') else None,
        "conclusion": report.conclusion,
        "strengths_count": len(report.strengths),
        "weaknesses_count": len(report.weaknesses),
        "recommendations_count": len(report.recommended_changes),
        "execution_time_ms": report.total_execution_time_ms,
    }

    # Add tournament winner
    if report.tournament_result:
        result["summary"]["tournament_winner"] = report.tournament_result.best_system
        result["summary"]["rankings"] = report.tournament_result.rankings

    # Add emergence info
    if report.emergence_analysis:
        result["summary"]["emergence_score"] = report.emergence_analysis.overall_emergence_score
        result["summary"]["emergent_capabilities"] = report.emergence_analysis.emergent_capabilities

    # Add failure info
    if report.failure_analysis:
        result["summary"]["health_score"] = report.failure_analysis.overall_health
        result["summary"]["failures_detected"] = report.failure_analysis.total_failures_detected

    # Add category scores from first benchmark result (ACOS)
    if report.benchmark_results:
        from collections import defaultdict
        category_scores = defaultdict(list)
        for br in report.benchmark_results:
            if "ACOS" in br.system_name.upper():
                category_scores[br.category.value].append(br.overall_score)
        result["summary"]["acos_category_scores"] = {
            cat: round(sum(scores) / len(scores), 4)
            for cat, scores in category_scores.items()
        }

    json.dump(result, sys.stdout, indent=2, default=str)


if __name__ == "__main__":
    main()
