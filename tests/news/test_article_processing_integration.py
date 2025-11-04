"""Integration tests for AI-powered article processing pipeline."""

from __future__ import annotations

import json
from typing import Any

import pytest

from news import article_processor as ap
from news import rss_parser as rp
from news.article_processor import ArticleProcessingError, ArticleProcessingResult


class DummyOllamaClient:
    """Simple stand-in for the Ollama SDK client."""

    def __init__(self, response_text: str | None = None, *, should_fail: bool = False) -> None:
        """Initialize the dummy client with a canned response or failure mode."""
        self._response_text = response_text or "{}"
        self._should_fail = should_fail
        self.captured_prompt: str | None = None
        self.captured_temperature: float | None = None

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Return the canned response, optionally raising to simulate errors."""
        if self._should_fail:
            message = "simulated failure"
            raise ap.OllamaClientError(message)
        self.captured_prompt = prompt
        self.captured_temperature = temperature
        return self._response_text


@pytest.fixture
def dummy_client(monkeypatch: pytest.MonkeyPatch) -> DummyOllamaClient:
    """Patch the Ollama client factory to return a dummy implementation."""
    client = DummyOllamaClient(
        response_text=json.dumps(
            {
                "summary": "BTC rallies on ETF flows",
                "cleaned_content": "Clean paragraph",
                "symbols": ["btc", "eth"],
                "relevance_score": 1.4,
                "is_relevant": True,
                "reasoning": "High-volume breakout",
            },
        ),
    )

    monkeypatch.setattr(ap, "get_ollama_client", lambda: client)
    return client


def test_process_article_with_ollama_integration_success(
    dummy_client: DummyOllamaClient,
) -> None:
    """Ensure the full processing pipeline normalizes AI output."""
    raw_content = "Market update." * 40
    result = ap.process_article_with_ollama(
        title="Morning Brief",
        raw_content=raw_content,
        focus_symbols=("eth", "btc"),
    )

    assert result.summary == "BTC rallies on ETF flows"
    assert result.cleaned_content == "Clean paragraph"
    assert result.symbols == ["BTC", "ETH"]
    assert result.relevance_score == 1.0
    assert result.is_relevant is True
    assert result.reasoning == "High-volume breakout"

    assert dummy_client.captured_temperature == 0.1
    assert dummy_client.captured_prompt is not None
    prompt_text = dummy_client.captured_prompt
    assert "Title: Morning Brief" in prompt_text
    assert "Focus symbols of interest: [BTC, ETH]" in prompt_text


def test_process_article_with_ollama_handles_marked_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip markdown wrappers and fall back to original content when needed."""
    wrapped_payload = '```json\n{"summary": "Wrapped", "symbols": []}\n```'
    client = DummyOllamaClient(response_text=wrapped_payload)
    monkeypatch.setattr(ap, "get_ollama_client", lambda: client)

    raw_content = "Clean body with detail."
    result = ap.process_article_with_ollama(
        title="Coverage",
        raw_content=raw_content,
        focus_symbols=None,
    )

    assert result.summary == "Wrapped"
    assert result.cleaned_content == raw_content.strip()
    assert result.symbols == []
    assert result.relevance_score is None
    assert result.is_relevant is False


def test_process_article_with_ollama_raises_wrapped_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Surface client failures as ArticleProcessingError for callers."""
    failing_client = DummyOllamaClient(should_fail=True)
    monkeypatch.setattr(ap, "get_ollama_client", lambda: failing_client)

    with pytest.raises(ArticleProcessingError) as err:
        ap.process_article_with_ollama(
            title="Failure Case",
            raw_content="content",
        )

    assert "simulated failure" in str(err.value)


def test_enrich_article_with_ai_uses_ai_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify enrichment path merges AI output with detected symbols."""
    analysis = ArticleProcessingResult(
        summary="Summary",
        cleaned_content="Cleaned",
        symbols=["btc"],
        relevance_score=0.7,
        is_relevant=True,
        reasoning="Looks actionable",
    )

    monkeypatch.setattr(rp, "process_article_with_ollama", lambda *_args, **_kwargs: analysis)

    enrichment = rp._enrich_article_with_ai(
        title="Title",
        full_content="Body",
        focus_symbols=["btc"],
        detected_symbols=["ETH"],
        article_link="https://example.com/article",
    )

    assert enrichment.summary == "Summary"
    assert enrichment.cleaned_content == "Cleaned"
    assert [symbol.upper() for symbol in enrichment.symbols] == ["BTC"]
    assert enrichment.relevance_score == 0.7
    assert enrichment.is_relevant is True
    assert enrichment.notes == "Looks actionable"


def test_enrich_article_with_ai_falls_back_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """If AI processing fails, the pipeline should still flag relevance."""
    def raise_error(*_args: Any, **_kwargs: Any) -> ArticleProcessingResult:
        message = "timeout"
        raise ArticleProcessingError(message)

    monkeypatch.setattr(rp, "process_article_with_ollama", raise_error)

    enrichment = rp._enrich_article_with_ai(
        title="Title",
        full_content="Body",
        focus_symbols=None,
        detected_symbols=["SOL"],
        article_link="https://example.com/article",
    )

    assert enrichment.summary == ""
    assert enrichment.cleaned_content == "Body"
    assert enrichment.symbols == ["SOL"]
    assert enrichment.relevance_score is None
    assert enrichment.is_relevant is True
    assert "timeout" in enrichment.notes
