"""Tests the Researcher -> Summarizer -> Critic orchestration logic with
a stubbed BedrockChatClient, so the control flow (revision loop,
early-approval short-circuit) is verified without calling AWS."""
from src.agents import ResearchPipeline


class ScriptedClient:
    """Returns canned `.run()` outputs in call order."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def run(self, system_prompt, user_message, tools=None, tool_specs=None, **kwargs):
        self.calls.append({"system_prompt": system_prompt, "user_message": user_message})
        return self._script.pop(0)


def test_pipeline_stops_immediately_on_approval():
    client = ScriptedClient(
        [
            "research notes here",          # researcher
            "draft report v1",              # summarizer
            "APPROVED: draft report v1",    # critic
        ]
    )
    pipeline = ResearchPipeline(client=client)

    result = pipeline.run("agentic AI", max_revisions=3)

    assert result.final_report == "draft report v1"
    assert result.revision_rounds == 1
    assert len(client.calls) == 3


def test_pipeline_revises_until_approved():
    client = ScriptedClient(
        [
            "research notes here",             # researcher
            "draft report v1",                 # summarizer
            "REVISE: add more detail",         # critic round 1
            "draft report v2",                 # summarizer (revision)
            "APPROVED: draft report v2",       # critic round 2
        ]
    )
    pipeline = ResearchPipeline(client=client)

    result = pipeline.run("agentic AI", max_revisions=3)

    assert result.final_report == "draft report v2"
    assert result.revision_rounds == 2


def test_pipeline_respects_max_revisions_cap():
    # critic never approves; pipeline must stop at max_revisions, not loop forever
    client = ScriptedClient(
        [
            "research notes here",   # researcher
            "draft report v1",       # summarizer
            "REVISE: still bad",     # critic round 1
            "draft report v2",       # summarizer
            "REVISE: still bad",     # critic round 2 (== max_revisions, loop ends)
        ]
    )
    pipeline = ResearchPipeline(client=client)

    result = pipeline.run("agentic AI", max_revisions=2)

    assert result.revision_rounds == 2
    assert result.final_report == "draft report v2"
    assert result.critique == "REVISE: still bad"
