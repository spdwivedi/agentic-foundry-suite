# Agentic Foundry Suite: Agent Model & Persona Cards

This document provides formal Agent Cards documenting the models, system prompts, roles, inputs, outputs, and constraints for each agent in the suite.

---

## 1. Model Card: Gemini 3.1 Flash Lite

- **Model Identifier**: `gemini-3.1-flash-lite`
- **Provider**: Google DeepMind / Google Cloud GenAI
- **SDK**: `langchain-google-genai` (v4.4.0) & `google-genai` (v2.24.0)
- **Quota & Limits**: 15 RPM (Requests Per Minute), 500 RPD (Requests Per Day)
- **Sampling Parameters**: `temperature=0.2`, deterministic top-k / top-p
- **Primary Strengths**: Low-latency structured output parsing, high JSON schema fidelity, cost-effective reasoning.

---

## 2. Agent Card: Assignment 1 Dynamic Research Planner

### Role & Purpose
Autonomous database infrastructure evaluation agent capable of dynamic multi-turn planning, tool dispatching, fault recovery, and architectural synthesis.

- **System Persona**: *"You are a Principal Database Infrastructure Architect. You plan and orchestrate infrastructure investigations, handle external service failures gracefully, and synthesize authoritative technical recommendations."*
- **Inputs**:
  - `task` (`str`): Target research question.
  - `reasoning_trace` (`List[Dict]`): Cumulative history of prior actions and tool observations.
  - `tool_call_counter` (`int`): Count of invoked tools.
- **Tools Available**:
  - `system_metrics_api(engine: str)`
  - `doc_lookup(query: str)`
  - `latency_math_engine(throughput_rps: int, cores: int)`
- **Outputs**:
  - Structured `PlannerOutput`: `decision` ("TOOL_CALL" | "SYNTHESIZE"), `rationale`, `tool_name`, `tool_args`.
  - Final synthesis markdown document.
- **Safety Bounds**:
  - Monitored tool ceiling: Halts immediately if `tool_call_counter >= 6`.
  - Fault tolerance: Intercepts HTTP 504 errors and dynamically shifts strategy without crashing.

---

## 3. Agent Card: Assignment 2 Worker Agent (Agent A)

### Role & Purpose
Distributed systems software engineer responsible for implementing production-ready asynchronous ASGI middleware and comprehensive test suites.

- **System Persona**: *"You are Agent A, a senior distributed systems engineer generating robust, production-grade code solutions."*
- **Inputs**:
  - Task instructions detailing rate-limiting requirements (concurrency, clock drift, edge cases, unit tests).
  - Scenario toggle (`pass` vs. `fail`).
- **Outputs**:
  - Complete Python code artifact containing FastAPI middleware and pytest test cases.
- **Key Invariants**:
  - Uses `asyncio.Lock` per key to ensure atomicity.
  - Employs `time.monotonic()` to defend against clock drift.
  - Validates positive integers for capacity and refill rates.

---

## 4. Agent Card: Assignment 2 Reviewer Gatekeeper (Agent B)

### Role & Purpose
Zero-trust security and architecture gatekeeper auditing submitted code against an uncompromising 4-part grading rubric.

- **System Persona**: *"You are Agent B, an uncompromising code review gatekeeper. You conduct rigorous audits of code for concurrency, edge cases, test completeness, and type annotations."*
- **Inputs**:
  - Complete code artifact submitted by Agent A.
  - Mandatory grading rubric.
- **Outputs**:
  - Structured `ReviewVerdict`:
    - `verdict`: `Literal["APPROVED", "REJECTED"]`
    - `criteria_scores`: `Dict[str, bool]`
    - `rejection_reasons`: `List[str]`
    - `review_notes`: `str`
- **Audit Rules**:
  - Unanimous pass required: If any criterion fails, `verdict` is set to `REJECTED` with specific itemized feedback.

---

## 5. Agent Card: Assignment 3 Microservice Spec Extractor

### Role & Purpose
Stateful JSON parser extracting network, compliance, and rate limiting specifications from raw service configuration files.

- **System Persona**: *"You extract structured network and compliance specs from microservice configuration files."*
- **Inputs**: Raw JSON file contents.
- **Outputs**: Structured `MicroserviceSpec`:
  - `service_name: str`
  - `compliance_flags: List[str]`
  - `exposed_ports: List[int]`
  - `rate_limits: Dict[str, Any]`

---

## 6. Agent Card: Assignment 3 Self-Check Validation Auditor

### Role & Purpose
Post-processing quality assurance node inspecting completed configuration records for schema compliance and non-emptiness.

- **System Persona**: *"You are a Quality & Schema Compliance Auditor. You validate JSON schema completeness, non-empty fields, and valid port/rate specifications."*
- **Inputs**: Aggregated dictionary of completed service specifications.
- **Outputs**: Structured `SelfCheckVerdict`:
  - `all_valid: bool`
  - `item_validity: Dict[str, bool]`
  - `flagged_errors: List[str]`
  - `validation_summary: str`
