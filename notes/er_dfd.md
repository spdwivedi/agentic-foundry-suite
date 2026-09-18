# Agentic Foundry Suite: Data Flow Diagrams & Entity Relationships

This document presents the **Data Flow Diagrams (DFD Level 0 and Level 1)** and the **Entity Relationship (ER) schemas** for the state models and SQLite persistence tables across the suite.

---

## 1. Data Flow Diagrams (DFD)

### 1.1 DFD Level 0: Context Level

```mermaid
flowchart TD
    User([System Operator / Engineer]) -->|CLI Commands & Flags| Core[[Agentic Foundry Suite]]
    Core -->|State Checkpoints| DB[(SQLite Store: agent_state.db)]
    DB -->|Restored State Snapshots| Core
    Core -->|Prompts & Schema Requests| Models[(Gemini API & External Tools)]
    Models -->|Responses & Telemetry| Core
    Core -->|Formatted Logs| Out[/Execution Transcripts & Reports/]
    Out -->|Inspection & Audit| User
```

---

### 1.2 DFD Level 1: Subsystem Level

### 1.2.1 Subsystem 1: Assignment 1 (Research Agent)
```mermaid
flowchart TD
    A1_Input[/Task String + Mock Flag/] --> A1_P1[Process 1.1: Dynamic Planning]
    A1_P1 -->|Action Proposal| A1_P2[Process 1.2: Tool Execution]
    A1_P2 -->|Observation Data| A1_DS1[(Reasoning Trace)]
    A1_DS1 -->|History Feed| A1_P1
    A1_P1 -->|Synthesis Trigger| A1_P3[Process 1.3: Architectural Synthesis]
    A1_P3 --> A1_Out[/Transcript 1 & 2/]
```

### 1.2.2 Subsystem 2: Assignment 2 (Review Gate)
```mermaid
flowchart TD
    A2_Input[/Scenario Flag: pass / fail/] --> A2_P1[Process 2.1: Worker Code Generation]
    A2_P1 -->|Code Artifact + Test Cases| A2_P2[Process 2.2: Review Gatekeeper]
    A2_P1 & A2_P2 -.->|Invocations & Tokens| A2_DS1[(Telemetry Tracker)]
    A2_P2 -->|ReviewVerdict Model| A2_Out[/Transcript 1 & 2/]
```

### 1.2.3 Subsystem 3: Assignment 3 (Resumable Checkpointer)
```mermaid
flowchart TD
    A3_Input[/Config Files + CLI Flags/] --> A3_P1[Process 3.1: Sequential Extraction]
    A3_P1 -->|Thread State Commit| A3_DS1[(SQLite Store: agent_state.db)]
    A3_DS1 -->|State Snapshot Query| A3_P1
    A3_P1 -->|Completed Extractions| A3_P2[Process 3.2: Self-Check Validator]
    A3_P2 --> A3_Out[/Transcript 1 & 2/]
```

---

<div style="page-break-before: always;"></div>

## 2. Entity Relationship (ER) Schemas

### 2.1 Agent State Entity Relationship Diagram

```mermaid
erDiagram
    AGENT_STATE_A1 {
        string task PK
        string reasoning_trace_json
        int tool_call_counter
        boolean mock_failure
        string final_synthesis
        string next_step
        string selected_tool
        json selected_args
    }

    REASONING_STEP_A1 {
        int step PK
        string decision
        string rationale
        json action
        json observation
    }

    MULTI_AGENT_STATE_A2 {
        string task PK
        string scenario
        string worker_output
        json review_verdict
        json telemetry
    }

    REVIEW_VERDICT_A2 {
        string verdict PK
        json criteria_scores
        string_list rejection_reasons
        string review_notes
    }

    CHECKPOINT_STATE_A3 {
        string thread_id PK
        int current_index
        string_list items_to_process
        json completed_items
        json validation_results
        int total_llm_calls
        string_list execution_log
    }

    MICROSERVICE_SPEC_A3 {
        string service_name PK
        string_list compliance_flags
        int_list exposed_ports
        json rate_limits
    }

    SQLITE_CHECKPOINT {
        string thread_id PK
        string checkpoint_ns PK
        string checkpoint_id PK
        string parent_checkpoint_id
        blob type
        blob checkpoint
        blob metadata
    }

    AGENT_STATE_A1 ||--o{ REASONING_STEP_A1 : contains
    MULTI_AGENT_STATE_A2 ||--|| REVIEW_VERDICT_A2 : generates
    CHECKPOINT_STATE_A3 ||--o{ MICROSERVICE_SPEC_A3 : extracts
    CHECKPOINT_STATE_A3 ||--|| SQLITE_CHECKPOINT : persists_to
```

---

## 3. Database Schema: SQLite State Store (`agent_state.db`)

When using `langgraph.checkpoint.sqlite.SqliteSaver`, the backing SQLite database contains the following formal schema:

### 3.1 Table: `checkpoints`
Stores sequential graph execution snapshots keyed by thread and checkpoint version:
```sql
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BLOB,
    metadata BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

### 3.2 Table: `checkpoint_blobs`
Stores binary serialized state payloads using orjson/msgpack serialization:
```sql
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT,
    blob BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
```

### 3.3 Table: `checkpoint_writes`
Captures pending intermediate channel writes between execution steps:
```sql
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BLOB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```
