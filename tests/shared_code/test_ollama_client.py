"""Unit tests for the Ollama client wrapper utilities."""

from __future__ import annotations

import types
from typing import Any, cast

import pytest

from infra.configuration import OllamaSettings
from shared_code import ollama_client as oc


@pytest.fixture
def patched_settings(monkeypatch: pytest.MonkeyPatch) -> OllamaSettings:
    """Provide predictable Ollama settings for tests."""
    settings = OllamaSettings(
        host="http://test-host:11434",
        model="test-model",
        timeout=12.5,
    )
    monkeypatch.setattr(oc, "get_ollama_settings", lambda: settings)
    return settings


def test_build_summary_prompt_includes_title_and_content() -> None:
    """Ensure the summary prompt embeds title, content, and word limit."""
    prompt = oc._build_summary_prompt(
        title="  Breaking News ",
        content="  Significant market move. ",
        max_words=155,
    )

    assert "Title: Breaking News" in prompt
    assert "Significant market move." in prompt
    assert "155 words" in prompt


@pytest.mark.parametrize(
    "response,expected",
    (
        ({"response": "  Hello  "}, "Hello"),
        ({"message": {"content": "  Alt text  "}}, "Alt text"),
        ({"response": "", "message": {"content": "  Trimmed  "}}, "Trimmed"),
        ({"response": None, "message": {}}, ""),
    ),
)
def test_extract_response_text_variants(response: dict[str, object], expected: str) -> None:
    """Validate response text extraction across supported payload shapes."""
    assert oc._extract_response_text(response) == expected


def test_resolve_settings_uses_overrides(patched_settings: OllamaSettings) -> None:
    """Overrides should replace defaults selectively."""
    overrides = oc._resolve_settings(host="http://override", model=None, timeout=7.0)

    assert overrides.host == "http://override"
    assert overrides.model == patched_settings.model
    assert overrides.timeout == 7.0


def test_ollama_client_generate_text_success(
    monkeypatch: pytest.MonkeyPatch,
    patched_settings: OllamaSettings,
) -> None:
    """Client should submit the prompt and return trimmed text."""
    calls: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, host: str) -> None:
            calls["host"] = host

        def generate(self, **kwargs):
            calls["generate_kwargs"] = kwargs
            return {"response": "  Completed response  "}

    dummy_module = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(oc, "_load_ollama", lambda: dummy_module)

    client = oc.OllamaClient()
    result = client.generate_text("Prompt text", temperature=0.55)

    assert result == "Completed response"
    assert calls["host"] == patched_settings.host

    generate_kwargs = cast(dict[str, Any], calls["generate_kwargs"])
    assert generate_kwargs["model"] == patched_settings.model
    assert generate_kwargs["prompt"] == "Prompt text"
    assert generate_kwargs["options"] == {"temperature": 0.55}
    assert "timeout" not in generate_kwargs


def test_ollama_client_generate_text_raises_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    patched_settings: OllamaSettings,
) -> None:
    """Runtime errors from the SDK should surface as OllamaClientError."""
    _ = patched_settings

    class DummyClient:
        def __init__(self, host: str) -> None:  # pragma: no cover - simple init
            self.host = host

        def generate(self, **_kwargs):  # pragma: no cover - runtime behavior tested
            message = "boom"
            raise RuntimeError(message)

    dummy_module = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(oc, "_load_ollama", lambda: dummy_module)

    client = oc.OllamaClient()

    with pytest.raises(oc.OllamaClientError) as err:
        client.generate_text("Prompt text")

    assert "boom" in str(err.value)


def test_ollama_client_generate_text_raises_on_empty_response(
    monkeypatch: pytest.MonkeyPatch,
    patched_settings: OllamaSettings,
) -> None:
    """An empty payload should raise a descriptive error."""
    _ = patched_settings

    class DummyClient:
        def __init__(self, host: str) -> None:
            self.host = host

        def generate(self, **_kwargs):
            return {"response": "  "}

    dummy_module = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(oc, "_load_ollama", lambda: dummy_module)

    client = oc.OllamaClient()

    with pytest.raises(oc.OllamaClientError) as err:
        client.generate_text("Prompt text")

    assert "empty response" in str(err.value)


def test_summarize_article_builds_prompt(
    monkeypatch: pytest.MonkeyPatch,
    patched_settings: OllamaSettings,
) -> None:
    """Summaries should pass structured prompts through generate_text."""
    _ = patched_settings

    class DummyClient:
        def __init__(self, host: str) -> None:
            self.host = host

        def generate(self, **_kwargs):
            return {"response": "unused"}

    dummy_module = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(oc, "_load_ollama", lambda: dummy_module)

    client = oc.OllamaClient()
    captured: dict[str, Any] = {}
    client.generate_text = lambda prompt, temperature: captured.update(  # type: ignore[method-assign]
        {"prompt": prompt, "temperature": temperature, "result": "summary"},
    ) or "summary"

    result = client.summarize_article(
        title="  Flash Crash ",
        raw_content="  BTC broke support. ",
        max_words=210,
        temperature=0.33,
    )

    assert result == "summary"
    assert captured["temperature"] == 0.33
    prompt_text = cast(str, captured["prompt"])
    assert "Flash Crash" in prompt_text
    assert "BTC broke support." in prompt_text
    assert "210 words" in prompt_text

