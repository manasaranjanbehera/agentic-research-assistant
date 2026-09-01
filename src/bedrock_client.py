"""Thin wrapper around the AWS Bedrock Runtime Converse API.

Handles the tool-use request/response loop generically so agent code
doesn't need to know about Bedrock's wire format. Swap `model_id` for
any Converse-API-compatible model available in your account/region.
"""
from __future__ import annotations

import logging
from typing import Any

import boto3

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class BedrockChatClient:
    """Wraps bedrock-runtime `converse` with a tool-calling loop.

    Pass a dict of {tool_name: python_callable} plus matching Bedrock
    tool specs; the client keeps calling the model, executing any
    tool_use requests locally, and feeding results back until the
    model returns a final text answer (or max_tool_rounds is hit).
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        region_name: str | None = None,
        client: Any = None,
    ) -> None:
        self.model_id = model_id
        self._client = client or boto3.client("bedrock-runtime", region_name=region_name)

    def run(
        self,
        system_prompt: str,
        user_message: str,
        tools: dict | None = None,
        tool_specs: list | None = None,
        max_tool_rounds: int = 5,
        temperature: float = 0.3,
    ) -> str:
        messages: list = [{"role": "user", "content": [{"text": user_message}]}]
        tool_config = {"tools": tool_specs} if tool_specs else None

        for round_num in range(max_tool_rounds):
            # Snapshot messages so converse() does not receive a live mutating reference.
            kwargs: dict[str, Any] = {
                "modelId": self.model_id,
                "system": [{"text": system_prompt}],
                "messages": list(messages),
                "inferenceConfig": {"temperature": temperature, "maxTokens": 2048},
            }
            if tool_config:
                kwargs["toolConfig"] = tool_config

            response = self._client.converse(**kwargs)
            output_message = response["output"]["message"]
            messages.append(output_message)
            stop_reason = response.get("stopReason")

            if stop_reason != "tool_use":
                return _extract_text(output_message)

            tool_results = []
            for block in output_message["content"]:
                if "toolUse" not in block:
                    continue
                tool_use = block["toolUse"]
                tool_name = tool_use["name"]
                tool_input = tool_use.get("input", {}) or {}
                logger.info("round %s: model called tool %s(%s)", round_num, tool_name, tool_input)

                if not tools or tool_name not in tools:
                    result_text = f"Error: unknown tool '{tool_name}'"
                else:
                    try:
                        result_text = str(tools[tool_name](**tool_input))
                    except Exception as exc:  # noqa: BLE001 - surface to the model, don't crash the run
                        result_text = f"Error executing {tool_name}: {exc}"

                tool_results.append(
                    {
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"text": result_text}],
                        }
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        raise RuntimeError(f"Exceeded max_tool_rounds={max_tool_rounds} without a final answer")


def _extract_text(message: dict) -> str:
    return "\n".join(block["text"] for block in message["content"] if "text" in block)
