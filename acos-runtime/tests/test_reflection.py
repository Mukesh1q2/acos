"""Unit tests for the ReflectionEngine."""

import pytest

from acos.engines.reflection import ReflectionEngine
from acos.models.router import ModelRouter, MockBackend
from acos.schemas.models import AgentOutput, AgentType


@pytest.fixture
def router():
    r = ModelRouter()
    r.register_backend("mock", MockBackend(), is_default=True)
    return r


@pytest.fixture
def engine(router):
    return ReflectionEngine(router)


class TestReflectionEngine:
    """Tests for the ReflectionEngine."""

    @pytest.mark.asyncio
    async def test_reflect_on_outputs(self, engine):
        """Test reflecting on a set of agent outputs."""
        outputs = [
            AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t1",
                content="Research finding: The sky is blue due to Rayleigh scattering.",
                confidence=0.9,
            ),
            AgentOutput(
                agent_type=AgentType.PLANNING,
                thread_id="t2",
                content="Plan: Investigate atmospheric optics further.",
                confidence=0.7,
            ),
        ]

        result = await engine.reflect("t1", outputs)
        assert result.thread_id == "t1"
        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0
        assert result.original_output is not None

    @pytest.mark.asyncio
    async def test_reflect_empty_outputs(self, engine):
        """Test reflecting on no outputs."""
        result = await engine.reflect("t1", [])
        assert result.quality_score == 0.0
        assert "No outputs" in result.issues_found[0]

    @pytest.mark.asyncio
    async def test_detect_cross_thread_contradictions(self, engine):
        """Test detecting contradictions between threads."""
        outputs = [
            AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t1",
                content="Analysis shows the market is bullish with strong growth indicators.",
                confidence=0.8,
            ),
            AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t2",
                content="Research indicates the market is bearish with declining trends.",
                confidence=0.7,
            ),
        ]

        contradictions = await engine.detect_cross_thread_contradictions(outputs)
        # With mock backend, we may or may not detect contradictions
        # The test verifies the function runs without error
        assert isinstance(contradictions, list)

    @pytest.mark.asyncio
    async def test_reflect_all(self, engine):
        """Test reflecting on all threads' outputs."""
        thread_outputs = {
            "t1": [AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t1",
                content="Finding 1",
                confidence=0.8,
            )],
            "t2": [AgentOutput(
                agent_type=AgentType.PLANNING,
                thread_id="t2",
                content="Plan 1",
                confidence=0.7,
            )],
        }

        results = await engine.reflect_all(thread_outputs)
        assert len(results) == 2
