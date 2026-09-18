# Agentic AI Engineering Take-Home Submission Document

**Candidate Name**: Surya Prakash Dwivedi  
**Role**: Junior AI Engineer (Autonomous Agent Products)  
**Email**: suryaprakashsep2001@gmail.com  
**Phone**: +91 9169124559  
**GitHub Profile**: [https://github.com/spdwivedi](https://github.com/spdwivedi)  
**Primary Repository**: [https://github.com/spdwivedi/agentic-foundry-suite](https://github.com/spdwivedi/agentic-foundry-suite)  
**Google Drive Mirror**: [https://drive.google.com/drive/folders/1fsD6fGxkANd9p5qgBXegWZejLKLqX2tx?usp=sharing](https://drive.google.com/drive/folders/1fsD6fGxkANd9p5qgBXegWZejLKLqX2tx?usp=sharing)  
**Date**: September 18, 2026  
**Primary Frameworks**: LangGraph, LangChain Google GenAI, Pydantic v2, SQLite  
**Foundation Model**: Google Gemini 3.1 Flash Lite (`gemini-3.1-flash-lite`)  

---

## 1. Executive Summary

This submission provides end-to-end implementations, real execution transcripts, and comprehensive architectural documentation for all three take-home assignments:
1. **Assignment 1: Tool-Using Research Agent**: Evaluates Redis Cluster vs KeyDB for a 100k read req/sec caching tier. Features dynamic multi-turn planning, a hard safety ceiling of 6 tool calls, and resilient recovery when the telemetry daemon encounters an HTTP 504 Gateway Timeout.
2. **Assignment 2: Multi-Agent Task with Review Gate**: Implements a two-agent pipeline featuring an engineering worker (Agent A) and an adversarial auditor (Agent B) evaluating an asynchronous FastAPI Token-Bucket rate limiter middleware across 4 strict criteria with full telemetry tracking.
3. **Assignment 3: Resumable Agent with Checkpointing**: Demonstrates crash-resilient sequential microservice configuration processing backed by `SqliteSaver`. Supports arbitrary execution interruption, state resumption with zero-loss item skipping, and a self-check validation node capable of catching injected schema corruption.

All code has been executed in a clean virtual environment, generating authentic transcript files verified with exit code `0`.

---

## 2. Assignment 1: Tool-Using Research Agent

### 2.1 Problem & Research Question
> *"Compare Redis Cluster vs KeyDB for an in-memory caching layer handling 100k read req/sec, and recommend one for low-memory overhead deployments."*

### 2.2 System Design
- **LangGraph State Machine**: Uses typed channel dictionary `AgentState` maintaining task, reasoning trace, tool call counter, failure flag, and synthesis.
- **Dynamic Tool Dispatcher**: Employs `gemini-3.1-flash-lite` with structured `PlannerOutput` to select tools based on evidence gathered so far, rather than executing a hardcoded sequence.
- **Tool Suite**:
  - `doc_lookup`: Returns architectural specifications, sharding, and memory overheads.
  - `latency_math_engine`: Computes queue saturation and projected p99 tail latency.
  - `system_metrics_api`: Emulates live cluster metrics (QPS, RSS, CPU) with a 504 mock fault injection switch.
- **Failure Recovery Invariant**: When `system_metrics_api` fails with HTTP 504, the agent logs the failure in its rationale, switches to `doc_lookup` and `latency_math_engine`, and successfully synthesizes the report.

### 2.3 Key Architectural Findings
- **Threading Model**: Redis uses a single-threaded execution core per shard, requiring 4-6 primary instances to service 100k read req/sec. KeyDB uses a multi-threaded shared-nothing architecture capable of saturating 8 cores within a single instance.
- **Memory Overhead**: Redis baseline overhead is ~54-65 bytes per key plus jemalloc multi-process fragmentation and cluster bus overhead. KeyDB averages ~42-50 bytes per key.
- **Recommendation**: **KeyDB** is recommended for low-memory overhead deployments at 100k read req/sec.

### 2.4 Execution Transcript Summaries
- **Clean Run (`--run-clean`)**:
  - Invocations: 2 tool calls (`doc_lookup`, `latency_math_engine`).
  - Output: `assignment-1/transcripts/transcript_1_clean.txt`.
- **Failure Recovery Run (`--run-failure`)**:
  - Step 1: `system_metrics_api` returns 504 Gateway Timeout.
  - Step 2: Agent logs error in rationale, pivots to `doc_lookup`.
  - Step 3: Executes `latency_math_engine`.
  - Step 4: Delivers complete final synthesis without crashing.
  - Output: `assignment-1/transcripts/transcript_2_failure_recovery.txt`.

---

## 3. Assignment 2: Multi-Agent Task with Review Gate

### 3.1 Problem & Specification
Design and review a production-grade asynchronous FastAPI Token-Bucket Rate Limiter middleware.

### 3.2 System Design
- **Agent A (Worker)**: Emits FastAPI middleware utilizing `BaseHTTPMiddleware`, `asyncio.Lock()`, `time.monotonic()`, and runnable pytest test cases.
- **Agent B (Reviewer)**: Independent gatekeeper evaluating code against 4 criteria:
  1. *Concurrency Safety* (`asyncio.Lock` per client)
  2. *Edge-Case Resilience* (zero/negative capacity, negative refill, clock drift)
  3. *Test Completeness* (minimum 2 valid pytest test cases)
  4. *Type Annotations & Docstrings* (full typing and concise docstrings)
- **Telemetry Subsystem**: Integrated `TelemetryCallbackHandler` capturing prompt tokens, completion tokens, total tokens, and invocation counts.

### 3.3 Evaluation Results & Transcripts
- **Pass Scenario (`--scenario pass`)**:
  - Gate Verdict: **APPROVED**
  - Scorecard: 4/4 criteria passed.
  - Telemetry: 2 LLM calls, 1,503 prompt tokens, 1,244 completion tokens, 2,747 total tokens.
  - Output: `assignment-2/transcripts/transcript_1_approved.txt`.
- **Fail Scenario (`--scenario fail`)**:
  - Gate Verdict: **REJECTED**
  - Scorecard: 0/4 criteria passed.
  - Rejection Reasons:
    1. Missing `asyncio.Lock` (race condition vulnerability)
    2. Clock drift vulnerability (uses `time.time()` instead of `time.monotonic()`)
    3. Missing input validation for non-positive capacity/refill
    4. Missing pytest test cases
    5. Incomplete type annotations and docstrings
  - Telemetry: 2 LLM calls, 814 prompt tokens, 759 completion tokens, 1,573 total tokens.
  - Output: `assignment-2/transcripts/transcript_2_rejected.txt`.

---

## 4. Assignment 3: Resumable Agent with Checkpointing

### 4.1 Problem & Specification
Sequentially process 4 microservice configurations (`auth_service.json`, `billing_service.json`, `gateway_service.json`, `event_stream.json`), extracting compliance flags, exposed ports, and rate limits. Support arbitrary process interruption, state resumption, and schema validation.

### 4.2 System Design
- **Persistence Engine**: LangGraph with `SqliteSaver` targeting `state_store/agent_state.db`.
- **Sequential Execution**: Processes one configuration per loop iteration, committing state transactionally to SQLite after each step.
- **Resume & Skip Semantics**: Upon `--resume`, the graph loads the state snapshot for `microservice_pipeline_thread`, inspects `completed_items`, logs `[RESUME SKIP]` for previously completed items, and resumes strictly on pending items.
- **Downstream Self-Check Node**: Executes after all items complete, auditing records against 4 schema invariants.
- **Corruption Injection (`--corrupt-item 3`)**: Deliberately injects an empty schema into item 3 (`gateway_service.json`), verifying that the Self-Check node detects and flags the violation.

### 4.3 Execution Results & Transcripts
- **Interrupted Run & Resumption**:
  - Trigger: `python assignment-3/agent.py --interrupt-after 2` followed by `python assignment-3/agent.py --resume`.
  - Log verification:
    ```
    [INTERRUPT] Simulated process termination reached after item 2. Checkpoint saved.
    [RESUME SKIP] Item 1 (auth_service.json) already verified in checkpoint. Skipping extraction.
    [RESUME SKIP] Item 2 (billing_service.json) already verified in checkpoint. Skipping extraction.
    [PROCESS] Processing item index 3/4: gateway_service.json
    [PROCESS] Processing item index 4/4: event_stream.json
    [SELF-CHECK] Audit completed with verdict: PASSED
    ```
  - Output: `assignment-3/transcripts/transcript_1_resumed.txt`.
- **Validation Failure Catch**:
  - Trigger: `python assignment-3/agent.py --corrupt-item 3`.
  - Result: Self-Check verdict `FAILED`. Flagged:
    - `gateway_service.json: service_name is empty`
    - `gateway_service.json: compliance_flags is empty`
    - `gateway_service.json: exposed_ports is empty`
    - `gateway_service.json: rate_limits is empty`
  - Output: `assignment-3/transcripts/transcript_2_validation_failed.txt`.

---

## 5. Summary of Deliverables & Documentation Index

| File | Purpose |
| :--- | :--- |
| `assignment-1/tools.py` | Registry of database specs, queuing math, and telemetry emulator |
| `assignment-1/agent.py` | Dynamic ReAct research agent with 6-call ceiling and 504 recovery |
| `assignment-1/README.md` | Architecture, tool registry, and reproduction guide for Assignment 1 |
| `assignment-2/agent.py` | Multi-agent review pipeline with Pydantic gatekeeper and telemetry |
| `assignment-2/README.md` | Worker-reviewer specs, grading rubrics, and reproduction guide |
| `assignment-3/agent.py` | Resumable pipeline with SQLite checkpointing and Self-Check node |
| `assignment-3/data/*.json` | 4 microservice configuration fixtures |
| `assignment-3/README.md` | Checkpointing schema, resume skip semantics, and reproduction guide |
| `notes/architecture.md` | Topological blueprints and StateGraph wiring diagrams |
| `notes/workflows.md` | Sequence diagrams and state transition lifecycles |
| `notes/er_dfd.md` | DFD Level 0/1 diagrams and Entity Relationship schemas |
| `notes/module_definitions.md` | Complete symbol and API dictionary across the repository |
| `reports/master_report.md` | Executive summary and evaluation scorecard |
| `reports/technical_report.md` | In-depth engineering analysis on recovery, checkpointing, and tokens |
| `reports/agent_cards.md` | Detailed model and agent cards for all personas |
| `reports/io_specifications.md` | Formal JSON schemas for inputs, states, and outputs |
| `reports/usage_guide.md` | Operator CLI manual from a clean repository clone |
| `README.md` | Root repository portfolio guide with badges and navigation links |
