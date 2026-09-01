"""Tests the tool-calling loop against a fake bedrock-runtime client so
no real AWS credentials or network access are required."""
import pytest
from src.bedrock_client import BedrockChatClient


class FakeBedrockRuntime:
    """Returns a scripted sequence of `converse` responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _text_response(text):
    return {
        "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
        "stopReason": "end_turn",
    }


def _tool_use_response(tool_use_id, name, tool_input):
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": tool_use_id,
                            "name": name,
                            "input": tool_input,
                        }
                    }
                ],
            }
        },
        "stopReason": "tool_use",
    }


def test_run_returns_text_when_no_tool_use():
    fake = FakeBedrockRuntime([_text_response("hello world")])
    client = BedrockChatClient(client=fake)

    result = client.run(system_prompt="sys", user_message="hi")

    assert result == "hello world"
    assert len(fake.calls) == 1


def test_run_executes_tool_and_feeds_result_back():
    fake = FakeBedrockRuntime(
        [
            _tool_use_response("tu-1", "double", {"n": 21}),
            _text_response("The answer is 42"),
        ]
    )
    client = BedrockChatClient(client=fake)

    result = client.run(
        system_prompt="sys",
        user_message="double 21",
        tools={"double": lambda n: n * 2},
        tool_specs=[{"toolSpec": {"name": "double", "description": "doubles a number"}}],
    )

    assert result == "The answer is 42"
    assert len(fake.calls) == 2
    # second call must include the tool result fed back as a user message
    second_call_messages = fake.calls[1]["messages"]
    tool_result_msg = second_call_messages[-1]
    assert tool_result_msg["role"] == "user"
    assert tool_result_msg["content"][0]["toolResult"]["toolUseId"] == "tu-1"
    assert tool_result_msg["content"][0]["toolResult"]["content"][0]["text"] == "42"


def test_run_reports_unknown_tool_without_crashing():
    fake = FakeBedrockRuntime(
        [
            _tool_use_response("tu-1", "nonexistent_tool", {}),
            _text_response("done"),
        ]
    )
    client = BedrockChatClient(client=fake)

    result = client.run(system_prompt="sys", user_message="hi", tools={}, tool_specs=[])

    assert result == "done"
    fed_back = fake.calls[1]["messages"][-1]["content"][0]["toolResult"]["content"][0]["text"]
    assert "unknown tool" in fed_back


def test_run_raises_after_max_tool_rounds():
    # model keeps calling a tool forever; client must give up rather than loop forever
    responses = [_tool_use_response(f"tu-{i}", "noop", {}) for i in range(10)]
    fake = FakeBedrockRuntime(responses)
    client = BedrockChatClient(client=fake)

    with pytest.raises(RuntimeError, match="max_tool_rounds"):
        client.run(
            system_prompt="sys",
            user_message="hi",
            tools={"noop": lambda: "ok"},
            tool_specs=[{"toolSpec": {"name": "noop"}}],
            max_tool_rounds=3,
        )
