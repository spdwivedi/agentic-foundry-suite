"""Tool-Using Research Agent for evaluating Redis Cluster vs KeyDB."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import doc_lookup, latency_math_engine, system_metrics_api

load_dotenv()
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


class AgentState(TypedDict):
    """Execution state for research agent."""
    task: str
    messages: List[Any]
    reasoning_trace: List[Dict[str, Any]]
    tool_call_counter: int
    mock_failure: bool
    final_synthesis: str
    next_step: Optional[str]
    selected_tool: Optional[str]
    selected_args: Optional[Dict[str, Any]]
    current_rationale: Optional[str]


class PlannerOutput(BaseModel):
    """Structured decision output from dynamic planner."""
    decision: Literal["TOOL_CALL", "SYNTHESIZE"] = Field(
        description="Choose TOOL_CALL to query tools or SYNTHESIZE once sufficient evidence is gathered."
    )
    rationale: str = Field(
        description="Detailed technical reasoning documenting evaluation, failures observed, and why this action was selected."
    )
    tool_name: Optional[Literal["doc_lookup", "latency_math_engine", "system_metrics_api"]] = Field(
        default=None,
        description="Tool name to execute when decision is TOOL_CALL."
    )
    tool_args: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters for tool execution."
    )


def get_chat_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Initialize ChatGoogleGenerativeAI using gemini-3.1-flash-lite."""
    return ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=temperature)


def dynamic_planner(state: AgentState) -> Dict[str, Any]:
    """Determine next action based on accumulated trace, failure history, and safety ceiling."""
    time.sleep(1.0)
    call_count = state.get("tool_call_counter", 0)
    if call_count >= 6:
        return {
            "next_step": "SYNTHESIZE",
            "current_rationale": "Hard safety ceiling of 6 tool calls reached. Forcing immediate final synthesis.",
            "selected_tool": None,
            "selected_args": {},
        }

    trace = state.get("reasoning_trace", [])
    trace_json = json.dumps(trace, indent=2)

    prompt = (
        f"You are a Principal Database Infrastructure Architect.\n"
        f"Target Research Task: \"{state['task']}\"\n\n"
        f"Available Tools:\n"
        f"1. system_metrics_api(engine: str): Query live telemetry for 'redis' or 'keydb' (returns measured QPS, CPU, RSS memory, per-key overhead).\n"
        f"2. doc_lookup(query: str): Inspect technical specifications, threading models, and memory architectures.\n"
        f"3. latency_math_engine(throughput_rps: int, cores: int): Compute per-core load, saturation factor, and p99 latency.\n\n"
        f"Investigation Guidelines:\n"
        f"- Current Tool Invocations: {call_count}/6.\n"
        f"- Priority: Start by querying live telemetry using system_metrics_api to gather real-world cluster metrics.\n"
        f"- Resilience & Recovery: If system_metrics_api returns status 504 or an error, explicitly state the failure in your rationale, formulate a recovery strategy, and pivot to doc_lookup and latency_math_engine to retrieve specifications and calculate load.\n"
        f"- Once empirical or theoretical evidence covers throughput, p99 latency, and memory overhead for both Redis Cluster and KeyDB, select SYNTHESIZE.\n\n"
        f"Current Reasoning Trace History:\n{trace_json}\n"
    )

    llm = get_chat_model(temperature=0.2)
    structured_llm = llm.with_structured_output(PlannerOutput)
    plan: PlannerOutput = structured_llm.invoke([
        SystemMessage(content="You dynamically plan database benchmarking steps."),
        HumanMessage(content=prompt),
    ])

    return {
        "next_step": plan.decision,
        "current_rationale": plan.rationale,
        "selected_tool": plan.tool_name,
        "selected_args": plan.tool_args or {},
    }


def execute_tool(state: AgentState) -> Dict[str, Any]:
    """Execute selected tool and record step details into reasoning trace."""
    time.sleep(1.0)
    tool_name = state.get("selected_tool")
    tool_args = state.get("selected_args") or {}
    rationale = state.get("current_rationale") or ""
    current_count = state.get("tool_call_counter", 0) + 1

    try:
        if tool_name == "doc_lookup":
            obs = doc_lookup(tool_args.get("query", "specs"))
        elif tool_name == "latency_math_engine":
            obs = latency_math_engine(
                throughput_rps=int(tool_args.get("throughput_rps", 100000)),
                cores=int(tool_args.get("cores", 4)),
            )
        elif tool_name == "system_metrics_api":
            obs = system_metrics_api(
                engine=str(tool_args.get("engine", "redis")),
                mock_failure=state.get("mock_failure", False),
            )
        else:
            obs = {"error": f"Unknown tool requested: {tool_name}"}
    except Exception as exc:
        obs = {"status": 500, "error": str(exc)}

    step_record = {
        "step": len(state.get("reasoning_trace", [])) + 1,
        "decision": f"EXECUTE_TOOL:{tool_name}",
        "rationale": rationale,
        "action": {"tool": tool_name, "args": tool_args},
        "observation": obs,
    }

    updated_trace = list(state.get("reasoning_trace", []))
    updated_trace.append(step_record)

    return {
        "reasoning_trace": updated_trace,
        "tool_call_counter": current_count,
        "selected_tool": None,
        "selected_args": None,
    }


def synthesize_results(state: AgentState) -> Dict[str, Any]:
    """Generate final architectural comparison and recommendation from reasoning trace."""
    time.sleep(1.0)
    trace_json = json.dumps(state.get("reasoning_trace", []), indent=2)
    prompt = (
        f"You are a Principal Database Infrastructure Architect. Provide a comprehensive, rigorous architectural evaluation.\n\n"
        f"Target Research Task: \"{state['task']}\"\n\n"
        f"Reasoning Trace & Collected Data:\n{trace_json}\n\n"
        f"Required Sections:\n"
        f"1. Executive Summary & Final Recommendation (Definitive verdict for low-memory overhead caching at 100k read req/sec)\n"
        f"2. Threading Model & Architectural Comparison (Redis single-threaded shard model vs KeyDB multi-threaded shared-nothing model)\n"
        f"3. Throughput & Latency Analysis at 100k RPS (Core saturation, node footprint, and p99 projections)\n"
        f"4. Memory Overhead Breakdown (Per-key dict/robj structures, jemalloc fragmentation, clustering metadata cost)\n"
        f"5. Telemetry & Fault Recovery Audit (Summary of telemetry observations and fallback decisions if encountered)\n"
        f"6. Production Deployment Blueprint (Specific hardware sizing, instance count, core allocation, and configuration tuning)"
    )

    llm = get_chat_model(temperature=0.2)
    resp = llm.invoke([
        SystemMessage(content="You write detailed infrastructure evaluation reports."),
        HumanMessage(content=prompt),
    ])

    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and "text" in item:
                    parts.append(item["text"])
                elif hasattr(item, "text"):
                    parts.append(getattr(item, "text"))
            return "\n".join(parts)
        return str(content)

    synthesis_text = _extract_text(resp.content)

    final_step = {
        "step": len(state.get("reasoning_trace", [])) + 1,
        "decision": "FINAL_SYNTHESIS",
        "rationale": state.get("current_rationale", "Synthesizing architectural recommendation from empirical findings."),
        "action": {"action": "synthesize_recommendation"},
        "observation": {"status": "completed", "output_characters": len(synthesis_text)},
    }
    updated_trace = list(state.get("reasoning_trace", []))
    updated_trace.append(final_step)

    return {
        "final_synthesis": synthesis_text,
        "reasoning_trace": updated_trace,
    }


def route_planner(state: AgentState) -> str:
    """Route to tool execution or final synthesis."""
    if state.get("next_step") == "SYNTHESIZE" or state.get("tool_call_counter", 0) >= 6:
        return "synthesize"
    return "execute_tool"


def build_research_graph():
    """Build and compile LangGraph StateGraph."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", dynamic_planner)
    graph.add_node("execute_tool", execute_tool)
    graph.add_node("synthesize", synthesize_results)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        route_planner,
        {
            "execute_tool": "execute_tool",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("execute_tool", "planner")
    graph.add_edge("synthesize", END)

    return graph.compile()


def format_transcript(state: AgentState, mode: str) -> str:
    """Format execution trace into clean readable transcript."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"AGENTIC FOUNDRY SUITE: ASSIGNMENT 1 RESEARCH TRANSCRIPT ({mode.upper()})")
    lines.append("=" * 80)
    lines.append(f"Task: {state['task']}")
    lines.append(f"Mock Failure Enabled: {state['mock_failure']}")
    lines.append(f"Total Tool Invocations: {state['tool_call_counter']}")
    lines.append("-" * 80)
    lines.append("EXECUTION & REASONING TRACE:")
    lines.append("-" * 80)

    for item in state.get("reasoning_trace", []):
        lines.append(f"\n[STEP {item['step']}] DECISION: {item['decision']}")
        lines.append(f"Rationale:   {item['rationale']}")
        lines.append(f"Action:      {json.dumps(item['action'])}")
        lines.append(f"Observation: {json.dumps(item['observation'], indent=2)}")

    lines.append("\n" + "=" * 80)
    lines.append("FINAL ARCHITECTURAL SYNTHESIS:")
    lines.append("=" * 80)
    lines.append(state.get("final_synthesis", "No synthesis generated."))
    lines.append("\n" + "=" * 80)
    lines.append("END OF TRANSCRIPT")
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    """CLI entrypoint for Assignment 1."""
    parser = argparse.ArgumentParser(description="Tool-Using Research Agent: Redis Cluster vs KeyDB")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-clean", action="store_true", help="Execute clean workflow with functioning telemetry")
    group.add_argument("--run-failure", action="store_true", help="Execute failure recovery workflow with mock 504 gateway timeout")
    args = parser.parse_args()

    task_prompt = (
        "Compare Redis Cluster vs KeyDB for an in-memory caching layer handling 100k read req/sec, "
        "and recommend one for low-memory overhead deployments."
    )

    initial_state: AgentState = {
        "task": task_prompt,
        "messages": [],
        "reasoning_trace": [],
        "tool_call_counter": 0,
        "mock_failure": args.run_failure,
        "final_synthesis": "",
        "next_step": None,
        "selected_tool": None,
        "selected_args": None,
        "current_rationale": None,
    }

    graph = build_research_graph()
    final_output = graph.invoke(initial_state)

    transcript_dir = Path(__file__).resolve().parent / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    if args.run_clean:
        output_file = transcript_dir / "transcript_1_clean.txt"
        transcript_text = format_transcript(final_output, "Clean Execution")
    else:
        output_file = transcript_dir / "transcript_2_failure_recovery.txt"
        transcript_text = format_transcript(final_output, "Failure Recovery Execution")

    output_file.write_text(transcript_text, encoding="utf-8")
    print(f"Execution finished successfully. Transcript written to: {output_file}")
    print(f"Total Tool Invocations: {final_output['tool_call_counter']}")
    print(f"Trace Steps Recorded: {len(final_output['reasoning_trace'])}")


if __name__ == "__main__":
    main()
