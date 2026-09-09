# Multi-Agent Research Assistant (AWS Bedrock)

[![CI](https://github.com/manasaranjanbehera/agentic-research-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/manasaranjanbehera/agentic-research-assistant/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![uv](https://img.shields.io/badge/uv-managed-7c3aed.svg)](https://docs.astral.sh/uv/)

A small, production-shaped multi-agent system: a **Researcher** agent gathers
facts using tool-calling against a knowledge base, a **Summarizer** agent turns
them into a structured report, and a **Critic** agent reviews the report and
sends it back for revision (bounded rounds) before approving a final answer.

This is the "researcher → summarizer → critic" agentic pattern — a lightweight,
automated QA gate that catches unsupported claims before they reach a user,
instead of trusting a single model call to get everything right first try.

## Quick start

```bash
# Install
uv sync

# Run tests (no AWS credentials needed)
uv run pytest -v

# Run live against Bedrock (requires AWS credentials — see Setup below)
uv run python -m src.main "What agentic AI patterns work well for production systems?" -v
```

## Architecture

### Target architecture

![Multi-Agent Research Assistant — target architecture](https://github.com/user-attachments/assets/b164553a-9565-4a07-815c-0b799dea7eb6)

### What this repository implements

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

This repository implements the orchestration layer of the architecture above:
the Researcher, Summarizer and Critic agents on the Bedrock Converse API, tool
calling, and the revision loop bounded by `max_revisions`. Retrieval sits behind
a swappable interface — `search_documents` in `src/tools.py` is keyword search
over `data/*.txt`, replaceable with a Bedrock Knowledge Base or OpenSearch
without changing pipeline logic.

The enterprise retrieval backends (vector store, knowledge graph), line-of-business
source systems and observability shown in the target diagram are integration
points, not included here. Guardrails, policy enforcement and audit are
implemented separately in
[agent-guardrail-framework](https://github.com/manasaranjanbehera/agent-guardrail-framework).


## How it works

Running the pipeline on a topic (`uv run python -m src.main "<topic>"`) executes
four steps, implemented in `src/agents.py` and `src/bedrock_client.py`:

1. **The Researcher agent gathers facts.** The topic is sent to the Researcher
   along with the `search_documents` tool definition (`src/tools.py`).
   `BedrockChatClient.run()` then handles the tool-use loop:
   - The model receives the topic and, per its system prompt, is expected to
     search before answering.
   - If it decides it needs information, it responds with a tool-use request
     instead of text.
   - The client executes the requested tool locally — `search_documents()`
     runs a keyword search over the sample corpus in `data/`.
   - The tool result is added to the conversation and the model is called
     again.
   - This repeats (up to `max_tool_rounds`) until the model returns a final
     text answer: the research notes, citing which document each fact came
     from.

2. **The Summarizer drafts a report.** The research notes are passed to the
   Summarizer agent, which has no tool access. It produces a structured
   report with headings, keeping only claims the notes support.

3. **The Critic reviews the report and can request a revision.** The Critic
   reads the draft and responds either `APPROVED: ...` or
   `REVISE: <specific feedback>`. On a revision request, the Summarizer is
   called again with that feedback and the Critic reviews the new draft. This
   can repeat up to `max_revisions` times (default `2`); if the cap is
   reached before approval, the last drafted report is returned rather than
   looping indefinitely.

4. **The final report is returned.** `PipelineResult` captures the topic, the
   research notes, the first draft, the final critique, the final report, and
   how many revision rounds were used. `main.py` prints the final report and
   the revision count.

## Design notes

- **Swappable retrieval**: `search_documents` in `src/tools.py` is a keyword
  search over `data/*.txt`, so the project runs without any AWS-side setup
  beyond model access. In production this function can be replaced with a
  call to a Bedrock Knowledge Base or OpenSearch, and nothing else in the
  pipeline needs to change.
- **Bounded revision loop**: the Critic can send work back, but
  `max_revisions` guarantees the loop terminates, bounding cost and latency.
- **Testable without AWS**: `tests/test_bedrock_client.py` and
  `tests/test_agents.py` mock the Bedrock client entirely, so the control
  flow (tool execution, unknown-tool handling, the revision loop, the round
  cap) is verified by `pytest` with zero AWS credentials or cost.
  `tests/test_tools.py` tests the retrieval function directly.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and environment manager)
- AWS credentials with Bedrock model access (for live runs only; tests do not need AWS)

## Setup

Install dependencies and create the local virtual environment:

```bash
uv sync
```

For live Bedrock runs, configure AWS credentials. You can export them directly
or copy `.env.example` to `.env` and load it with your shell or a secrets manager:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

In the Bedrock console, request access to the model in `DEFAULT_MODEL_ID`
(`src/bedrock_client.py`) for your account and region before running live.

## Start

Run the research pipeline on a topic:

```bash
uv run python -m src.main "What agentic AI patterns work well for production systems?" -v
```

Or with Make:

```bash
make run TOPIC="What agentic AI patterns work well for production systems?"
```

Optional flags:

- `-v` / `--verbose` — show INFO-level logs from the pipeline
- `--max-revisions N` — cap critic revision rounds (default: `2`)

The command runs the full researcher → summarizer → critic loop, prints the
final report, and exits when finished.

## Stop

This project is a one-shot CLI, not a background service.

- **Normal completion:** the process exits on its own after printing the report.
- **Cancel in progress:** press `Ctrl+C` in the terminal to interrupt a run.

No separate shutdown step is required.

## Test and lint (no AWS required)

```bash
make lint test
```

Or individually:

```bash
uv run ruff check src tests
uv run pytest -v
```

CI runs the same checks on every push and pull request to `main`.

## Project layout

```
.
├── .github/
│   ├── workflows/ci.yml       # GitHub Actions: Ruff + pytest (Python 3.10–3.12)
│   ├── dependabot.yml         # Monthly GitHub Actions updates
│   ├── ISSUE_TEMPLATE/        # Bug report and feature request forms
│   └── pull_request_template.md
├── data/                      # Sample corpus for local document search
├── src/
│   ├── __init__.py
│   ├── agents.py              # Researcher → Summarizer → Critic pipeline
│   ├── bedrock_client.py      # Bedrock Converse API + tool-use loop
│   ├── main.py                # CLI entry point
│   └── tools.py               # search_documents tool (swap for KB in prod)
├── tests/                     # Mocked Bedrock tests (no AWS credentials)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── Makefile                   # install, lint, test, run shortcuts
├── pyproject.toml             # Dependencies, Ruff, and pytest config
├── SECURITY.md
└── uv.lock                    # Locked dependency versions for reproducible installs
```

## Possible extensions

- Swap `search_documents` for a Bedrock Knowledge Base retriever call.
- Add a fourth agent (e.g. a "Formatter") or branch into parallel researchers
  for topics that span multiple sources.
- Wrap each `BedrockChatClient.run()` call with the guardrail layer from the
  companion project, [agent-guardrail-framework](https://github.com/manasaranjanbehera/agent-guardrail-framework),
to add policy checks, PII redaction, and cost tracking without changing
this project's logic.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Pull requests welcome; CI must pass before merge.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
