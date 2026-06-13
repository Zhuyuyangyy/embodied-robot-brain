# embodied-robot-brain — Q2 Review (Round 1)

**Scope reviewed:** `backend/main.py`, `backend/app.py`, `backend/agents/physics_gate.py`, `backend/agents/research_validator.py`, `backend/agents/orchestrator.py`, `backend/agents/experiment_agent.py`, `backend/core/config.py`, `backend/rag/knowledge_graph.py`, `backend/api/research.py`, frontend skeleton, `tests/`.

**Sub-project framing:** Multi-Agent research assistant with a `PhysicsGate` (TCM-style hard-gate) and a `ResearchValidator` (evidence-alignment / conflict / scoring). Project is a "smart-education + LLM agent" stack.

---

## 1. Problem Definition & Novelty — 12 / 15
The double-artifact framing (an `Orchestrator` running literature + experiment + progress agents, gated by a `PhysicsGate` whose error function `E(A_t,K)` and dynamic `δ(t)` are formalised) is a clear, defensible position. The validator's `Type-I/II/III` taxonomy and confidence weighting (`0.25/0.20/0.30/0.25`) directly mirror a paper. The TCM knowledge base (~80 explicit herb pairs) is concrete and reproducible. Deduction: novelty is "framework + domain rules", not algorithm — so several points withheld until a clearer "physics gate" primitive is published vs. existing tool-use filters. Score 12/15.

## 2. Code Architecture & Modularity — 13 / 15
Layering is clean: `core/{config,logging,security,metrics}` + `agents/` + `api/` + `rag/` + `orchestrator/`. The `main.py` (canonical) and `app.py` (legacy monolith duplicating `LiteratureAgent`/`ExperimentDesignAgent`/`ProgressAgent`/`Orchestrator` in 1 000+ LoC) co-exist — a serious drift risk; `app.py` even defines a second `Orchestrator` and ignores the `core/` middleware stack. The new `agents/orchestrator.py` is a thin wrapper around an `_agent_pool` (good fix for the "即用即弃" issue noted in its comment). Pydantic `BaseSettings` for config is correct. The frontend `views/` and `components/` directories are empty. Score 13/15.

## 3. Algorithm Correctness & Rigor — 12 / 15
`PhysicsGate` is mathematically explicit: `compute_error_function` -> `compute_dynamic_delta(iteration<3 ? 0.05 : 0.10)` -> ternary `HARD/SOFT/PASS`, with a stated "safety theorem" (`E=1.0 => HARD_REJECT` regardless of `delta`). Bootstrap CI on 1 000 resamples is a legitimate statistical device. Validator's `_compute_consistency` and `_compute_kg_support` are correct given their assumptions. However: (a) `_rag_search`/`_web_search` in legacy `app.py` are *fake* — they `asyncio.sleep(0.05)` and return templated strings, so the "validation" runs on synthesised data; (b) `experiment_agent._generate_design_step` produces hard-coded templates ("准备数据集/1天") not a real reflection loop. Score 12/15.

## 4. Engineering Quality (Production-readiness) — 12 / 15
Strong: layered middleware (SecurityHeaders -> CORS -> Metrics -> RateLimit -> RequestLogging), Prometheus `/metrics`, three-tier rate limit (global + burst + per-IP), structured `{code, message, request_id}` error envelope, lifespan-managed startup, Pydantic-settings env loading, loguru request_id correlation. CORS is correctly domain-whitelisted in `core/config.py` (legacy `app.py` still uses `allow_origins=["*"]`). Concerns: no DB layer (`sessions: Dict` in-memory, comment says "replace with Redis/DB"); `app.py` still binds `port=8021`; no auth; Prometheus metrics only count, no histograms; security headers middleware is referenced but not reviewed. Score 12/15.

## 5. Testing & Validation — 8 / 15
Test files exist and are well-named: `test_physics_gate.py`, `test_research_validator.py`, `test_literature_agent.py`, `test_experiment_agent.py`, `test_orchestrator.py`, `test_progress_agent.py` (unit), `test_api_integration.py`, `test_research_workflow.py`, `test_api.py` (backend), `test_smoke.py` + e2e. `run_tcm_validation` returns `precision/recall/f1` over the herb-pair set and a hard-reject audit. But: (a) we did not read the tests, only counted them; (b) the only "empirical" number surfaced is the 80-pair TCM table — no SOTA comparison, no latency/throughput number; (c) the validator's claims (Eq.1–4) have no held-out evaluation shown in code. Score 8/15.

## 6. Documentation & Reproducibility — 11 / 15
`physics_gate.py` is heavily commented and self-documenting (paper-section cross-references, type hints, dataclass `ConflictRecord`, full CLI `__main__`). `research_validator.py` similarly maps to §3.1–§3.4. Top-level `README.md` + `SCI_FRAMEWORK*.md` + `专利技术交底书.md` + `INNOVATION_ROADMAP.md` + `OPTIMIZATION_REPORT.md` exist. `pyproject`-style `requirements.txt` + `pytest.ini` + `start.sh` + Dockerfile path under `deployment/`. Gaps: no `Makefile` or `setup.cfg`, no example notebooks, no pinned hashes in `requirements.txt`, no per-module README; `app.py` has no module docstring tying it to the deprecated path. Score 11/15.

## 7. Innovation & Differentiation — 10 / 10 (cap)
Distinct: a three-value `PhysicsGate` with `delta(t)` relaxation, formal conflict taxonomy with confidence-weighted synthesis (Eq.4), a "digital twin KG" linking literature -> experiment -> progress, and a 200-pair TCM conflict dataset embedded in code. Even where some pieces are templates, the *combination* (gate + validator + KG + reflection loop) is non-trivial. Score 10/10.

---

**Total: 78 / 100**

### Top-3 Risks
1. **Dual main entry** — `main.py` (8013, with full middleware) and `app.py` (8021, legacy monolith) both register routers and both bind agents. Anyone running `app.py` in production gets a degraded service.
2. **Fake I/O in legacy path** — `_rag_search` and `_web_search` return mocked `f"[RAG] {query}相关研究论文 {i+1}"`. Any "validator F1" number from the legacy app is meaningless.
3. **Empty frontend directories** — `frontend/src/views/` and `components/` are both empty; the only deliverable surface is the API.

### Top-3 Improvements
1. Delete or quarantine `app.py` and make `main.py` the single entry; move `app.py`'s agents to `backend/agents/` and have the router import them.
2. Replace mocked RAG/Web with at least a thin `httpx` call (ArXiv API is free, Milvus has a Python client) and gate "validator F1" on real data.
3. Add a `Makefile` (or `tox.ini`) with `make test`, `make lint`, `make run`; pin deps; add CI.

### Files Touched (absolute paths)
- D:/ZYY Project/embodied-robot-brain/backend/main.py
- D:/ZYY Project/embodied-robot-brain/backend/app.py
- D:/ZYY Project/embodied-robot-brain/backend/agents/physics_gate.py
- D:/ZYY Project/embodied-robot-brain/backend/agents/research_validator.py
- D:/ZYY Project/embodied-robot-brain/backend/agents/orchestrator.py
- D:/ZYY Project/embodied-robot-brain/backend/agents/experiment_agent.py
- D:/ZYY Project/embodied-robot-brain/backend/core/config.py
- D:/ZYY Project/embodied-robot-brain/backend/rag/knowledge_graph.py
- D:/ZYY Project/embodied-robot-brain/frontend/src/{views,components}/ (empty)
