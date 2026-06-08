"""
Model Router - Routes tasks to the best available LLM model.

Supported backends:
1. Mock backend (for testing without LLM)
2. Ollama backend (for local models: Gemma, Qwen, Llama)
3. Z-AI API backend (for cloud LLM via existing Next.js /api/chat)

Capabilities:
- Route tasks to the most appropriate model
- Track model performance metrics
- Fallback to available models if preferred is unavailable
- Support task-specific model selection
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from acos.schemas.models import ModelInfo, ModelRoutingDecision


class LLMBackend:
    """Base class for LLM backends."""

    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        raise NotImplementedError

    async def is_available(self) -> bool:
        raise NotImplementedError

    def get_info(self) -> ModelInfo:
        raise NotImplementedError


class MockBackend(LLMBackend):
    """Mock LLM backend for testing without an actual model."""

    def __init__(self):
        self._call_count = 0

    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        self._call_count += 1
        # Generate contextual mock responses based on prompt keywords
        prompt_lower = prompt.lower()

        if "research" in prompt_lower or "analyze" in prompt_lower:
            return (
                "Research Analysis:\n"
                "Based on the query, I've identified three key areas for investigation:\n"
                "1. Historical context and precedent patterns\n"
                "2. Current state-of-the-art approaches and their limitations\n"
                "3. Emerging trends and potential breakthroughs\n\n"
                "Key finding: The intersection of orthogonal memory systems and "
                "hierarchical attention mechanisms presents a novel approach that "
                "hasn't been fully explored in current literature."
            )
        elif "plan" in prompt_lower or "strategy" in prompt_lower:
            return (
                "Strategic Plan:\n"
                "Phase 1: Requirements gathering and constraint analysis\n"
                "Phase 2: Architecture design with modular components\n"
                "Phase 3: Iterative implementation with validation checkpoints\n"
                "Phase 4: Integration testing and performance optimization\n\n"
                "Critical path: Phase 2 depends on Phase 1 output. "
                "Phase 3 can partially overlap with Phase 2 for parallel development."
            )
        elif "verif" in prompt_lower or "check" in prompt_lower or "validate" in prompt_lower:
            return (
                "Verification Report:\n"
                "Status: PASSED with minor observations\n"
                "- Fact check: Claims are consistent with established knowledge\n"
                "- Logic check: No circular reasoning or contradictions detected\n"
                "- Confidence: 0.85 (high)\n\n"
                "Observations:\n"
                "- One claim could benefit from additional citation\n"
                "- Assumptions are clearly stated and reasonable"
            )
        elif "reflect" in prompt_lower or "review" in prompt_lower or "improve" in prompt_lower:
            return (
                "Reflection Review:\n"
                "Quality Assessment: Good with room for improvement\n\n"
                "Strengths:\n"
                "- Clear structure and logical flow\n"
                "- Well-supported arguments\n\n"
                "Suggested Improvements:\n"
                "- Add quantitative evidence where possible\n"
                "- Consider edge cases in the analysis\n"
                "- Strengthen the conclusion with actionable next steps"
            )
        elif "memory" in prompt_lower or "remember" in prompt_lower or "recall" in prompt_lower:
            return (
                "Memory Retrieval Report:\n"
                "Relevant memories found: 5 records\n\n"
                "Key memories:\n"
                "1. Previous similar query was processed on the last session\n"
                "2. User preference: concise answers with technical depth\n"
                "3. Domain context: ACOS/AFM architecture\n"
                "4. Recent focus: Orthogonal Thread Memory implementation\n"
                "5. Outstanding question: Performance benchmarking approach\n\n"
                "Memory consolidation recommended for working memory tier."
            )
        elif "synthe" in prompt_lower or "combine" in prompt_lower or "merge" in prompt_lower:
            return (
                "Synthesis Report:\n\n"
                "Combining outputs from multiple reasoning threads:\n\n"
                "Research findings confirm the feasibility of the proposed approach. "
                "The strategic plan provides a clear execution path with manageable risk. "
                "Verification confirms accuracy with high confidence. "
                "Memory context adds relevant historical insights.\n\n"
                "Recommendation: Proceed with implementation following Phase 1 of the plan, "
                "incorporating the research findings to mitigate identified risks."
            )
        else:
            return (
                f"ACOS Response (thread #{self._call_count}):\n"
                f"Processing query: {prompt[:100]}...\n\n"
                "Analysis complete. The query has been processed through "
                "multiple reasoning threads with orthogonal memory isolation. "
                "Results are ready for synthesis."
            )

    async def is_available(self) -> bool:
        return True

    def get_info(self) -> ModelInfo:
        return ModelInfo(
            name="mock",
            provider="mock",
            capabilities=["generation", "testing"],
            context_window=4096,
            is_available=True,
        )


class OllamaBackend(LLMBackend):
    """Ollama backend for local model inference."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        payload.update(kwargs)

        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def is_available(self) -> bool:
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def get_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="ollama",
            capabilities=["generation", "local-inference"],
            context_window=8192,
            is_available=False,  # Will be checked at runtime
        )


class ZAIAPIBackend(LLMBackend):
    """Z-AI API backend - calls the Next.js /api/chat endpoint."""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json={"messages": messages},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def is_available(self) -> bool:
        try:
            response = await self._client.get(self.base_url)
            return response.status_code == 200
        except Exception:
            return False

    def get_info(self) -> ModelInfo:
        return ModelInfo(
            name="z-ai-api",
            provider="zai-api",
            capabilities=["generation", "acos-aware"],
            context_window=8192,
            is_available=False,  # Will be checked at runtime
        )


class ModelRouter:
    """
    Routes tasks to the best available LLM model.

    Strategy:
    1. Check if the requested model is available
    2. Fall back to the next best available model
    3. Track performance metrics for adaptive routing
    """

    def __init__(self):
        self._backends: dict[str, LLMBackend] = {}
        self._performance: dict[str, list[float]] = {}  # model -> [latencies]
        self._default_backend: str = "mock"

    def register_backend(self, name: str, backend: LLMBackend, is_default: bool = False) -> None:
        """Register an LLM backend."""
        self._backends[name] = backend
        self._performance[name] = []
        if is_default or not self._backends:
            self._default_backend = name

    async def auto_discover(self) -> None:
        """Discover and register available backends."""
        # Always register mock backend as default (fast, reliable)
        self.register_backend("mock", MockBackend(), is_default=True)

        # Try Ollama
        try:
            ollama = OllamaBackend()
            # Short timeout check
            ollama._client = httpx.AsyncClient(timeout=3.0)
            if await asyncio.wait_for(ollama.is_available(), timeout=5.0):
                self.register_backend("ollama", ollama)
                self._default_backend = "ollama"
        except Exception:
            pass

        # Z-AI API: register but don't check availability (too slow)
        # Users can explicitly enable it via preferred_model="z-ai-api"
        # zai = ZAIAPIBackend()
        # self.register_backend("z-ai-api", zai)

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        preferred_model: str | None = None,
        **kwargs,
    ) -> str:
        """Generate a response using the best available model."""
        backend_name = preferred_model or self._default_backend
        backend = self._backends.get(backend_name)

        # Fallback chain
        if not backend or not await backend.is_available():
            for name, b in self._backends.items():
                if await b.is_available():
                    backend = b
                    backend_name = name
                    break

        if not backend:
            raise RuntimeError("No LLM backend available")

        start = time.monotonic()
        try:
            result = await backend.generate(prompt, system, **kwargs)
            latency = time.monotonic() - start
            self._performance.setdefault(backend_name, []).append(latency)
            return result
        except Exception as e:
            # Try fallback
            for name, b in self._backends.items():
                if name != backend_name and await b.is_available():
                    try:
                        result = await b.generate(prompt, system, **kwargs)
                        latency = time.monotonic() - start
                        self._performance.setdefault(name, []).append(latency)
                        return result
                    except Exception:
                        continue
            raise RuntimeError(f"All backends failed. Last error: {e}") from e

    def route(self, task_type: str) -> ModelRoutingDecision:
        """Decide which model to use for a task type."""
        # Task-specific routing logic
        routing_map = {
            "research": "ollama",    # Prefer local for research (data privacy)
            "planning": "z-ai-api",  # Prefer cloud for planning (quality)
            "memory": "mock",        # Memory tasks are simple
            "verification": "z-ai-api",  # Verification needs quality
            "creative": "ollama",    # Creative can use local
        }

        preferred = routing_map.get(task_type, self._default_backend)

        # Check if preferred is available
        available = preferred in self._backends
        actual = preferred if available else self._default_backend

        return ModelRoutingDecision(
            model_name=actual,
            provider=self._backends[actual].get_info().provider if actual in self._backends else "unknown",
            reason=f"Task type '{task_type}' routed to {actual} (preferred: {preferred}, available: {available})",
            confidence=0.8 if available else 0.5,
        )

    async def get_available_models(self) -> list[ModelInfo]:
        """Get info about all available models."""
        models = []
        for name, backend in self._backends.items():
            info = backend.get_info()
            info.is_available = await backend.is_available()
            models.append(info)
        return models

    def get_performance_stats(self) -> dict[str, dict[str, float]]:
        """Get performance statistics for all models."""
        stats = {}
        for name, latencies in self._performance.items():
            if latencies:
                stats[name] = {
                    "avg_latency": sum(latencies) / len(latencies),
                    "min_latency": min(latencies),
                    "max_latency": max(latencies),
                    "call_count": len(latencies),
                }
        return stats
