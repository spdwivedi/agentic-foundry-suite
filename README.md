# Agentic Foundry Suite

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-LangGraph%20%7C%20LangChain-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Model](https://img.shields.io/badge/Model-Gemini%203.1%20Flash%20Lite-green.svg)](https://ai.google.dev/)
[![Status](https://img.shields.io/badge/Suite%20Status-Verified%20%26%20Passing-brightgreen.svg)]()

A production-grade collection of agentic systems demonstrating **dynamic tool orchestration**, **multi-agent adversarial review gates**, and **transactional state checkpointing** using **LangGraph** and Google Gemini.

---

## Portfolio Index

| Assignment | Domain & Challenge | Key Architectural Patterns | Transcripts & Docs |
| :--- | :--- | :--- | :--- |
| **[Assignment 1: Research Agent](./assignment-1/)** | Database Architecture Evaluation (Redis vs KeyDB at 100k RPS) | Dynamic ReAct planning, 6-call hard safety ceiling, HTTP 504 error recovery | [Clean Run](./assignment-1/transcripts/transcript_1_clean.txt) <br> [Failure Recovery](./assignment-1/transcripts/transcript_2_failure_recovery.txt) |
| **[Assignment 2: Review Gate](./assignment-2/)** | Distributed Systems Code Review (FastAPI Token-Bucket Middleware) | Worker-Reviewer pair, Pydantic structured audit verdict, LangChain callback telemetry | [Approved Run](./assignment-2/transcripts/transcript_1_approved.txt) <br> [Rejected Run](./assignment-2/transcripts/transcript_2_rejected.txt) |
| **[Assignment 3: Resumable Agent](./assignment-3/)** | Microservice Configuration Compliance Ingestion | Native SQLite checkpointing (`SqliteSaver`), arbitrary interrupt/resume, Self-Check auditor | [Resumed Run](./assignment-3/transcripts/transcript_1_resumed.txt) <br> [Corruption Caught](./assignment-3/transcripts/transcript_2_validation_failed.txt) |

---

## Technical Notes & Architectural Blueprints

Comprehensive architectural diagrams and engineering specifications are organized in the [`notes/`](./notes/) directory:
- **[Topological Architecture](./notes/architecture.md)**: StateGraph diagrams, node configurations, routing conditions, and invariants.
- **[Execution Workflows](./notes/workflows.md)**: Sequence diagrams, loop lifecycles, and checkpointer resume pathways.
- **[DFD & Entity Relationships](./notes/er_dfd.md)**: DFD Level 0, DFD Level 1, ER diagrams, and SQLite schema.
- **[Module Definitions Dictionary](./notes/module_definitions.md)**: Complete API dictionary of classes, functions, and state channels.

---

## Executive Reports & Specifications

Detailed performance evaluations and technical analyses are located in the [`reports/`](./reports/) directory:
- **[Master Evaluation Report](./reports/master_report.md)**: Executive summary, scorecard, and scenario test results matrix.
- **[Deep-Dive Technical Report](./reports/technical_report.md)**: Queuing model mathematics, SQLite binary serialization, and token efficiency analysis.
- **[Agent Model Cards](./reports/agent_cards.md)**: Persona specifications, system prompts, inputs, outputs, and constraints.
- **[Input/Output Specifications](./reports/io_specifications.md)**: Formal JSON schemas for inputs, states, tool calls, and outputs.
- **[CLI Usage Guide](./reports/usage_guide.md)**: Operator quickstart guide from a clean repository clone.
- **[Complete Submission Document](./reports/submission_document.md)**: Publication-grade submission package ready for evaluation.

---

## Quickstart Installation & Execution

### 1. Setup Environment
```bash
git clone https://github.com/spdwivedi/agentic-foundry-suite.git
cd agentic-foundry-suite

python -m venv .venv
# Activate virtual environment
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # Linux / macOS

pip install -r requirements.txt
```

### 2. Configure Credentials
Create a `.env` file in the root folder:
```ini
GEMINI_API_KEY=your_google_ai_studio_key_here
```

### 3. Reproduce All Scenarios

```powershell
# --- Assignment 1: Research Agent ---
python assignment-1/agent.py --run-clean
python assignment-1/agent.py --run-failure

# --- Assignment 2: Multi-Agent Review Gate ---
python assignment-2/agent.py --scenario pass
python assignment-2/agent.py --scenario fail

# --- Assignment 3: Resumable Checkpoint Agent ---
python assignment-3/agent.py --interrupt-after 2
python assignment-3/agent.py --resume
python assignment-3/agent.py --corrupt-item 3
```

---

## License
MIT License. Developed as part of the Agentic Foundry Suite.
