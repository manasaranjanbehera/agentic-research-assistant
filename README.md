# Agentic Research & Reporting Assistant (AWS Bedrock)

A small, production-shaped multi-agent system: a **Researcher** agent gathers
facts using tool-calling against a knowledge base, a **Summarizer** agent turns
them into a structured report, and a **Critic** agent reviews the report and
sends it back for revision (bounded rounds) before approving a final answer.

This is the "researcher → summarizer → critic" agentic pattern — a lightweight,
automated QA gate that catches unsupported claims before they reach a user,
instead of trusting a single model call to get everything right first try.

## Architecture

```
 topic
   │
   ▼
┌─────────────┐   tool call    ┌───────────────────┐
│  Researcher  │ ─────────────▶│ search_documents() │  (swap for a real
│   (Bedrock)  │ ◀───────────── │  local corpus /   │   Bedrock Knowledge
└──────┬───────┘   tool result  │  OpenSearch, etc. │   Base in production)
       │ research notes         └───────────────────┘
       ▼
┌──────────────┐
│  Summarizer   │  produces draft report
│   (Bedrock)   │
└──────┬────────┘
       │ draft
       ▼
┌──────────────┐   REVISE: <feedback>
│   Critic      │ ───────────────────▶ back to Summarizer (max_revisions rounds)
│   (Bedrock)   │
└──────┬────────┘
       │ APPROVED
       ▼
  final report
```

All three agents are calls to the same `BedrockChatClient`, which wraps the
Bedrock **Converse API** (`bedrock-runtime.converse`) and implements the
tool-use request/response loop generically — call the model, if it asks to run
a tool then run it locally and feed the result back, repeat until it returns
text. Only the Researcher is given tools in this demo; Summarizer and Critic
reason purely over text, which keeps the audit trail simple (every tool call
is visible in `PipelineResult.research_notes`).

## Why this design (and why it's a portfolio piece, not a toy)

- **Swappable retrieval**: `search_documents` in `src/tools.py` is a naive
  local keyword search over `data/*.txt` so the whole demo runs without any
  AWS-side setup beyond model access. In a real engagement this function is
  replaced with a call to a Bedrock Knowledge Base or OpenSearch, and nothing
  else in the pipeline changes.
- **Bounded revision loop**: the Critic can send work back, but `max_revisions`
  guarantees termination — a real cost/latency control most "agent demo" code
  skips.
- **Testable without AWS**: `tests/test_bedrock_client.py` and
  `tests/test_agents.py` mock the Bedrock client entirely, so the control flow
  (tool execution, unknown-tool handling, the revision loop, the round cap) is
  verified by `pytest` with zero AWS credentials or cost. `tests/test_tools.py`
  tests the retrieval function directly.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# AWS credentials with Bedrock model access, e.g.:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
# In the Bedrock console, request access to the model in DEFAULT_MODEL_ID
# (src/bedrock_client.py) for your account/region before running live.
```

## Run

```bash
python -m src.main "What agentic AI patterns work well for production systems?" -v
```

## Test (no AWS required)

```bash
pytest -v
```

## Extending this for a client engagement
- Swap `search_documents` for a Bedrock Knowledge Base retriever call.
- Add a fourth agent (e.g. "Formatter") or branch into parallel researchers
  for multi-source topics.
- Add the guardrail/audit wrapper from the companion project,
  `../02-agent-guardrail-framework`, around every `BedrockChatClient.run()`
  call to get policy checks, PII redaction, and cost tracking for free.
