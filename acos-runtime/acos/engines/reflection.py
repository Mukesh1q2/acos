"""
Reflection Engine - Reviews outputs and detects contradictions.

Capabilities:
- Review agent outputs for quality
- Detect contradictions between thread results
- Generate improvement suggestions
- Provide quality scoring
"""

from __future__ import annotations

from acos.schemas.models import AgentOutput, ReflectionResult
from acos.models.router import ModelRouter


REFLECTION_SYSTEM_PROMPT = """You are the Reflection Engine in the ACOS (Avadhan Cognitive Operating System).
Your role is to critically review outputs from reasoning threads.

When reviewing outputs, you should:
1. Assess overall quality and completeness
2. Detect contradictions between different thread outputs
3. Identify gaps or missing perspectives
4. Suggest specific improvements
5. Generate a revised version if warranted
6. Provide a quality score (0.0 to 1.0)

Be constructive but thorough. Every improvement suggestion should be actionable."""


class ReflectionEngine:
    """
    Reflection Engine for ACOS.

    Reviews outputs from multiple threads, detects contradictions,
    and generates improvement suggestions.
    """

    def __init__(self, model_router: ModelRouter):
        self._router = model_router

    async def reflect(
        self,
        thread_id: str,
        outputs: list[AgentOutput],
    ) -> ReflectionResult:
        """Reflect on a set of agent outputs."""
        if not outputs:
            return ReflectionResult(
                thread_id=thread_id,
                original_output="",
                issues_found=["No outputs to reflect on"],
                quality_score=0.0,
            )

        # Build reflection prompt
        outputs_text = "\n\n".join(
            f"[{o.agent_type.value}] (confidence: {o.confidence:.2f})\n{o.content}"
            for o in outputs
        )

        prompt = f"""Review the following outputs from multiple reasoning threads:

{outputs_text}

Please provide a thorough reflection:
1. Quality Assessment (overall completeness, depth, accuracy)
2. Contradictions Found (any conflicting claims between outputs)
3. Gaps Identified (missing perspectives or incomplete analysis)
4. Improvement Suggestions (specific, actionable)
5. Revised Output (if improvements are warranted, provide an improved version)
6. Quality Score (0.0-1.0)"""

        result = await self._router.generate(prompt, system=REFLECTION_SYSTEM_PROMPT)

        # Parse the reflection result
        issues = self._extract_section(result, "issues", "quality")
        contradictions = self._extract_section(result, "contradiction")
        improvements = self._extract_section(result, "improvement")
        quality_score = self._extract_score(result)

        return ReflectionResult(
            thread_id=thread_id,
            original_output=outputs_text[:1000],
            issues_found=issues,
            contradictions=contradictions,
            improvements=improvements,
            revised_output=result,
            quality_score=quality_score,
        )

    async def reflect_all(
        self,
        thread_outputs: dict[str, list[AgentOutput]],
    ) -> list[ReflectionResult]:
        """Reflect on outputs from all threads."""
        results = []
        for thread_id, outputs in thread_outputs.items():
            result = await self.reflect(thread_id, outputs)
            results.append(result)
        return results

    async def detect_cross_thread_contradictions(
        self,
        all_outputs: list[AgentOutput],
    ) -> list[str]:
        """Detect contradictions between different threads' outputs."""
        if len(all_outputs) < 2:
            return []

        outputs_text = "\n\n".join(
            f"[Thread {o.thread_id[:8]} | {o.agent_type.value}]\n{o.content[:300]}"
            for o in all_outputs
        )

        prompt = f"""Analyze these outputs from different reasoning threads and identify any contradictions:

{outputs_text}

List only the specific contradictions found between different thread outputs.
If no contradictions exist, respond with "No contradictions found."

Format each contradiction as a bullet point starting with "-"."""

        result = await self._router.generate(prompt, system=REFLECTION_SYSTEM_PROMPT)

        # Parse contradictions
        contradictions = []
        for line in result.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                contradictions.append(line[1:].strip())
            elif line.startswith("*"):
                contradictions.append(line[1:].strip())

        return contradictions if contradictions and contradictions[0] != "No contradictions found." else []

    def _extract_section(self, text: str, *keywords: str) -> list[str]:
        """Extract bullet points from a section matching any of the keywords."""
        items = []
        in_section = False
        for line in text.split("\n"):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                in_section = True
                continue
            if in_section:
                if line.strip().startswith(("-", "*", "•")):
                    items.append(line.strip().lstrip("-*• ").strip())
                elif line.strip() and not line.strip().startswith("#") and len(items) > 0:
                    # Might be a continuation or next section
                    if any(
                        kw in line_lower
                        for kw in ["quality", "contradiction", "improvement", "gap", "score", "revised"]
                    ):
                        in_section = False
        return items

    def _extract_score(self, text: str) -> float:
        """Extract a numeric quality score from the reflection."""
        import re
        # Look for patterns like "Quality Score: 0.8" or "Score: 0.75"
        patterns = [
            r"(?:quality\s+)?score[:\s]+(\d+\.?\d*)",
            r"(\d+\.?\d*)/(?:1\.0|10)",
            r"quality[:\s]+(\d+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score if score <= 1.0 else score / 10.0))
        return 0.5  # Default
