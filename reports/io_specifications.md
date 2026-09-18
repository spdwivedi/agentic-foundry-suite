# Agentic Foundry Suite: Input/Output Specifications

This document defines the formal JSON schemas for inputs, graph states, tool calls, and structured outputs across the suite.

---

## 1. Assignment 1 Specifications

### 1.1 State Schema: `AgentState`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentState",
  "type": "object",
  "properties": {
    "task": { "type": "string" },
    "messages": { "type": "array", "items": { "type": "object" } },
    "reasoning_trace": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step": { "type": "integer" },
          "decision": { "type": "string" },
          "rationale": { "type": "string" },
          "action": { "type": "object" },
          "observation": { "type": "object" }
        },
        "required": ["step", "decision", "rationale", "action", "observation"]
      }
    },
    "tool_call_counter": { "type": "integer", "minimum": 0 },
    "mock_failure": { "type": "boolean" },
    "final_synthesis": { "type": "string" },
    "next_step": { "type": ["string", "null"], "enum": ["TOOL_CALL", "SYNTHESIZE", null] },
    "selected_tool": { "type": ["string", "null"] },
    "selected_args": { "type": ["object", "null"] },
    "current_rationale": { "type": ["string", "null"] }
  },
  "required": ["task", "messages", "reasoning_trace", "tool_call_counter", "mock_failure"]
}
```

### 1.2 Tool Call Schema: `system_metrics_api`
```json
{
  "title": "SystemMetricsAPI",
  "type": "object",
  "properties": {
    "engine": { "type": "string", "enum": ["redis", "keydb"] },
    "mock_failure": { "type": "boolean", "default": false }
  },
  "required": ["engine"]
}
```

### 1.3 Tool Call Schema: `latency_math_engine`
```json
{
  "title": "LatencyMathEngine",
  "type": "object",
  "properties": {
    "throughput_rps": { "type": "integer", "minimum": 1 },
    "cores": { "type": "integer", "minimum": 1 }
  },
  "required": ["throughput_rps", "cores"]
}
```

---

## 2. Assignment 2 Specifications

### 2.1 State Schema: `MultiAgentState`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MultiAgentState",
  "type": "object",
  "properties": {
    "task": { "type": "string" },
    "scenario": { "type": "string", "enum": ["pass", "fail"] },
    "worker_output": { "type": "string" },
    "review_verdict": { "$ref": "#/definitions/ReviewVerdict" },
    "telemetry": {
      "type": "object",
      "properties": {
        "total_llm_calls": { "type": "integer" },
        "prompt_tokens": { "type": "integer" },
        "completion_tokens": { "type": "integer" },
        "total_tokens": { "type": "integer" }
      }
    }
  },
  "required": ["task", "scenario", "worker_output"]
}
```

### 2.2 Output Schema: `ReviewVerdict`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewVerdict",
  "type": "object",
  "properties": {
    "verdict": { "type": "string", "enum": ["APPROVED", "REJECTED"] },
    "criteria_scores": {
      "type": "object",
      "properties": {
        "concurrency_safety": { "type": "boolean" },
        "edge_case_resilience": { "type": "boolean" },
        "test_completeness": { "type": "boolean" },
        "type_annotations_and_docstrings": { "type": "boolean" }
      },
      "required": [
        "concurrency_safety",
        "edge_case_resilience",
        "test_completeness",
        "type_annotations_and_docstrings"
      ]
    },
    "rejection_reasons": {
      "type": "array",
      "items": { "type": "string" }
    },
    "review_notes": { "type": "string" }
  },
  "required": ["verdict", "criteria_scores", "rejection_reasons", "review_notes"]
}
```

---

## 3. Assignment 3 Specifications

### 3.1 State Schema: `CheckpointState`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CheckpointState",
  "type": "object",
  "properties": {
    "items_to_process": {
      "type": "array",
      "items": { "type": "string" }
    },
    "completed_items": {
      "type": "object",
      "additionalProperties": { "$ref": "#/definitions/MicroserviceSpec" }
    },
    "current_index": { "type": "integer", "minimum": 0 },
    "validation_results": { "$ref": "#/definitions/SelfCheckVerdict" },
    "total_llm_calls": { "type": "integer", "minimum": 0 },
    "execution_log": {
      "type": "array",
      "items": { "type": "string" }
    },
    "interrupt_after": { "type": ["integer", "null"] },
    "corrupt_item": { "type": ["integer", "null"] }
  },
  "required": ["items_to_process", "completed_items", "current_index", "total_llm_calls"]
}
```

### 3.2 Output Schema: `MicroserviceSpec`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MicroserviceSpec",
  "type": "object",
  "properties": {
    "service_name": { "type": "string" },
    "compliance_flags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "exposed_ports": {
      "type": "array",
      "items": { "type": "integer" }
    },
    "rate_limits": { "type": "object" }
  },
  "required": ["service_name", "compliance_flags", "exposed_ports", "rate_limits"]
}
```

### 3.3 Output Schema: `SelfCheckVerdict`
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SelfCheckVerdict",
  "type": "object",
  "properties": {
    "all_valid": { "type": "boolean" },
    "item_validity": {
      "type": "object",
      "additionalProperties": { "type": "boolean" }
    },
    "flagged_errors": {
      "type": "array",
      "items": { "type": "string" }
    },
    "validation_summary": { "type": "string" }
  },
  "required": ["all_valid", "item_validity", "flagged_errors", "validation_summary"]
}
```
