"""Resumable Agent with SQLite Checkpointing and Validation Self-Check."""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

load_dotenv()
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


class MicroserviceSpec(BaseModel):
    """Schema for extracted microservice configuration."""
    service_name: str = Field(description="Name of the service")
    compliance_flags: List[str] = Field(description="List of compliance standards, e.g. SOC2, PCI-DSS, HIPAA")
    exposed_ports: List[int] = Field(description="List of integer port numbers exposed")
    rate_limits: Dict[str, Any] = Field(description="Extracted rate limit settings including RPS and burst")


class SelfCheckVerdict(BaseModel):
    """Schema for self-check validation node."""
    all_valid: bool = Field(description="True if all microservices have complete, non-empty, valid extractions")
    item_validity: Dict[str, bool] = Field(description="Per-file validity status mapping")
    flagged_errors: List[str] = Field(default_factory=list, description="List of validation failures detected")
    validation_summary: str = Field(description="Summary of the validation audit")


class CheckpointState(TypedDict):
    """State schema for resumable agent."""
    items_to_process: List[str]
    completed_items: Dict[str, Any]
    current_index: int
    validation_results: Dict[str, Any]
    total_llm_calls: int
    execution_log: List[str]
    interrupt_after: Optional[int]
    corrupt_item: Optional[int]


def get_chat_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Initialize ChatGoogleGenerativeAI model."""
    return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=temperature)


def extract_config(file_path: Path, model: ChatGoogleGenerativeAI) -> Dict[str, Any]:
    """Extract compliance, ports, and rate limits from JSON config via LLM."""
    time.sleep(1.0)
    content = file_path.read_text(encoding="utf-8")
    prompt = (
        f"Extract compliance flags, exposed ports, and rate limits from this microservice config:\n\n"
        f"{content}\n\n"
        f"Return structured fields matching MicroserviceSpec."
    )
    structured_llm = model.with_structured_output(MicroserviceSpec)
    spec: MicroserviceSpec = structured_llm.invoke([
        SystemMessage(content="You extract structured network and compliance specs."),
        HumanMessage(content=prompt),
    ])
    return spec.model_dump()


def process_item_node(state: CheckpointState) -> Dict[str, Any]:
    """Sequential processing node for a single microservice configuration."""
    idx = state["current_index"]
    items = state["items_to_process"]
    completed = dict(state.get("completed_items", {}))
    logs = list(state.get("execution_log", []))
    llm_calls = state.get("total_llm_calls", 0)

    item_name = items[idx]
    logs.append(f"[PROCESS] Processing item index {idx + 1}/{len(items)}: {item_name}")

    corrupt_target = state.get("corrupt_item")
    if corrupt_target is not None and (idx + 1) == corrupt_target:
        logs.append(f"[INJECT] Deliberately injecting corrupt empty schema into item {idx + 1} ({item_name})")
        corrupt_payload = {
            "service_name": "",
            "compliance_flags": [],
            "exposed_ports": [],
            "rate_limits": {},
        }
        completed[item_name] = corrupt_payload
    else:
        data_path = Path(__file__).resolve().parent / "data" / item_name
        model = get_chat_model()
        extracted = extract_config(data_path, model)
        llm_calls += 1
        completed[item_name] = extracted
        logs.append(f"[SUCCESS] Extracted ports {extracted['exposed_ports']}, compliance {extracted['compliance_flags']}")

    logs.append(f"[CHECKPOINT] State persisted for item {item_name} (Current Index: {idx + 1})")

    return {
        "completed_items": completed,
        "current_index": idx + 1,
        "execution_log": logs,
        "total_llm_calls": llm_calls,
    }


def should_continue(state: CheckpointState) -> str:
    """Conditional router enforcing sequential step loop and interrupt limit."""
    idx = state["current_index"]
    items = state["items_to_process"]
    interrupt_after = state.get("interrupt_after")

    if interrupt_after is not None and idx >= interrupt_after and idx < len(items):
        return "interrupt_exit"
    if idx < len(items):
        return "process_item"
    return "self_check"


def interrupt_exit_node(state: CheckpointState) -> Dict[str, Any]:
    """Handle simulated process interruption."""
    logs = list(state.get("execution_log", []))
    logs.append(f"[INTERRUPT] Simulated process termination reached after item {state['current_index']}. Checkpoint saved.")
    return {"execution_log": logs}


def self_check_node(state: CheckpointState) -> Dict[str, Any]:
    """Validate completeness and schema integrity of all processed items."""
    time.sleep(1.0)
    completed = state.get("completed_items", {})
    logs = list(state.get("execution_log", []))
    llm_calls = state.get("total_llm_calls", 0)

    logs.append("[SELF-CHECK] Executing validation check across all completed configurations.")
    prompt = (
        f"You are a Quality & Schema Compliance Auditor.\n"
        f"Review the extracted microservice specifications below:\n\n"
        f"{json.dumps(completed, indent=2)}\n\n"
        f"Validation Criteria:\n"
        f"1. Each service must have a non-empty service_name.\n"
        f"2. Each service must have at least one compliance flag in compliance_flags.\n"
        f"3. Each service must have at least one valid port number in exposed_ports.\n"
        f"4. Each service must contain rate limit parameters.\n\n"
        f"If ANY service fails any criterion, set all_valid to false, flag the specific item in item_validity, and detail the defect in flagged_errors."
    )

    model = get_chat_model()
    structured_checker = model.with_structured_output(SelfCheckVerdict)
    verdict: SelfCheckVerdict = structured_checker.invoke([
        SystemMessage(content="You validate JSON schema completeness."),
        HumanMessage(content=prompt),
    ])
    llm_calls += 1

    status_str = "PASSED" if verdict.all_valid else "FAILED"
    logs.append(f"[SELF-CHECK] Audit completed with verdict: {status_str}")
    if not verdict.all_valid:
        for err in verdict.flagged_errors:
            logs.append(f"[VALIDATION ERROR] {err}")

    return {
        "validation_results": verdict.model_dump(),
        "execution_log": logs,
        "total_llm_calls": llm_calls,
    }


def build_graph(checkpointer: SqliteSaver):
    """Construct and compile LangGraph StateGraph with checkpointing."""
    graph = StateGraph(CheckpointState)
    graph.add_node("process_item", process_item_node)
    graph.add_node("interrupt_exit", interrupt_exit_node)
    graph.add_node("self_check", self_check_node)

    graph.set_entry_point("process_item")
    graph.add_conditional_edges(
        "process_item",
        should_continue,
        {
            "process_item": "process_item",
            "interrupt_exit": "interrupt_exit",
            "self_check": "self_check",
        },
    )
    graph.add_edge("interrupt_exit", END)
    graph.add_edge("self_check", END)

    return graph.compile(checkpointer=checkpointer)


def format_transcript(state: CheckpointState, title: str) -> str:
    """Format execution trace and checkpoint state into text transcript."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"AGENTIC FOUNDRY SUITE: ASSIGNMENT 3 CHECKPOINT TRANSCRIPT ({title.upper()})")
    lines.append("=" * 80)
    lines.append(f"Items to Process: {len(state.get('items_to_process', []))}")
    lines.append(f"Completed Items:  {len(state.get('completed_items', {}))}")
    lines.append(f"Total LLM Calls:  {state.get('total_llm_calls', 0)}")
    lines.append("-" * 80)
    lines.append("EXECUTION LOGS:")
    for log in state.get("execution_log", []):
        lines.append(f"  {log}")
    lines.append("-" * 80)
    lines.append("FINAL EXTRACTED MICROSERVICE DATA:")
    lines.append(json.dumps(state.get("completed_items", {}), indent=2))
    lines.append("-" * 80)
    lines.append("SELF-CHECK VALIDATION VERDICT:")
    lines.append(json.dumps(state.get("validation_results", {}), indent=2))
    lines.append("-" * 80)
    lines.append("END OF TRANSCRIPT")
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    """CLI entrypoint for Assignment 3."""
    parser = argparse.ArgumentParser(description="Resumable Agent with SQLite Checkpointing")
    parser.add_argument("--interrupt-after", type=int, default=None, help="Interrupt execution after N items")
    parser.add_argument("--resume", action="store_true", help="Resume pipeline from persisted SQLite checkpoint")
    parser.add_argument("--corrupt-item", type=int, default=None, help="Inject empty/corrupt schema at item index N (1-indexed)")
    args = parser.parse_args()

    data_items = [
        "auth_service.json",
        "billing_service.json",
        "gateway_service.json",
        "event_stream.json",
    ]

    state_store_dir = Path(__file__).resolve().parent / "state_store"
    state_store_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_store_dir / "agent_state.db"

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()

    thread_id = "microservice_pipeline_thread"
    config = {"configurable": {"thread_id": thread_id}}

    compiled_graph = build_graph(saver)
    transcript_dir = Path(__file__).resolve().parent / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    if args.resume:
        print("[RESUME] Connecting to SQLite checkpointer...")
        saved_snapshot = compiled_graph.get_state(config)
        if not saved_snapshot or not saved_snapshot.values:
            print("[ERROR] No existing checkpoint found in state store. Run with --interrupt-after first.")
            conn.close()
            sys.exit(1)

        resumed_state = dict(saved_snapshot.values)
        existing_completed = resumed_state.get("completed_items", {})
        logs = list(resumed_state.get("execution_log", []))
        logs.append(f"[RESUME] Checkpoint retrieved from {db_path} for thread '{thread_id}'")

        for idx, itm in enumerate(resumed_state["items_to_process"]):
            if itm in existing_completed:
                logs.append(f"[RESUME SKIP] Item {idx + 1} ({itm}) already verified in checkpoint. Skipping extraction.")
            else:
                logs.append(f"[RESUME PENDING] Item {idx + 1} ({itm}) pending processing.")

        resumed_state["interrupt_after"] = None
        resumed_state["execution_log"] = logs

        final_state = compiled_graph.invoke(resumed_state, config)
        transcript_path = transcript_dir / "transcript_1_resumed.txt"
        transcript_content = format_transcript(final_state, "Resumed Pipeline Run")
        transcript_path.write_text(transcript_content, encoding="utf-8")
        print(f"[SUCCESS] Resumed pipeline completed. Output written to: {transcript_path}")

    else:
        initial_state: CheckpointState = {
            "items_to_process": data_items,
            "completed_items": {},
            "current_index": 0,
            "validation_results": {},
            "total_llm_calls": 0,
            "execution_log": [
                f"[START] Initializing fresh microservice pipeline with {len(data_items)} items",
                f"[STORE] Checkpointer targeting {db_path}",
            ],
            "interrupt_after": args.interrupt_after,
            "corrupt_item": args.corrupt_item,
        }

        final_state = compiled_graph.invoke(initial_state, config)

        if args.interrupt_after:
            print(f"[INTERRUPT] Interrupted after {args.interrupt_after} items. State saved to {db_path}.")
        elif args.corrupt_item:
            transcript_path = transcript_dir / "transcript_2_validation_failed.txt"
            transcript_content = format_transcript(final_state, "Corrupted Item Validation Failure")
            transcript_path.write_text(transcript_content, encoding="utf-8")
            print(f"[VALIDATION FAILURE RECORDED] Transcript written to: {transcript_path}")

    conn.close()


if __name__ == "__main__":
    main()
