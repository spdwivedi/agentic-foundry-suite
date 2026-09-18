"""Multi-Agent Task with Review Gate: FastAPI Token-Bucket Rate Limiter."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

load_dotenv()
if "GOOGLE_API_KEY" not in os.environ and "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


class TelemetryCallbackHandler(BaseCallbackHandler):
    """LangChain callback tracking LLM invocations and token usage."""

    def __init__(self):
        super().__init__()
        self.total_llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs):
        self.total_llm_calls += 1
        for gen_list in response.generations:
            for gen in gen_list:
                msg = getattr(gen, "message", None)
                if msg and hasattr(msg, "usage_metadata") and msg.usage_metadata:
                    u = msg.usage_metadata
                    self.prompt_tokens += u.get("input_tokens", 0)
                    self.completion_tokens += u.get("output_tokens", 0)
                    self.total_tokens += u.get("total_tokens", 0)
                    return


class ReviewVerdict(BaseModel):
    """Structured audit verdict from Reviewer Agent B."""
    verdict: Literal["APPROVED", "REJECTED"] = Field(
        description="Final verdict: APPROVED only if all 4 criteria pass, else REJECTED."
    )
    criteria_scores: Dict[str, bool] = Field(
        description="Boolean score for: concurrency_safety, edge_case_resilience, test_completeness, type_annotations_and_docstrings."
    )
    rejection_reasons: List[str] = Field(
        default_factory=list,
        description="Itemized technical failure descriptions if rejected, empty if approved."
    )
    review_notes: str = Field(
        description="Detailed audit narrative explaining evaluation against requirements."
    )


class MultiAgentState(TypedDict):
    """State schema for worker-reviewer multi-agent graph."""
    task: str
    scenario: Literal["pass", "fail"]
    worker_output: str
    review_verdict: Optional[Dict[str, Any]]
    telemetry: Dict[str, int]


def get_chat_model(callbacks: Optional[List[Any]] = None) -> ChatGoogleGenerativeAI:
    """Initialize ChatGoogleGenerativeAI model."""
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        temperature=0.2,
        callbacks=callbacks or [],
    )


def extract_content(content: Any) -> str:
    """Normalize message response content to string."""
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


def worker_node(state: MultiAgentState, callback: TelemetryCallbackHandler) -> Dict[str, Any]:
    """Agent A: Implement FastAPI rate limiter middleware and test cases."""
    time.sleep(1.0)
    scenario = state["scenario"]

    if scenario == "pass":
        prompt = (
            "You are Agent A (Senior Distributed Systems Engineer).\n"
            "Task: Design a production-grade asynchronous FastAPI Token-Bucket Rate Limiter middleware.\n"
            "Strict Requirements for Quality Pass:\n"
            "1. Concurrency safety: Use asyncio.Lock per client/key to ensure atomic token replenishment and consumption across concurrent requests.\n"
            "2. Edge-case resilience: Validate and guard against zero capacity, non-positive or negative refill rates, and use time.monotonic() to eliminate clock drift vulnerabilities.\n"
            "3. Test completeness: Include at least 2 valid, runnable pytest test cases using httpx.AsyncClient or starlette.testclient.TestClient.\n"
            "4. Type annotations & docstrings: Include comprehensive typing (Request, Response, Callable, Optional) and clear docstrings.\n\n"
            "Produce the complete Python implementation followed by unit tests."
        )
    else:
        prompt = (
            "You are Agent A (Junior Developer Draft Mode).\n"
            "Task: Produce a preliminary draft of a FastAPI Token-Bucket Rate Limiter middleware.\n"
            "Important Scenario Directives:\n"
            "- Intentionally omit asyncio.Lock (allow naked race conditions on shared bucket token variables).\n"
            "- Do NOT include any pytest unit test cases (leave tests completely missing).\n"
            "- Provide basic class logic without concurrency safeguards."
        )

    llm = get_chat_model([callback])
    resp = llm.invoke([
        SystemMessage(content="You are Agent A, a software engineer generating code solutions."),
        HumanMessage(content=prompt),
    ])

    return {"worker_output": extract_content(resp.content)}


def reviewer_node(state: MultiAgentState, callback: TelemetryCallbackHandler) -> Dict[str, Any]:
    """Agent B: Perform strict multi-criteria audit on Agent A's output."""
    time.sleep(1.0)
    worker_code = state.get("worker_output", "")

    rubric_prompt = (
        "You are Agent B (Lead Security & Architecture Reviewer).\n"
        "Your task is to conduct an uncompromising audit of Agent A's FastAPI Token-Bucket Rate Limiter implementation.\n\n"
        "Audit against these 4 explicit criteria:\n"
        "1. Concurrency Safety: Must utilize asynchronous locks (asyncio.Lock) or atomic concurrency controls to prevent race conditions during token consumption.\n"
        "2. Edge-Case Resilience: Must explicitly handle zero/negative capacity, non-positive refill rates, and protect against clock drift (e.g. time.monotonic).\n"
        "3. Test Completeness: Must include a minimum of 2 valid pytest test cases demonstrating rate limiting enforcement.\n"
        "4. Type Annotations & Docstrings: Must include complete Python type annotations and concise docstrings.\n\n"
        "Grading Rules:\n"
        "- If ALL 4 criteria pass, set verdict to 'APPROVED'. Rejection reasons must be empty.\n"
        "- If ANY criterion fails, set verdict to 'REJECTED'. Provide itemized, highly specific technical reasons under rejection_reasons.\n\n"
        f"--- AGENT A SUBMISSION ---\n{worker_code}\n--------------------------"
    )

    llm = get_chat_model([callback])
    structured_reviewer = llm.with_structured_output(ReviewVerdict)
    verdict: ReviewVerdict = structured_reviewer.invoke([
        SystemMessage(content="You are an uncompromising code review gatekeeper."),
        HumanMessage(content=rubric_prompt),
    ])

    return {"review_verdict": verdict.model_dump()}


def format_transcript(state: MultiAgentState, telemetry: Dict[str, int]) -> str:
    """Generate formatted multi-agent review transcript."""
    verdict_data = state.get("review_verdict", {})
    verdict = verdict_data.get("verdict", "UNKNOWN")
    scores = verdict_data.get("criteria_scores", {})
    reasons = verdict_data.get("rejection_reasons", [])
    notes = verdict_data.get("review_notes", "")

    lines = []
    lines.append("=" * 80)
    lines.append(f"AGENTIC FOUNDRY SUITE: ASSIGNMENT 2 MULTI-AGENT REVIEW ({state['scenario'].upper()})")
    lines.append("=" * 80)
    lines.append(f"Task: {state['task']}")
    lines.append(f"Scenario Mode: {state['scenario']}")
    lines.append(f"Gate Verdict: {verdict}")
    lines.append("-" * 80)
    lines.append("TELEMETRY SUMMARY:")
    lines.append(f"  Total LLM Calls:       {telemetry.get('total_llm_calls', 0)}")
    lines.append(f"  Prompt Tokens:         {telemetry.get('prompt_tokens', 0)}")
    lines.append(f"  Completion Tokens:     {telemetry.get('completion_tokens', 0)}")
    lines.append(f"  Total Tokens Consumed: {telemetry.get('total_tokens', 0)}")
    lines.append("-" * 80)
    lines.append("CRITERIA SCORECARD:")
    for criterion, passed in scores.items():
        status = "PASSED [OK]" if passed else "FAILED [X]"
        lines.append(f"  - {criterion:<35}: {status}")
    lines.append("-" * 80)

    if reasons:
        lines.append("ITEMIZED REJECTION REASONS:")
        for idx, reason in enumerate(reasons, 1):
            lines.append(f"  {idx}. {reason}")
        lines.append("-" * 80)

    lines.append("REVIEW NOTES:")
    lines.append(notes)
    lines.append("-" * 80)
    lines.append("AGENT A (WORKER) ARTIFACT SUBMISSION:")
    lines.append("-" * 80)
    lines.append(state.get("worker_output", "No code produced."))
    lines.append("\n" + "=" * 80)
    lines.append("END OF TRANSCRIPT")
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    """CLI entrypoint for Assignment 2."""
    parser = argparse.ArgumentParser(description="Multi-Agent Task with Review Gate")
    parser.add_argument(
        "--scenario",
        choices=["pass", "fail"],
        required=True,
        help="pass: Agent A outputs compliant code, Agent B approves. fail: Agent A outputs flawed code, Agent B rejects.",
    )
    args = parser.parse_args()

    telemetry_handler = TelemetryCallbackHandler()

    graph = StateGraph(MultiAgentState)
    graph.add_node("worker", lambda s: worker_node(s, telemetry_handler))
    graph.add_node("reviewer", lambda s: reviewer_node(s, telemetry_handler))

    graph.set_entry_point("worker")
    graph.add_edge("worker", "reviewer")
    graph.add_edge("reviewer", END)

    compiled_graph = graph.compile()

    initial_state: MultiAgentState = {
        "task": "Design and review an asynchronous FastAPI Token-Bucket Rate Limiter middleware.",
        "scenario": args.scenario,
        "worker_output": "",
        "review_verdict": None,
        "telemetry": {},
    }

    final_state = compiled_graph.invoke(initial_state)

    telemetry_summary = {
        "total_llm_calls": telemetry_handler.total_llm_calls,
        "prompt_tokens": telemetry_handler.prompt_tokens,
        "completion_tokens": telemetry_handler.completion_tokens,
        "total_tokens": telemetry_handler.total_tokens,
    }

    transcript_dir = Path(__file__).resolve().parent / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    if args.scenario == "pass":
        transcript_file = transcript_dir / "transcript_1_approved.txt"
    else:
        transcript_file = transcript_dir / "transcript_2_rejected.txt"

    transcript_content = format_transcript(final_state, telemetry_summary)
    transcript_file.write_text(transcript_content, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Scenario: {args.scenario.upper()} Execution Completed")
    print(f"Review Verdict: {final_state['review_verdict']['verdict']}")
    print(f"Transcript written to: {transcript_file}")
    print("Telemetry Metrics:")
    print(f"  Total LLM Calls:   {telemetry_summary['total_llm_calls']}")
    print(f"  Prompt Tokens:     {telemetry_summary['prompt_tokens']}")
    print(f"  Completion Tokens: {telemetry_summary['completion_tokens']}")
    print(f"  Total Tokens:      {telemetry_summary['total_tokens']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
