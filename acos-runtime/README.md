# ACOS Runtime v0.1

**Avadhan Cognitive Operating System** - An executable cognitive infrastructure that processes queries through multiple parallel reasoning threads with isolated memory, agent orchestration, reflection, and verification.

## Architecture

```
User Query
    │
    ▼
┌──────────────────┐
│ Cognitive Kernel  │  ← Central orchestrator
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│Planning│ │Analysis│ │ Memory │ │Verification│  ← Reasoning Threads
│ Agent  │ │ Agent  │ │ Agent  │ │   Agent   │
└────┬───┘ └────┬───┘ └────┬───┘ └─────┬─────┘
     │          │          │           │
     ▼          ▼          ▼           ▼
┌─────────────────────────────────────────────┐
│         Orthogonal Thread Memory (OTM)       │  ← Isolated per-thread memory
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐    │
│  │Work. │  │Epi.  │  │Seman.│  │Work. │    │
│  │Mem T1│  │Mem T2│  │Mem T3│  │Mem T4│    │
│  └──────┘  └──────┘  └──────┘  └──────┘    │
└─────────────────────────────────────────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │Reflection│ │Verification│ │Synthesis │
    │  Engine  │ │  Engine   │ │  Engine  │
    └──────────┘ └──────────┘ └──────────┘
                    │
                    ▼
            ┌──────────────┐
            │Final Answer  │
            └──────────────┘
```

## Components

### Core
- **CognitiveKernel** - Central orchestrator: accepts queries, spawns threads, coordinates agents, merges results
- **ThreadScheduler** - Thread lifecycle: create, pause, resume, kill, prioritize
- **OrthogonalThreadMemory** - Per-thread isolated memory (S_i^T * S_j = 0)
- **MemoryManager** - Three-tier memory: Working, Episodic, Semantic (SQLite)

### Agents
- **ResearchAgent** - Deep analysis and information gathering
- **PlanningAgent** - Strategic planning and task decomposition
- **MemoryAgent** - Memory retrieval and context building
- **VerificationAgent** - Fact checking and validation

### Engines
- **ReflectionEngine** - Reviews outputs, detects contradictions, generates improvements
- **VerificationEngine** - Fact checking, consistency checking, confidence scoring
- **ModelRouter** - Routes tasks to best LLM (Mock/Ollama/Z-AI API)

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Process a query via CLI
python -m acos.cli query "Design a trading strategy"

# Start interactive mode
python -m acos.cli interactive

# Start API server
python -m acos.cli serve --port 8000

# Run tests
python -m pytest tests/ -v
```

## API Usage

```bash
# Process a query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Design a trading strategy"}'

# Check health
curl http://localhost:8000/health

# List models
curl http://localhost:8000/models

# Search memory
curl http://localhost:8000/memory/search/trading
```

## Success Criteria Verification

| # | Criterion | Status |
|---|-----------|--------|
| 1 | User query creates multiple reasoning threads | ✅ |
| 2 | Threads execute independently | ✅ |
| 3 | Threads maintain isolated memory | ✅ |
| 4 | Agent orchestration works | ✅ |
| 5 | Reflection loop works | ✅ |
| 6 | Verifier reviews outputs | ✅ |
| 7 | Final synthesis combines thread results | ✅ |
| 8 | Memory persists across sessions | ✅ |

## LLM Backends

| Backend | Status | Use Case |
|---------|--------|----------|
| Mock | ✅ Default | Testing, development |
| Ollama | Auto-detect | Local inference (Gemma, Qwen, Llama) |
| Z-AI API | Manual | Cloud LLM via Next.js /api/chat |

## Project Structure

```
acos-runtime/
├── acos/
│   ├── kernel.py          # CognitiveKernel
│   ├── scheduler.py       # ThreadScheduler
│   ├── memory/
│   │   ├── otm.py         # OrthogonalThreadMemory
│   │   ├── manager.py     # MemoryManager
│   │   └── store.py       # SQLite storage backend
│   ├── agents/
│   │   ├── base.py        # Agent base class
│   │   ├── research.py    # ResearchAgent
│   │   ├── planning.py    # PlanningAgent
│   │   ├── memory.py      # MemoryAgent
│   │   └── verification.py# VerificationAgent
│   ├── models/
│   │   └── router.py      # ModelRouter + backends
│   ├── engines/
│   │   ├── reflection.py  # ReflectionEngine
│   │   └── verification.py# VerificationEngine
│   ├── schemas/
│   │   └── models.py      # Pydantic data models
│   ├── api/
│   │   └── server.py      # FastAPI server
│   └── cli.py             # CLI interface
├── tests/
│   ├── test_kernel.py
│   ├── test_scheduler.py
│   ├── test_memory.py
│   ├── test_agents.py
│   ├── test_reflection.py
│   ├── test_verification.py
│   └── test_integration.py
├── data/                   # SQLite database
└── pyproject.toml
```
