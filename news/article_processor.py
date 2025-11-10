"""Utilities for AI-powered processing of news articles."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from shared_code.ollama_client import OllamaClientError, get_ollama_client


MAX_ARTICLE_CHARS = 6000
RELEVANCE_THRESHOLD = 0.4


class ArticleProcessingError(RuntimeError):
    """Raised when AI-powered processing of an article fails."""


@dataclass(slots=True)
class ArticleProcessingResult:
    """Normalized result produced by Ollama for an article."""

    summary: str
    cleaned_content: str
    symbols: list[str]
    relevance_score: float | None
    is_relevant: bool
    reasoning: str
    elapsed_time: float


def process_article_with_ollama(
    title: str,
    raw_content: str,
    focus_symbols: Sequence[str] | None = None,
) -> ArticleProcessingResult:
    """Process an article with Ollama to produce summary and relevance signals."""
    start_time = time.perf_counter()

    normalized_content = raw_content.strip()
    if not normalized_content:
        message = "Article content is empty; skipping AI processing."
        raise ArticleProcessingError(message)

    truncated_content = normalized_content[:MAX_ARTICLE_CHARS]
    symbols_text = ", ".join(sorted(set(_normalize_symbol_list(focus_symbols))))

    prompt = _build_analysis_prompt(
        title=title,
        content=truncated_content,
        symbols_text=symbols_text,
    )

    client = get_ollama_client()

    try:
        response_text = client.generate_text(prompt, temperature=0.1)
    except OllamaClientError as exc:
        raise ArticleProcessingError(str(exc)) from exc

    payload = _parse_json_response(response_text)
    elapsed_time = time.perf_counter() - start_time

    return _build_processing_result(
        payload, fallback_content=normalized_content, elapsed_time=elapsed_time,
    )


def _build_analysis_prompt(*, title: str, content: str, symbols_text: str) -> str:
    focus_section = (
        f"Focus symbols of interest: [{symbols_text}]\n"
        if symbols_text
        else "No predefined focus symbols supplied.\n"
    )

    return (
        "You are an assistant that prepares cryptocurrency news for trading analysis.\n"
        "Given the article title and body, you must:\n"
        "1. Produce a concise summary with market-impacting facts.\n"
        "2. Rewrite the body into clean Markdown paragraphs and bullet points.\n"
        "3. Identify cryptocurrency tickers discussed (uppercase like BTC, ETH).\n"
        "4. Score relevance between 0 and 1 for today's trading decisions.\n"
        "5. Mark is_relevant true only if the article offers actionable or time-sensitive info.\n"
        "6. Keep reasoning short and describe why the score was chosen.\n"
        "Output JSON with keys: summary, cleaned_content, symbols,\n"
        "relevance_score, is_relevant, reasoning.\n"
        "Do not wrap the JSON in markdown or add commentary.\n"
        f"{focus_section}\n"
        f"Title: {title.strip()}\n"
        "Article Body:\n"
        f"""{content}"""
    )


def _parse_json_response(response_text: str) -> dict[str, object]:
    candidate = response_text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not match:
            message = "Received non-JSON response from Ollama."
            raise ArticleProcessingError(message) from None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            message = "Failed to decode JSON payload from Ollama."
            raise ArticleProcessingError(message) from exc


def _build_processing_result(
    payload: dict[str, object],
    *,
    fallback_content: str,
    elapsed_time: float,
) -> ArticleProcessingResult:
    summary = _coerce_str(payload.get("summary"))
    cleaned_content = _coerce_str(payload.get("cleaned_content")) or fallback_content
    raw_symbols = payload.get("symbols")
    if isinstance(raw_symbols, str):
        symbol_iterable: Iterable[str] | None = [raw_symbols]
    elif isinstance(raw_symbols, Iterable):
        symbol_iterable = raw_symbols
    else:
        symbol_iterable = None
    symbols = _normalize_symbol_list(symbol_iterable)

    relevance_score = payload.get("relevance_score")
    if isinstance(relevance_score, (int, float)):
        relevance_score = max(0.0, min(float(relevance_score), 1.0))
    else:
        relevance_score = None

    is_relevant = payload.get("is_relevant")
    relevant_flag = (
        is_relevant
        if isinstance(is_relevant, bool)
        else (relevance_score or 0.0) >= RELEVANCE_THRESHOLD
    )

    reasoning = _coerce_str(payload.get("reasoning"))

    return ArticleProcessingResult(
        summary=summary,
        cleaned_content=cleaned_content,
        symbols=symbols,
        relevance_score=relevance_score,
        is_relevant=relevant_flag,
        reasoning=reasoning,
        elapsed_time=elapsed_time,
    )


def _normalize_symbol_list(symbols: Iterable[str] | None) -> list[str]:
    if not symbols:
        return []
    normalized = {
        symbol.strip().upper() for symbol in symbols if isinstance(symbol, str) and symbol.strip()
    }
    return sorted(normalized)


def _coerce_str(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "ArticleProcessingError",
    "ArticleProcessingResult",
    "process_article_with_ollama",
]
