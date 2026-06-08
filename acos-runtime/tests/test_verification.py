"""Unit tests for the VerificationEngine."""

import pytest

from acos.engines.verification import VerificationEngine
from acos.models.router import ModelRouter, MockBackend
from acos.schemas.models import AgentOutput, AgentType


@pytest.fixture
def router():
    r = ModelRouter()
    r.register_backend("mock", MockBackend(), is_default=True)
    return r


@pytest.fixture
def engine(router):
    return VerificationEngine(router)


class TestVerificationEngine:
    """Tests for the VerificationEngine."""

    @pytest.mark.asyncio
    async def test_verify_content(self, engine):
        """Test verifying a piece of content."""
        result = await engine.verify(
            "t1",
            "The Earth revolves around the Sun. Water boils at 100 degrees Celsius at sea level.",
        )
        assert result.thread_id == "t1"
        assert result.consistency_score >= 0.0
        assert result.confidence_score >= 0.0
        assert isinstance(result.passed, bool)

    @pytest.mark.asyncio
    async def test_verify_with_context(self, engine):
        """Test verifying with additional context."""
        result = await engine.verify(
            "t1",
            "The system uses HBTA for attention.",
            context="HBTA is Hierarchical Binary-Tree Attention with O(Nd2logN) complexity.",
        )
        assert result.confidence_score >= 0.0

    @pytest.mark.asyncio
    async def test_verify_multiple_outputs(self, engine):
        """Test verifying multiple agent outputs."""
        outputs = [
            AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t1",
                content="Research finding about quantum mechanics.",
                confidence=0.8,
            ),
            AgentOutput(
                agent_type=AgentType.PLANNING,
                thread_id="t2",
                content="Strategic plan for the project.",
                confidence=0.7,
            ),
        ]

        results = await engine.verify_outputs(outputs)
        assert len(results) == 2
        for r in results:
            assert r.consistency_score >= 0.0

    @pytest.mark.asyncio
    async def test_cross_verify(self, engine):
        """Test cross-verification between threads."""
        outputs = [
            AgentOutput(
                agent_type=AgentType.RESEARCH,
                thread_id="t1",
                content="The market is growing at 15% annually.",
                confidence=0.8,
            ),
            AgentOutput(
                agent_type=AgentType.PLANNING,
                thread_id="t2",
                content="Given the 15% growth rate, we should invest heavily.",
                confidence=0.7,
            ),
        ]

        result = await engine.cross_verify(outputs)
        assert result.consistency_score >= 0.0
        assert result.confidence_score >= 0.0
