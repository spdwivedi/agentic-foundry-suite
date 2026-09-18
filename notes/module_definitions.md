# Agentic Foundry Suite: Module & Symbol Definitions

A comprehensive technical dictionary documenting every class, function, TypedDict, Pydantic model, state variable, and utility across the repository.

---

## 1. Assignment 1 Modules

### File: `assignment-1/tools.py`

#### Functions
- **`doc_lookup(query: str) -> Dict[str, Any]`**
  - **Description**: Technical documentation retrieval engine for Redis Cluster and KeyDB.
  - **Parameters**: `query: str` — Search query keywords (e.g., "redis", "keydb", "threading", "overhead").
  - **Returns**: Dictionary with architectural specifications, clustering models, per-key memory overheads, and throughput scaling.
- **`latency_math_engine(throughput_rps: int, cores: int) -> Dict[str, Any]`**
  - **Description**: Quantitative queuing model computing core saturation factor, per-core RPS, and projected p99 tail latency.
  - **Parameters**:
    - `throughput_rps: int` — Target read request rate per second.
    - `cores: int` — Available CPU cores.
  - **Returns**: Dictionary with `per_core_rps`, `core_utilization_pct`, `projected_p99_latency_ms`, and saturation `status`.
- **`system_metrics_api(engine: str, mock_failure: bool = False) -> Dict[str, Any]`**
  - **Description**: Production telemetry emulator for Redis Cluster and KeyDB.
  - **Parameters**:
    - `engine: str` — Target database engine name ("redis" or "keydb").
    - `mock_failure: bool` — If True, simulates daemon outage returning HTTP 504 Gateway Timeout.
  - **Returns**: Telemetry dictionary with QPS, CPU utilization, per-key memory bytes, and RSS footprint.

---

### File: `assignment-1/agent.py`

#### Classes & Types
- **`AgentState(TypedDict)`**
  - `task: str` — The objective prompt.
  - `messages: List[Any]` — Graph message history.
  - `reasoning_trace: List[Dict[str, Any]]` — Step-by-step audit trail (step, decision, rationale, action, observation).
  - `tool_call_counter: int` — Monotonically increasing tool invocation counter.
  - `mock_failure: bool` — Boolean toggle injecting HTTP 504 fault.
  - `final_synthesis: str` — Formatted architectural report.
  - `next_step: Optional[str]` — Planner routing flag (`TOOL_CALL` or `SYNTHESIZE`).
  - `selected_tool: Optional[str]` — Selected tool identifier.
  - `selected_args: Optional[Dict[str, Any]]` — Tool invocation parameters.
  - `current_rationale: Optional[str]` — Model rationale string.
- **`PlannerOutput(BaseModel)`**
  - `decision: Literal["TOOL_CALL", "SYNTHESIZE"]` — Next action signal.
  - `rationale: str` — Detailed justification for current step.
  - `tool_name: Optional[Literal["doc_lookup", "latency_math_engine", "system_metrics_api"]]` — Tool name.
  - `tool_args: Optional[Dict[str, Any]]` — Argument dictionary.

#### Functions
- **`get_chat_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI`**
  - Instantiates Gemini model (`gemini-3.1-flash-lite`) configured with Google GenAI credentials.
- **`dynamic_planner(state: AgentState) -> Dict[str, Any]`**
  - LangGraph node evaluating accumulated observations and deciding whether to invoke tools or synthesize. Enforces 6-call safety ceiling.
- **`execute_tool(state: AgentState) -> Dict[str, Any]`**
  - Dispatches tool invocation, captures results, updates trace, and increments counter.
- **`synthesize_results(state: AgentState) -> Dict[str, Any]`**
  - Produces multi-section final engineering comparison report.
- **`route_planner(state: AgentState) -> str`**
  - Conditional routing edge directing state to `execute_tool` or `synthesize`.
- **`build_research_graph() -> CompiledGraph`**
  - Assembles and compiles the StateGraph workflow.
- **`format_transcript(state: AgentState, mode: str) -> str`**
  - Serializes state into human-readable transcript format.
- **`main() -> None`**
  - CLI argument handler supporting `--run-clean` and `--run-failure`.

---

## 2. Assignment 2 Modules

### File: `assignment-2/agent.py`

#### Classes & Types
- **`TelemetryCallbackHandler(BaseCallbackHandler)`**
  - Tracks LLM calls, prompt tokens, completion tokens, and aggregate tokens across graph execution turns via `on_llm_end`.
- **`ReviewVerdict(BaseModel)`**
  - `verdict: Literal["APPROVED", "REJECTED"]` — Final review decision.
  - `criteria_scores: Dict[str, bool]` — Scorecard for 4 criteria.
  - `rejection_reasons: List[str]` — Itemized defect notes.
  - `review_notes: str` — Audit narrative.
- **`MultiAgentState(TypedDict)`**
  - `task: str` — Task description.
  - `scenario: Literal["pass", "fail"]` — Test scenario.
  - `worker_output: str` — Code and tests from Agent A.
  - `review_verdict: Optional[Dict[str, Any]]` — Audit verdict from Agent B.
  - `telemetry: Dict[str, int]` — Usage metrics.

#### Functions
- **`get_chat_model(callbacks: Optional[List[Any]] = None) -> ChatGoogleGenerativeAI`**
  - Instantiates `gemini-3.1-flash-lite` attached to telemetry callback listeners.
- **`extract_content(content: Any) -> str`**
  - Normalizes string and multi-part content structures from LangChain messages.
- **`worker_node(state: MultiAgentState, callback: TelemetryCallbackHandler) -> Dict[str, Any]`**
  - Generates rate limiter middleware and test cases under `pass` or `fail` prompts.
- **`reviewer_node(state: MultiAgentState, callback: TelemetryCallbackHandler) -> Dict[str, Any]`**
  - Audits Worker code against concurrency, edge-case, testing, and typing criteria.
- **`format_transcript(state: MultiAgentState, telemetry: Dict[str, int]) -> str`**
  - Formats scorecard, rejection items, review notes, and telemetry summary.
- **`main() -> None`**
  - CLI entrypoint accepting `--scenario pass` or `--scenario fail`.

---

## 3. Assignment 3 Modules

### File: `assignment-3/agent.py`

#### Classes & Types
- **`MicroserviceSpec(BaseModel)`**
  - `service_name: str` — Name of microservice.
  - `compliance_flags: List[str]` — Extracted compliance standards.
  - `exposed_ports: List[int]` — List of exposed TCP/UDP ports.
  - `rate_limits: Dict[str, Any]` — Extracted rate limiting policies.
- **`SelfCheckVerdict(BaseModel)`**
  - `all_valid: bool` — Overall compliance boolean.
  - `item_validity: Dict[str, bool]` — Per-file validity indicators.
  - `flagged_errors: List[str]` — Itemized failure list.
  - `validation_summary: str` — Comprehensive validation review notes.
- **`CheckpointState(TypedDict)`**
  - `items_to_process: List[str]` — List of service JSON filenames.
  - `completed_items: Dict[str, Any]` — Dict of extracted specifications.
  - `current_index: int` — Pointer to active item.
  - `validation_results: Dict[str, Any]` — Self-check verdict dictionary.
  - `total_llm_calls: int` — Invocations counter.
  - `execution_log: List[str]` — Step log entries.
  - `interrupt_after: Optional[int]` — Interruption index threshold.
  - `corrupt_item: Optional[int]` — Index of item to corrupt for testing.

#### Functions
- **`get_chat_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI`**
  - Initializes Gemini model.
- **`extract_config(file_path: Path, model: ChatGoogleGenerativeAI) -> Dict[str, Any]`**
  - Reads service JSON fixture and extracts `MicroserviceSpec`.
- **`process_item_node(state: CheckpointState) -> Dict[str, Any]`**
  - Sequential loop step extracting one microservice and persisting state to SQLite.
- **`should_continue(state: CheckpointState) -> str`**
  - Router directing flow to `process_item`, `interrupt_exit`, or `self_check`.
- **`interrupt_exit_node(state: CheckpointState) -> Dict[str, Any]`**
  - Halts execution when interrupt threshold is reached and records persistence log.
- **`self_check_node(state: CheckpointState) -> Dict[str, Any]`**
  - Post-processing auditor validating schema compliance across all items.
- **`build_graph(checkpointer: SqliteSaver) -> CompiledGraph`**
  - Compiles state graph bound to SQLite checkpointer.
- **`format_transcript(state: CheckpointState, title: str) -> str`**
  - Formats execution log, extracted JSON specs, and validation verdict into transcript.
- **`main() -> None`**
  - CLI entrypoint supporting `--interrupt-after`, `--resume`, and `--corrupt-item`.
