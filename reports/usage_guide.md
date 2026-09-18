# Agentic Foundry Suite: Quickstart & CLI Usage Guide

A practical operator's guide for setting up, configuring, and executing all three agentic systems from a fresh repository clone.

---

## 1. Prerequisites & Environment Setup

### System Requirements
- **Python**: 3.10 to 3.14 (Verified on Python 3.14 on Windows/Linux/macOS)
- **Google GenAI API Key**: Obtainable from Google AI Studio.

### Step-by-Step Installation
```bash
# 1. Clone repository
git clone <repo-url> agentic-foundry-suite
cd agentic-foundry-suite

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Configure Credentials
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Populate `.env` with your Google API Key:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 2. Command Line Execution Manual

### Assignment 1: Tool-Using Research Agent

#### Scenario 1.1: Clean Research Flow
Runs the agent with fully functional telemetry and mathematical modeling:
```powershell
python assignment-1/agent.py --run-clean
```
- **Output Artifact**: `assignment-1/transcripts/transcript_1_clean.txt`
- **Expected Result**: 2-3 tool calls, complete architectural synthesis, exit code `0`.

#### Scenario 1.2: Failure Recovery Flow
Simulates upstream telemetry outage (HTTP 504) and demonstrates dynamic error recovery:
```powershell
python assignment-1/agent.py --run-failure
```
- **Output Artifact**: `assignment-1/transcripts/transcript_2_failure_recovery.txt`
- **Expected Result**: Detects 504 error, logs recovery rationale, pivots to docs/math, exit code `0`.

---

### Assignment 2: Multi-Agent Task with Review Gate

#### Scenario 2.1: Approval Flow (`pass`)
Worker (Agent A) produces robust, concurrency-safe FastAPI middleware with unit tests. Reviewer (Agent B) grants unanimous approval:
```powershell
python assignment-2/agent.py --scenario pass
```
- **Output Artifact**: `assignment-2/transcripts/transcript_1_approved.txt`
- **Expected Result**: Gate verdict `APPROVED`, 4/4 criteria passed, telemetry summary printed.

#### Scenario 2.2: Rejection Flow (`fail`)
Worker (Agent A) produces draft code omitting `asyncio.Lock` and test cases. Reviewer (Agent B) rejects with itemized defects:
```powershell
python assignment-2/agent.py --scenario fail
```
- **Output Artifact**: `assignment-2/transcripts/transcript_2_rejected.txt`
- **Expected Result**: Gate verdict `REJECTED`, itemized failure list logged, telemetry summary printed.

---

### Assignment 3: Resumable Agent with Checkpointing

#### Scenario 3.1: Interruption & Resumption Cycle

**Step 1: Run Interrupted Pipeline**
Processes items 1 and 2, commits checkpoints to SQLite, and halts:
```powershell
python assignment-3/agent.py --interrupt-after 2
```
- **State Store**: `assignment-3/state_store/agent_state.db` contains checkpoint at index 2.

**Step 2: Resume Pipeline**
Loads checkpoint from SQLite, skips items 1 & 2, processes items 3 & 4, and runs Self-Check:
```powershell
python assignment-3/agent.py --resume
```
- **Output Artifact**: `assignment-3/transcripts/transcript_1_resumed.txt`
- **Expected Result**: Emits `[RESUME SKIP]` for items 1 & 2, Self-Check verdict `PASSED`.

#### Scenario 3.2: Self-Check Failure Catch
Deliberately injects empty/corrupted schema on item 3 (`gateway_service.json`):
```powershell
python assignment-3/agent.py --corrupt-item 3
```
- **Output Artifact**: `assignment-3/transcripts/transcript_2_validation_failed.txt`
- **Expected Result**: Self-Check verdict `FAILED`, itemized validation errors recorded.

---

## 3. Verifying Results & Cleanliness
To verify all transcripts have been generated and populated:
```powershell
Get-ChildItem -Recurse -Filter "*.txt" | Select-Object FullName, Length
```
All transcripts should be non-empty (>3KB) formatted execution logs.
