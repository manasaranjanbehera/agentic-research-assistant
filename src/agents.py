"""Three-stage agentic pipeline: Researcher -> Summarizer -> Critic.

Each stage is a separate Bedrock Converse call with its own system
prompt. The Researcher is the only stage with tool access (it calls
`search_documents`); Summarizer and Critic reason purely over text,
which keeps the tool-use loop simple to audit. The Critic can send the
draft back for revision (bounded by max_revisions) before returning a
final report -- a lightweight, automated QA gate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .bedrock_client import BedrockChatClient
from .tools import TOOL_SPECS, TOOLS

logger = logging.getLogger(__name__)

RESEARCHER_PROMPT = (
    "You are a research agent. Use the search_documents tool to gather facts "
    "relevant to the user's topic before answering. Cite which document each "
    "fact came from. Do not fabricate facts not found in the search results."
)

SUMMARIZER_PROMPT = (
    "You are a summarization agent. Turn the research notes you receive into "
    "a tight, well-structured report with headings. Keep only claims that are "
    "supported by the notes."
)

CRITIC_PROMPT = (
    "You are a critic agent reviewing a report for accuracy and clarity. "
    "If the report cites unsupported claims, is vague, or is poorly organized, "
    "respond starting with 'REVISE:' followed by specific fixes. If it is solid, "
    "respond starting with 'APPROVED:' followed by the final report unchanged."
)


@dataclass
class PipelineResult:
    topic: str
    research_notes: str
    draft_report: str
    critique: str
    final_report: str
    revision_rounds: int


class ResearchPipeline:
    def __init__(self, client: Optional[BedrockChatClient] = None) -> None:
        self.client = client or BedrockChatClient()

    def run(self, topic: str, max_revisions: int = 2) -> PipelineResult:
        research_notes = self.client.run(
            system_prompt=RESEARCHER_PROMPT,
            user_message=f"Research topic: {topic}",
            tools=TOOLS,
            tool_specs=TOOL_SPECS,
        )
        logger.info("research notes gathered (%d chars)", len(research_notes))

        report = self.client.run(
            system_prompt=SUMMARIZER_PROMPT,
            user_message=f"Topic: {topic}\n\nResearch notes:\n{research_notes}",
        )
        draft_report = report

        critique = ""
        rounds = 0
        for rounds in range(1, max_revisions + 1):
            critique = self.client.run(
                system_prompt=CRITIC_PROMPT,
                user_message=f"Topic: {topic}\n\nReport:\n{report}",
            )
            if critique.strip().upper().startswith("APPROVED"):
                break
            if rounds == max_revisions:
                # Hit the revision cap: ship the last drafted report rather than
                # spending another summarizer call the critic won't get to review.
                break
            report = self.client.run(
                system_prompt=SUMMARIZER_PROMPT,
                user_message=(
                    f"Topic: {topic}\n\nResearch notes:\n{research_notes}\n\n"
                    f"Revise the report to address this critique:\n{critique}"
                ),
            )

        return PipelineResult(
            topic=topic,
            research_notes=research_notes,
            draft_report=draft_report,
            critique=critique,
            final_report=report,
            revision_rounds=rounds,
        )
