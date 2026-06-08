"""Unit tests for the Agent subsystem."""

import os
import tempfile
import pytest

from acos.agents.research import ResearchAgent
from acos.agents.planning import PlanningAgent
from acos.agents.memory import MemoryAgent
from acos.agents.verification import VerificationAgent
from acos.memory.store import StorageBackend
from acos.memory.manager import MemoryManager
from acos.models.router import ModelRouter, MockBackend
from acos.schemas.models import AgentType, ThreadState, ThreadType, ThreadStatus


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def agent_setup(db_path):
    """Set up dependencies for agent testing."""
    storage = StorageBackend(db_path=db_path)
    await storage.initialize()
    router = ModelRouter()
    router.register_backend("mock", MockBackend(), is_default=True)
    memory = MemoryManager(storage)
    yield storage, router, memory
    await storage.close()


class TestResearchAgent:
    """Tests for the ResearchAgent."""

    @pytest.mark.asyncio
    async def test_execute(self, agent_setup):
        storage, router, memory = agent_setup
        agent = ResearchAgent(router, memory)
        thread = ThreadState(
            query="What is quantum computing?",
            type=ThreadType.ANALYSIS,
        )
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.RESEARCH
        assert len(output.content) > 0
        assert output.confidence > 0

    @pytest.mark.asyncio
    async def test_stores_memory(self, agent_setup):
        storage, router, memory = agent_setup
        agent = ResearchAgent(router, memory)
        thread = ThreadState(query="Test query", type=ThreadType.ANALYSIS)
        await agent.execute(thread)

        memories = await memory.retrieve(thread.id)
        assert len(memories) > 0


class TestPlanningAgent:
    """Tests for the PlanningAgent."""

    @pytest.mark.asyncio
    async def test_execute(self, agent_setup):
        storage, router, memory = agent_setup
        agent = PlanningAgent(router, memory)
        thread = ThreadState(query="Plan a project", type=ThreadType.PLANNING)
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.PLANNING
        assert len(output.content) > 0


class TestMemoryAgent:
    """Tests for the MemoryAgent."""

    @pytest.mark.asyncio
    async def test_execute(self, agent_setup):
        storage, router, memory = agent_setup
        agent = MemoryAgent(router, memory)
        thread = ThreadState(query="Recall previous work", type=ThreadType.MEMORY)
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.MEMORY
        assert len(output.content) > 0

    @pytest.mark.asyncio
    async def test_with_existing_memories(self, agent_setup):
        storage, router, memory = agent_setup
        # Pre-populate memories
        await memory.store_semantic("test-thread", "Previous research on ACOS architecture")

        agent = MemoryAgent(router, memory)
        thread = ThreadState(query="What was my previous research?", type=ThreadType.MEMORY)
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.MEMORY


class TestVerificationAgent:
    """Tests for the VerificationAgent."""

    @pytest.mark.asyncio
    async def test_execute(self, agent_setup):
        storage, router, memory = agent_setup
        agent = VerificationAgent(router, memory)
        thread = ThreadState(query="Verify this claim", type=ThreadType.VERIFICATION)
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.VERIFICATION
        assert len(output.content) > 0

    @pytest.mark.asyncio
    async def test_with_thread_result(self, agent_setup):
        storage, router, memory = agent_setup
        agent = VerificationAgent(router, memory)
        thread = ThreadState(
            query="Verify the analysis",
            type=ThreadType.VERIFICATION,
        )
        thread.result = "Previous analysis claimed 100% accuracy"
        output = await agent.execute(thread)
        assert output.agent_type == AgentType.VERIFICATION
