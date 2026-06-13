# Embodied Robot Brain

> Multi-agent research assistant with PhysicsGate safety mechanism for embodied AI systems. Implements a full research pipeline from literature discovery through experiment design to progress tracking, with deterministic conflict detection independent of LLM self-evaluation.

Embodied Robot Brain is a multi-agent system designed as a personalized research assistant for university students. It orchestrates four specialized agents -- Literature, Experiment Design, Progress Management, and Research Validator -- through an event-driven orchestrator. The system's core innovation is **PhysicsGate**, a physical-feedback-driven hard gate mechanism that provides deterministic, model-independent safety guarantees for LLM-generated outputs, originally developed for Traditional Chinese Medicine (TCM) compatibility validation and generalizable to any domain with structured constraint knowledge.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Benchmarks](#benchmarks)
- [Research](#research)
- [Innovation Roadmap](#innovation-roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Overview

Large language models (LLMs) used as "brains" in embodied AI systems suffer from a fundamental limitation: their safety evaluations are probabilistic self-assessments, not physically grounded constraints. When an LLM generates a prescription containing incompatible herbs or a robot motion plan violating kinematic constraints, no mechanism independent of the model's own confidence can reliably block the action.

Embodied Robot Brain addresses this by introducing **PhysicsGate** -- an O(1) hash-lookup hard gate that sits between the LLM's output and the execution layer. Every generated instruction is checked against a structured constraint library (e.g., TCM compatibility rules, physical laws, safety regulations). The gate outputs a three-valued signal (PASS / SOFT_REJECT / HARD_REJECT) based on a mathematical error function, providing safety guarantees that are completely independent of the LLM's probability distribution.

The system integrates this safety mechanism into a full research assistant pipeline:

```
User Research Question
        |
        v
+-------------------+     +---------------------+     +-------------------+
| Literature Agent  | --> | Experiment Agent    | --> | Progress Agent    |
| (RAG + Web + KG)  |     | (Chain-of-Design)   |     | (Digital Twin KG) |
+--------+----------+     +----------+----------+     +--------+----------+
         |                           |                          |
         v                           v                          v
+---------------------------------------------------------------------+
|                    Research Validator Agent                           |
|  Evidence Alignment -> Conflict Detection -> Confidence -> Synthesis |
+---------------------------------------------------------------------+
         |
         v
+---------------------------------------------------------------------+
|                       PhysicsGate                                    |
|  TCMConstraintLibrary -> Error Function -> Transfer Signal           |
|  (O(1) hash lookup, model-independent, deterministic)                |
+---------------------------------------------------------------------+
```

---

## Key Features

### Multi-Agent Research Pipeline
- **Literature Agent** -- Keyword search, semantic vector search, knowledge graph traversal, and systematic literature review generation
- **Experiment Agent** -- Reflexive Chain-of-Design loop: generate design, self-review, propose improvements, iterate
- **Progress Agent** -- Digital twin knowledge graph with milestone management, blocker detection, and reflective plan adjustment
- **Research Validator** -- Evidence alignment, three-layer conflict detection, four-dimensional credibility scoring, and synthesis
- **Orchestrator** -- Event-driven agent routing with persistent agent pool, parallel execution via `asyncio.gather`, and timeout management

### PhysicsGate Safety Mechanism
- **Deterministic Hard Gate** -- O(1) hash-lookup constraint checking, independent of LLM probability model
- **Three-valued Transfer Signal** -- PASS / SOFT_REJECT / HARD_REJECT based on mathematical error function E(A_t, K)
- **Dynamic Delta Decay** -- Strict threshold (delta=0.05) for first 3 retries, relaxed (delta=0.10) after, preventing deadlock while maintaining safety
- **TCM Constraint Library** -- 21 eighteen-antagonism pairs (fatal, E=1.0), 9 nineteen-fear pairs (high, E=0.7), 6 cold-hot conflict pairs (medium, E=0.4)
- **Safety Guarantee Theorem** -- Fatal conflicts (E=1.0) always output HARD_REJECT regardless of delta configuration

### Three-Layer Conflict Taxonomy
- **Type-I** -- Method inconsistency across datasets/settings (delta > 2.0%)
- **Type-II** -- Performance gap within dataset comparisons (delta > 5.0%)
- **Type-III** -- Theoretical/semantic contradiction between papers

### Production-Grade Backend
- **Security** -- SecurityHeadersMiddleware, per-IP sliding-window rate limiting, CORS whitelist (no wildcards in production)
- **Observability** -- Prometheus metrics endpoint, request-ID correlation, structured logging via Loguru
- **Health Checks** -- `/health`, `/health/ready`, `/health/live` endpoints with Kubernetes-compatible probes
- **WebSocket** -- Real-time agent state broadcasting to connected clients

---

## Architecture

```
                    +------------------------------------------+
                    |              FastAPI Backend              |
                    |         (Security + Rate Limiting)        |
                    +--------------------+---------------------+
                                         |
                    +--------------------+---------------------+
                    |              Orchestrator                 |
                    |    (Event-driven, persistent agent pool)  |
                    +----+----------+----------+---------------+
                         |          |          |
              +----------+    +-----+-----+   +--------+
              |               |           |            |
              v               v           v            v
    +-----------------+ +-----------+ +----------+ +-------------+
    | Literature      | | Experiment| | Progress | | Research    |
    | Agent           | | Agent     | | Agent    | | Validator   |
    |                 | |           | |          | |             |
    | - Keyword Search| | - Design  | | - Plan   | | - Alignment |
    | - Semantic Search| - Review  | | - Track  | | - Conflict  |
    | - KG Traversal  | | - Reflect | | - Alert  | | - Scoring   |
    | - Lit Review    | | - Iterate | | - Adjust | | - Synthesis |
    +-----------------+ +-----------+ +----------+ +------+------+
                                                          |
                                                    +-----+------+
                                                    |PhysicsGate |
                                                    |            |
                                                    | E(A_t, K)  |
                                                    | G(A,K,delta)|
                                                    +------------+
```

### State Machine

Each agent follows a state machine: `idle -> initializing -> ready -> working -> ready` with WebSocket broadcast on every transition.

### Agent Communication

Agents communicate through the Orchestrator's task routing system. The `run_research_session` method executes all three core agents in parallel via `asyncio.gather`, then feeds results into the Progress Agent for plan synthesis.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI + Starlette | Async REST API with WebSocket support |
| **Runtime** | Uvicorn + Gunicorn | Production ASGI server with worker management |
| **Validation** | Pydantic v2 + pydantic-settings | Schema validation and environment configuration |
| **Logging** | Loguru | Structured logging with request-ID correlation |
| **Metrics** | Prometheus Client | Request count, latency histograms |
| **Database** | Neo4j | Knowledge graph storage (planned) |
| **Vector Store** | Milvus | Semantic search for literature retrieval (planned) |
| **LLM** | Claude / GPT-4 API | Reasoning engine for agents |
| **Dashboard** | Streamlit | Real-time monitoring dashboard |
| **Frontend** | Vue 3 + Three.js + GSAP | Interactive 3D visualization (in development) |
| **Testing** | Pytest | Unit and integration tests |
| **CI/CD** | GitHub Actions | Lint (ruff) + test pipeline |
| **Container** | Docker + Docker Compose | Multi-service deployment |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or conda package manager
- (Optional) Docker and Docker Compose for production deployment

### 1. Backend Server

```bash
cd embodied-robot-brain/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API server (port 8013)
python main.py
```

The API is available at `http://localhost:8013`. Interactive docs at `http://localhost:8013/docs`.

### 2. Streamlit Dashboard (Optional)

```bash
# From the project root
streamlit run dashboard.py --server.port 18713
```

Opens a real-time monitoring dashboard at `http://localhost:18713` with tabs for Dashboard, Literature Agent, Experiment Agent, Progress Tracker, and Knowledge Graph.

### 3. Docker Deployment (Production)

```bash
cd deployment

# Start all services (backend + Neo4j + Milvus)
docker-compose up -d

# Check status
docker-compose ps
```

Services:
- Backend API: `http://localhost:8013`
- Neo4j Browser: `http://localhost:7474`
- Milvus: `localhost:19530`

### 4. Health Check

```bash
curl http://localhost:8013/health
# {"status": "healthy", "version": "1.0.0", "service": "...", "environment": "development"}
```

---

## API Reference

### Base URL: `http://localhost:8013/api/v1`

#### Research Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/research/sessions` | Create a new research session (triggers literature + experiment + progress pipeline) |
| `GET` | `/research/sessions/{id}` | Get session status and insights |

#### Literature Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/literature/search` | Search literature (RAG / Web / Hybrid mode) |
| `POST` | `/api/literature/review` | Search + validate (evidence alignment + conflict detection + credibility scoring) |

#### Experiment Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/experiment/design` | Run reflexive Chain-of-Design loop |

#### Progress Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/progress/plan` | Create research plan from literature + experiment results |
| `POST` | `/api/progress/update` | Update task progress |
| `GET` | `/api/progress/knowledge-graph/{session_id}` | Get digital twin knowledge graph |

#### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with agent states |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/api/orchestrator/states` | All agent states |
| `GET` | `/api/orchestrator/events` | Event history |
| `WS` | `/ws/{client_id}` | WebSocket for real-time agent state updates |

### Example: Create Research Session

```bash
curl -X POST http://localhost:8013/api/v1/research/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {"name": "Zhang San", "major": "Computer Science"},
    "research_topic": "LLM-based medical diagnosis",
    "goals": ["Literature review", "Experiment design", "Paper draft"]
  }'
```

---

## Project Structure

```
embodied-robot-brain/
├── backend/
│   ├── main.py                          # FastAPI entry point (port 8013)
│   ├── app.py                           # Legacy entry point (port 8021)
│   ├── schemas.py                       # Pydantic request/response models
│   ├── dashboard.py                     # Streamlit dashboard (port 18713)
│   ├── gunicorn_conf.py                 # Gunicorn production config
│   ├── __init__.py
│   │
│   ├── agents/                          # Agent implementations
│   │   ├── __init__.py
│   │   ├── orchestrator.py              # Agent routing and parallel execution
│   │   ├── literature_agent.py          # Literature search + conflict detection
│   │   ├── experiment_agent.py          # Reflexive Chain-of-Design loop
│   │   ├── progress_agent.py            # Digital twin KG + milestone tracking
│   │   ├── research_validator.py        # Evidence alignment + credibility scoring
│   │   ├── conflict_validator.py        # PhysicsGate + TCMConstraintLibrary
│   │   ├── conflict_evidence.py         # Conflict evidence extraction
│   │   ├── conflict_type_classifier.py  # Type-I/II/III classification
│   │   └── physics_gate.py              # PhysicsGate gate mechanism
│   │
│   ├── api/                             # API route definitions
│   │   ├── __init__.py
│   │   └── research.py                  # Research session endpoints
│   │
│   ├── core/                            # Infrastructure
│   │   ├── __init__.py
│   │   ├── config.py                    # Environment settings (pydantic-settings)
│   │   ├── logging_config.py            # Request-ID logging middleware
│   │   ├── security.py                  # Security headers + rate limiting
│   │   └── metrics.py                   # Prometheus metrics middleware
│   │
│   ├── orchestrator/                    # Orchestrator engine
│   │   ├── __init__.py
│   │   └── engine.py
│   │
│   ├── rag/                             # RAG components
│   │   ├── __init__.py
│   │   ├── knowledge_graph.py           # Neo4j knowledge graph manager
│   │   └── vector_store.py              # Milvus vector store
│   │
│   ├── services/                        # External service integrations
│   │   ├── __init__.py
│   │   └── llm_service.py              # LLM API client (Claude/GPT-4)
│   │
│   ├── experiments/                     # Experiment scripts and results
│   │   ├── phase3_ablation.py           # PhysicsGate ablation study
│   │   ├── phase4_governance_stress.py  # Governance stress test
│   │   ├── phase4_type3_enrichment.py   # Type-III conflict enrichment
│   │   └── results/                     # CSV/JSON experiment results
│   │
│   ├── data/                            # Validation data
│   │   └── validation/
│   │       ├── ground_truth.json
│   │       ├── literature_validation_set.json
│   │       ├── conflict_results.json
│   │       └── run_results.json
│   │
│   ├── tests/                           # Test suite
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_api.py
│   │
│   └── requirements.txt
│
├── frontend/                            # Vue 3 + Three.js frontend (in development)
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│
├── deployment/                          # Production deployment
│   ├── docker-compose.yml               # Multi-service orchestration
│   ├── Dockerfile
│   ├── production.md
│   ├── start.sh
│   └── start.bat
│
├── docs/                                # Design documents
│   ├── Phase1_minimal_closed_loop.md
│   ├── Phase2_design.md
│   ├── Phase3_ablation_report.md
│   └── Phase4_governance_stress_report.md
│
├── .github/
│   └── workflows/
│       └── ci.yml                       # GitHub Actions CI (ruff + pytest)
│
├── dashboard.py                         # Streamlit dashboard entry point
├── SCI_FRAMEWORK.md                     # SCI paper framework v1
├── SCI_FRAMEWORK_v2_代码融合版.md        # SCI paper framework v2
├── SCI_FRAMEWORK_v3_PhysicsGate核心版.md # SCI paper framework v3 (PhysicsGate)
├── 专利技术交底书.md                      # Patent technical disclosure
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Benchmarks

### PhysicsGate Conflict Detection

Evaluated on 17 published TCM research papers with 8 annotated ground-truth conflicts (3 Type-I, 3 Type-II, 2 Type-III).

| Method | Precision@5 | Precision@10 | Recall@5 | Recall@10 | F1@10 |
|--------|-----------|-------------|---------|----------|-------|
| GPT-4 Self-Check | 0.40 | 0.30 | 0.25 | 0.38 | 0.33 |
| GPT-4 + KG | 0.60 | 0.50 | 0.38 | 0.50 | 0.50 |
| **PhysicsGate** | **1.00** | **1.00** | 0.625 | **0.75** | **0.857** |

Key findings:
- **100% Precision** -- Zero false positives on known conflict types due to deterministic constraint checking
- **75% Recall** -- Miss rate corresponds to edge cases not yet in TCMConstraintLibrary (dosage-dependent conflicts, preparation method interactions)
- **GPT-4 baselines suffer from hallucination** -- Confident but incorrect assessments, especially for rare herb pairs

### PhysicsGate Ablation Study

| Configuration | Precision | Recall | F1 |
|---------------|-----------|--------|-----|
| PhysicsGate (delta=0.05, fixed) | 1.00 | 0.625 | 0.769 |
| PhysicsGate (delta=0.10, fixed) | 1.00 | 0.625 | 0.769 |
| PhysicsGate (no delta decay) | 1.00 | 0.625 | 0.769 |
| **PhysicsGate (full, dynamic decay)** | **1.00** | **0.75** | **0.857** |

The dynamic delta decay mechanism is crucial for recall improvement -- allowing SOFT_REJECT cases to retry with a relaxed threshold catches borderline conflicts.

### PhysicsGate Latency

| Operation | Time Complexity | Measured Latency |
|-----------|----------------|-----------------|
| Single pair lookup | O(1) | < 0.01ms |
| Formula check (10 herbs) | O(n^2) | < 0.1ms |
| GPT-4 single inference | O(n_tokens) | ~2000ms |

PhysicsGate is approximately **200,000x faster** than LLM-based conflict checking for single constraint queries.

### TCM Validation Results

Closed-loop validation on 10 TCM herb pairs (7 conflict, 3 non-conflict):

| Metric | Value |
|--------|-------|
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |
| True Positives | 7 |
| True Negatives | 3 |
| False Positives | 0 |
| False Negatives | 0 |

---

## Research

### SCI Paper Framework

Three versions of the SCI paper framework have been developed:

1. **v1** (`SCI_FRAMEWORK.md`) -- Initial framework with multi-agent architecture and conflict detection
2. **v2** (`SCI_FRAMEWORK_v2_代码融合版.md`) -- Code-integrated version with implementation details
3. **v3** (`SCI_FRAMEWORK_v3_PhysicsGate核心版.md`) -- PhysicsGate-focused version with mathematical formulations, theorems, and proofs

Core contributions for publication:

| Contribution | Description |
|-------------|-------------|
| **C1 (PhysicsGate)** | Physical feedback-driven delta threshold hard gate mechanism with error function E(A_t, K) and three-valued transfer signal |
| **C2 (TCMConstraintLibrary)** | Three-layer TCM compatibility constraint library with O(1) hash-lookup (21 + 9 + 36 pairs) |
| **C3 (Triple-Layer Taxonomy)** | Type-I/II/III conflict classification with four-dimensional credibility scoring |
| **C4 (Dynamic Delta Decay)** | Adaptive threshold mechanism balancing safety (delta=0.05) with usability (delta=0.10) |

### Patent

A patent technical disclosure document (`专利技术交底书.md`) has been prepared covering the PhysicsGate mechanism and TCM constraint validation system.

### Experiment Phases

| Phase | Report | Focus |
|-------|--------|-------|
| Phase 1 | `docs/Phase1_minimal_closed_loop.md` | Minimal closed-loop validation |
| Phase 2 | `docs/Phase2_design.md` | System design and architecture |
| Phase 3 | `docs/Phase3_ablation_report.md` | PhysicsGate ablation study |
| Phase 4 | `docs/Phase4_governance_stress_report.md` | Governance stress testing and threshold sensitivity |

---

## Innovation Roadmap

### Short-term (0-6 months)
- [ ] Integrate LLM API calls for real literature retrieval (replace simulated responses)
- [ ] Connect Neo4j knowledge graph for persistent storage
- [ ] Connect Milvus vector store for semantic search
- [ ] Vue 3 frontend with Three.js knowledge graph visualization

### Medium-term (6-12 months)
- [ ] Expand TCMConstraintLibrary to cover dosage-dependent conflicts
- [ ] Extend PhysicsGate to Western medicine drug interactions
- [ ] Extend PhysicsGate to robot kinematics constraints
- [ ] Production deployment with monitoring and alerting

### Long-term (12+ months)
- [ ] Multi-modal perception integration (vision, touch, proprioception)
- [ ] Real-time motion planning with safety constraints
- [ ] Environmental modeling and prediction
- [ ] Human-robot interaction optimization

---

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/embodied-robot-brain.git
cd embodied-robot-brain

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run linter
ruff check .
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions small and focused (max 20 lines recommended)

### Testing

- Write unit tests for all new functionality
- Aim for 80%+ code coverage
- Use pytest fixtures for common test setup
- Mock external dependencies (LLM APIs, databases)

---

## License

This project is currently unlicensed. All rights reserved by the author.

---

## Contact

For questions, collaboration inquiries, or research discussion, please contact the project maintainer.

---

*Built with FastAPI, multi-agent architecture, and PhysicsGate safety mechanism.*
