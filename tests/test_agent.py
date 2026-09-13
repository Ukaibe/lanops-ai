from types import SimpleNamespace

from lanops_ai.agent import _content_text, _invoke_with_failover


def test_content_text_extracts_gemini_text_blocks():
    content = [
        {
            "type": "text",
            "text": '{"type":"answer","answer":"Check reachability."}',
            "extras": {"signature": "ignored"},
        }
    ]

    assert _content_text(content) == (
        '{"type":"answer","answer":"Check reachability."}'
    )


async def test_invoke_with_failover_uses_ollama_after_gemini_error():
    class _Model:
        def __init__(self, result=None, error=None):
            self.result = result
            self.error = error
            self.calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.error is not None:
                raise self.error
            return self.result

    primary = _Model(error=RuntimeError("Gemini unavailable"))
    expected = SimpleNamespace(content="local answer")
    failover = _Model(result=expected)

    result = await _invoke_with_failover(primary, failover, [])

    assert result is expected
    assert primary.calls == 1
    assert failover.calls == 1
