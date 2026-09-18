# Agentic Foundry Suite: Execution Workflows & State Lifecycles

This document details the lifecycle workflows, step-by-step state transitions, loop control mechanics, and checkpointer recovery pathways across all three assignments.

---

## 1. Assignment 1 Workflow: Dynamic Tool-Using Research Agent

### 1.1 State Transition Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Graph as LangGraph Engine
    participant Planner as dynamic_planner Node
    participant Executor as execute_tool Node
    participant Registry as Tool Registry
    participant Synth as synthesize_results Node

    User->>Graph: invoke(task, mock_failure)
    Graph->>Planner: Execute turn with AgentState
    alt Tool Call Selected & Counter < 6
        Planner-->>Graph: PlannerOutput(decision="TOOL_CALL", tool, args)
        Graph->>Executor: execute_tool(selected_tool, args)
        Executor->>Registry: invoke target tool (API / Docs / Math)
        Registry-->>Executor: tool observation payload
        Executor-->>Graph: return updated reasoning_trace & counter+1
        Graph->>Planner: Next planning cycle
    else Safety Limit Hit (Counter >= 6) or Sufficient Evidence
        Planner-->>Graph: PlannerOutput(decision="SYNTHESIZE")
        Graph->>Synth: synthesize_results(reasoning_trace)
        Synth-->>Graph: final_synthesis markdown
        Graph-->>User: Complete research transcript
    end
```

### 1.2 Failure Recovery Decision Path
1. **Initial Action**: The agent chooses `system_metrics_api(engine="redis")` to query live telemetry.
2. **Error Injection**: When `mock_failure=True`, the tool returns:
   ```json
   {"status": 504, "error": "Gateway Timeout: Telemetry daemon unreachable after 5000ms"}
   ```
3. **Detection & Pivot**: In the next turn, `dynamic_planner` inspects the trace, detects the 504 error, and logs:
   > *"The system_metrics_api returned a 504 Gateway Timeout for the Redis telemetry query. Given the failure to retrieve live metrics, I must pivot to theoretical analysis. I will use doc_lookup to retrieve the architectural specifications..."*
4. **Resilient Continuation**: Executes `doc_lookup` and `latency_math_engine`, successfully obtaining the metrics needed to complete the recommendation without crashing.

---

## 2. Assignment 2 Workflow: Multi-Agent Review Gate

### 2.1 Workflow Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor CLI as Command Line Runner
    participant Graph as Multi-Agent Graph
    participant Telemetry as TelemetryCallbackHandler
    participant AgentA as Agent A (Worker)
    participant AgentB as Agent B (Reviewer)

    CLI->>Graph: invoke(scenario="pass" | "fail")
    Graph->>AgentA: worker_node(state, callback)
    AgentA->>Telemetry: on_llm_start / on_llm_end
    AgentA-->>Graph: Return worker_output (FastAPI middleware code)
    
    Graph->>AgentB: reviewer_node(state, callback)
    AgentB->>Telemetry: on_llm_start / on_llm_end
    AgentB-->>Graph: Return ReviewVerdict (Pydantic structured output)
    
    Graph-->>CLI: Format transcript & print telemetry summary
```

### 2.2 Branching Scenarios & Verdict State Matrix

| Step / Property | Pass Scenario (`--scenario pass`) | Fail Scenario (`--scenario fail`) |
| :--- | :--- | :--- |
| **Worker Directive** | High-assurance production implementation | Draft mode with intentional defects |
| **Locks Present** | `asyncio.Lock()` per key | None (naked shared dictionary) |
| **Clock Source** | `time.monotonic()` (clock-drift immune) | `time.time()` (vulnerable to NTP jumps) |
| **Input Validation** | Rejects `capacity <= 0` or `refill <= 0` | Missing |
| **Pytest Cases** | 2 valid async/sync test cases | 0 test cases |
| **Reviewer Verdict**| **APPROVED** | **REJECTED** |
| **Criteria Scores** | 4/4 True | 0/4 True |
| **Rejection Reasons**| None (empty list) | 5 itemized failure reasons |

---

## 3. Assignment 3 Workflow: Resumable Checkpoint Pipeline

### 3.1 Interruption & Resumption Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Runner as Pipeline Runner
    participant Engine as LangGraph Runtime
    participant Node as process_item_node
    participant SQLite as SQLite State Store (agent_state.db)
    participant Validator as self_check_node

    Note over Runner, SQLite: RUN 1: --interrupt-after 2
    Runner->>Engine: invoke(items=[1,2,3,4], interrupt_after=2)
    Engine->>Node: Process Item 1 (auth_service.json)
    Node->>SQLite: Save Checkpoint (index=1, items={auth})
    Engine->>Node: Process Item 2 (billing_service.json)
    Node->>SQLite: Save Checkpoint (index=2, items={auth, billing})
    Engine->>Engine: Router evaluates idx (2) == interrupt_after (2)
    Engine-->>Runner: Exit with State Interrupted

    Note over Runner, SQLite: RUN 2: --resume
    Runner->>SQLite: get_state(thread_id="microservice_pipeline_thread")
    SQLite-->>Runner: Loaded Checkpoint (completed={auth, billing}, idx=2)
    Runner->>Engine: invoke(resumed_state)
    Note over Engine: Log [RESUME SKIP] for Item 1 & 2
    Engine->>Node: Process Item 3 (gateway_service.json)
    Node->>SQLite: Save Checkpoint (index=3, items={auth, billing, gateway})
    Engine->>Node: Process Item 4 (event_stream.json)
    Node->>SQLite: Save Checkpoint (index=4, items={auth, billing, gateway, event})
    Engine->>Validator: Validate completed_items
    Validator-->>Runner: Emit SelfCheckVerdict(all_valid=True)
```

### 3.2 Corrupted Item Self-Check Decision Path (`--corrupt-item 3`)
1. **Pipeline Execution**: Items 1, 2, 3, and 4 are processed sequentially.
2. **Fault Injection**: At index 3 (`gateway_service.json`), the pipeline injects an empty payload:
   ```json
   {
     "service_name": "",
     "compliance_flags": [],
     "exposed_ports": [],
     "rate_limits": {}
   }
   ```
3. **Self-Check Audit**: The `self_check` node runs Gemini against all 4 records.
4. **Violation Catch**:
   - `all_valid`: `false`
   - `flagged_errors`:
     - `gateway_service.json: service_name is empty`
     - `gateway_service.json: compliance_flags is empty`
     - `gateway_service.json: exposed_ports is empty`
     - `gateway_service.json: rate_limits is empty`
5. **Report Generation**: State is committed and recorded in `transcript_2_validation_failed.txt`.
