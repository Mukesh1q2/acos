"""
Verification Engine - Fact checking, consistency checking, confidence scoring.

Capabilities:
- Verify factual claims against known information
- Check logical consistency of outputs
- Compute confidence scores
- Identify unverifiable claims
- Cross-reference between thread outputs
"""

from __future__ import annotations

from acos.schemas.models import (
    AgentOutput, VerificationResult, FactCheck,
)
from acos.models.router import ModelRouter


VERIFICATION_SYSTEM_PROMPT = """You are the Verification Engine in the ACOS (Avadhan Cognitive Operating System).
Your role is to verify the accuracy and consistency of outputs.

When verifying content, you should:
1. Extract key factual claims
2. Check each claim against established knowledge
3. Assess logical consistency (no circular reasoning, no self-contradictions)
4. Score confidence for each claim (0.0-1.0)
5. Identify unverifiable claims
6. Provide an overall pass/fail assessment

Output format:
- For each claim, provide: claim, verified (true/false), confidence, evidence
- Provide overall consistency score and confidence score
- Provide pass/fail verdict with reasoning"""


class VerificationEngine:
    """
    Verification Engine for ACOS.

    Performs fact checking, consistency checking, and confidence scoring
    on agent outputs.
    """

    def __init__(self, model_router: ModelRouter):
        self._router = model_router

    async def verify(
        self,
        thread_id: str,
        content: str,
        context: str | None = None,
    ) -> VerificationResult:
        """Verify a single piece of content."""
        prompt = f"""Verify the following content:

{content}

{f"Additional context for verification:\n{context}\n" if context else ""}

Provide a structured verification:
1. Extract key claims
2. For each claim: Is it verified? What's the confidence? What evidence supports it?
3. Overall consistency score (0.0-1.0)
4. Overall confidence score (0.0-1.0)
5. Pass or fail?
6. List any issues"""

        result = await self._router.generate(prompt, system=VERIFICATION_SYSTEM_PROMPT)

        # Parse fact checks
        fact_checks = self._parse_fact_checks(result)
        consistency_score = self._extract_score(result, "consistency")
        confidence_score = self._extract_score(result, "confidence")
        issues = self._extract_issues(result)
        passed = confidence_score >= 0.5 and consistency_score >= 0.5

        return VerificationResult(
            thread_id=thread_id,
            content=content[:500],
            fact_checks=fact_checks,
            consistency_score=consistency_score,
            confidence_score=confidence_score,
            passed=passed,
            issues=issues,
        )

    async def verify_outputs(
        self,
        outputs: list[AgentOutput],
    ) -> list[VerificationResult]:
        """Verify multiple agent outputs."""
        results = []
        for output in outputs:
            result = await self.verify(output.thread_id, output.content)
            results.append(result)
        return results

    async def cross_verify(
        self,
        outputs: list[AgentOutput],
    ) -> VerificationResult:
        """Cross-verify outputs from multiple threads for consistency."""
        if len(outputs) < 2:
            return VerificationResult(
                thread_id="cross-verify",
                content="Insufficient outputs for cross-verification",
                passed=True,
            )

        outputs_text = "\n\n".join(
            f"[{o.agent_type.value}] {o.content[:500]}"
            for o in outputs
        )

        prompt = f"""Cross-verify these outputs from multiple reasoning threads for consistency:

{outputs_text}

Check:
1. Are the claims across threads consistent with each other?
2. Are there any direct contradictions?
3. Is the overall narrative coherent?
4. Provide a combined consistency and confidence score"""

        result = await self._router.generate(prompt, system=VERIFICATION_SYSTEM_PROMPT)

        consistency_score = self._extract_score(result, "consistency")
        confidence_score = self._extract_score(result, "confidence")
        issues = self._extract_issues(result)

        return VerificationResult(
            thread_id="cross-verify",
            content=outputs_text[:500],
            fact_checks=[],
            consistency_score=consistency_score,
            confidence_score=confidence_score,
            passed=consistency_score >= 0.5 and confidence_score >= 0.5,
            issues=issues,
        )

    def _parse_fact_checks(self, text: str) -> list[FactCheck]:
        """Parse fact check results from verification output."""
        checks = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("-", "*", "•")) and ("verified" in line.lower() or "claim" in line.lower()):
                # Simple parsing - in production, use structured output
                verified = "true" in line.lower() or "verified" in line.lower()
                checks.append(FactCheck(
                    claim=line.lstrip("-*• ").strip(),
                    verified=verified,
                    confidence=0.7 if verified else 0.3,
                ))
        return checks[:10]  # Limit to 10 checks

    def _extract_score(self, text: str, score_type: str) -> float:
        """Extract a numeric score from verification output."""
        import re
        pattern = rf"{score_type}\s*(?:score)?[:\s]+(\d+\.?\d*)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            return min(1.0, max(0.0, score if score <= 1.0 else score / 10.0))
        return 0.5

    def _extract_issues(self, text: str) -> list[str]:
        """Extract issues from verification output."""
        issues = []
        in_issues = False
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            if "issue" in line_lower:
                in_issues = True
                continue
            if in_issues and line.strip().startswith(("-", "*", "•")):
                issues.append(line.strip().lstrip("-*• ").strip())
        return issues
