# ADR-004: Groq Model Selection & Deprecation Safeguards

## Status
Accepted

## Context
ArogyaRakshak uses the Groq API for high-speed LLM inference across multi-agent chains (BillNyay 5-agent pipeline, BimaNyay dispute auditor, SchemeSetu reasoning). Early hackathon code relied on `llama3-70b` and `llama-3.3-70b-versatile`.

## Problem
On June 17, 2026, Groq officially deprecated the Llama 3 70B and 8B model endpoints. Hardcoded references to these deprecated models caused API failures and system downtime.

## Decision
1. **Strict Deprecation Ban**: Never invoke `llama3-70b` or `llama-3.3-70b-versatile` anywhere in the codebase.
2. **Environment Variable Configuration**: All LLM calls must read the target model dynamically from the `GROQ_MODEL` environment variable.
3. **Default Model**: The default model is pinned to `openai/gpt-oss-120b` (with `qwen/qwen3.6-27b` as verified alternative).

## Consequences
### Positive
- Resilience to provider-side model lifecycle shifts; switching models requires only an environment variable update.
- Improved multi-agent reasoning performance on complex medical and legal texts.
### Negative
- Prompts must remain model-agnostic and avoid vendor-specific token formatting quirks.
