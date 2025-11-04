---
goal: Implement AI-powered article summarization and filtering for crypto news analysis
version: 1.0
date_created: 2025-11-04
last_updated: 2025-11-04
owner: graniluk
status: Planned
tags: feature, ai, summarization, crypto
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan outlines the implementation of a new feature to improve article summarization and AI analysis by using Ollama API to preprocess articles before sending them to the main Gemini daily analysis. This will reduce token usage, improve symbol assignment, and ensure only relevant articles are analyzed.

## 1. Requirements & Constraints

- **REQ-001**: Integrate Ollama API for article summarization and formatting improvement
- **REQ-002**: Assign crypto symbols properly to articles based on content analysis
- **REQ-003**: Determine article relevance for today's crypto analysis using AI
- **REQ-004**: Filter out irrelevant articles before sending to main Gemini analysis
- **REQ-005**: Cache summarized articles to avoid re-processing and improve performance
- **CON-001**: Must maintain compatibility with existing RSS fetching pipeline
- **CON-002**: Must not break existing daily report generation process
- **GUD-001**: Use efficient prompting to minimize Ollama API costs and response times
- **PAT-001**: Follow existing code patterns for AI integrations in the codebase

## 2. Implementation Steps

### Implementation Phase 1: Ollama Integration Setup

- GOAL-001: Set up Ollama API client and basic article summarization functionality

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Install and configure Ollama Python client library in requirements.txt |  |  |
| TASK-002 | Create Ollama API client wrapper in shared_code/ollama_client.py |  |  |
| TASK-003 | Implement basic article summarization function with test prompts |  |  |
| TASK-004 | Add configuration for Ollama endpoint and model selection in infra/configuration.py |  |  |

### Implementation Phase 2: Article Processing Enhancement

- GOAL-002: Modify article processing pipeline to include AI summarization, symbol assignment, and relevance filtering

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Update news_agent.py to integrate Ollama summarization after RSS fetching |  |  |
| TASK-006 | Implement symbol detection and assignment using Ollama analysis |  |  |
| TASK-007 | Add relevance scoring for daily crypto analysis using Ollama |  |  |
| TASK-008 | Create article filtering logic to exclude irrelevant articles |  |  |
| TASK-009 | Update article data structure to include summary, symbols, and relevance score |  |  |
| TASK-010 | Extend CachedArticle class and caching logic to store summarized articles |  |  |

### Implementation Phase 3: Daily Report Integration

- GOAL-003: Update daily report generation to use filtered and summarized articles

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-011 | Modify daily_report.py to accept pre-filtered articles instead of raw RSS data |  |  |
| TASK-012 | Update Gemini analysis prompts to work with summarized articles |  |  |
| TASK-013 | Add logging for article filtering statistics and token usage |  |  |

## 3. Alternatives

- **ALT-001**: Perform all analysis (summarization, symbol assignment, relevance) in a single Ollama API call instead of separate steps - rejected due to potential complexity and cost
- **ALT-002**: Use existing symbol_detector.py for symbol assignment instead of AI - rejected due to poor current performance mentioned by user
- **ALT-003**: Implement caching for summarized articles to avoid re-processing - implemented using existing article_cache.py infrastructure

## 4. Dependencies

- **DEP-001**: Ollama API service running locally or accessible endpoint
- **DEP-002**: Python Ollama client library (ollama package)
- **DEP-003**: Sufficient computational resources for Ollama model inference
- **DEP-004**: Existing RSS parsing and news fetching infrastructure

## 5. Files

- **FILE-001**: requirements.txt - Add Ollama client dependency
- **FILE-002**: shared_code/ollama_client.py - New Ollama API wrapper
- **FILE-003**: infra/configuration.py - Add Ollama configuration
- **FILE-004**: news/news_agent.py - Integrate article processing with Ollama
- **FILE-005**: reports/daily_report.py - Update to use filtered articles
- **FILE-006**: news/article_cache.py - Extend CachedArticle class and update caching logic for summarized articles

## 6. Testing

- **TEST-001**: Unit tests for Ollama client wrapper functions
- **TEST-002**: Integration tests for article summarization pipeline
- **TEST-003**: Tests for symbol assignment accuracy with sample articles
- **TEST-004**: Tests for relevance filtering with various article types
- **TEST-005**: Tests for caching of summarized articles to avoid re-processing
- **TEST-006**: End-to-end test for daily report generation with filtered articles

## 7. Risks & Assumptions

- **RISK-001**: Ollama API performance may impact daily report generation time
- **RISK-002**: Accuracy of AI-based symbol assignment and relevance scoring
- **RISK-003**: Additional computational costs for running Ollama locally
- **ASSUMPTION-001**: Ollama service will be available and properly configured
- **ASSUMPTION-002**: Existing RSS feeds continue to provide articles in expected format

## 8. Related Specifications / Further Reading

- [Ollama API Documentation](https://github.com/ollama/ollama)
- Existing news processing code in news/news_agent.py
- Current daily report implementation in reports/daily_report.py