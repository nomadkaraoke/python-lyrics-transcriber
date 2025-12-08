## Technical Guidance: Agentic AI Corrector

### Summary of Recommendations
- Orchestration: Use LangGraph for a constrained, semi-agentic workflow (bounded loops, explicit tools/actions).
- Provider Abstraction: Use LiteLLM or OpenRouter SDK to unify model access, retries, timeouts, and cost tracking.
- Observability: Keep Langfuse; add custom metrics and OpenTelemetry logs if needed.
- Structured Outputs: Enforce Pydantic schemas (via Instructor or pydantic-ai) for CorrectionProposal[].
- Local Models: Keep Ollama for privacy/offline; add vLLM later only if you need throughput.
- Feedback Storage: Use SQLite or DuckDB for 3-year retention and analytics (supersedes loose JSON as the source of truth; still export JSON as artifacts).
- Evaluation/Testing: jiwer for WER/CER, promptfoo for prompt regression; optional DeepEval/TruLens.

### Architecture Pattern: Semi-Agentic Correction
Use a fixed-stage graph with narrow actions rather than free-form agents:
1) AnalyzeGap → 2) ChooseAction → 3) ExecuteAction (ReplaceWord, SplitWord, DeleteWord, AdjustTiming) → 4) Validate → 5) Record.
Bounded by: max 2 passes, per-call token cap, and total time budget (<10s/song).

### Provider Layer
- Adopt LiteLLM or OpenRouter to access Claude, GPT, Gemini, and Ollama with a unified API.
- Configure retries (exponential backoff + jitter), timeouts (2–4s), circuit breakers per provider.
- Track cost/latency per request; tag with song hash and model.

### Structured Output Contract
- Define a Pydantic model: CorrectionProposal with fields: word_id(s), action, replacement_text, timing_delta_ms, confidence, reason.
- All LLM calls must return JSON matching this schema; invalid JSON → auto-retry once with formatting hint.
- Apply corrections idempotently and deterministically.

### Routing Strategy
- Start rules-based routing by gap type/length/uncertainty.
- Use consensus only for high-uncertainty gaps; otherwise single best model for latency.
- Local-first (Ollama) for simple gaps when privacy mode is enabled; otherwise cloud-first.

### Observability & Metrics
- Emit Langfuse traces per graph node with metrics:
  - acceptance_rate, gap_fix_rate, error_reduction, latency_ms, tokens, cost_usd
- Add tags: model, tool, song_hash, genre.
- Ship minimal OpenTelemetry logs for infra parity if needed.

### Data & Feedback Store
- SQLite or DuckDB tables for: AICorrection, HumanFeedback, CorrectionSession, ObservabilityMetrics.
- Keep JSON exports as artifacts, but treat DB as source of truth.
- Enforce retention policy (3 years) via periodic cleanup.

### Performance Practices
- Operate on gaps, not full transcripts; cap token windows (~500 tokens per call).
- Concurrency with a small cap; respect provider rate limits.
- Strict timeouts; fast fallback to rule-based handlers.

### Testing & Evaluation
- Contract tests: OpenAPI endpoints.
- Integration tests: golden songs, assert WER/CER via jiwer, acceptance_rate thresholds.
- Prompt evals: promptfoo scenarios; commit YAML alongside prompts.
- Unit tests: tool actions, router policy, JSON schemas, timing slice math.

### Model Choices (pragmatic baseline)
- Default: Claude 4 Sonnet; Alternates: GPT‑5; Gemini 2.5 Pro if multimodal needed.
- Local: DeepSeek R1 7B or Qwen2.5 7B via Ollama.

### Rollout Phases
1) Single-model, structured outputs, SQLite store, Langfuse metrics.
2) Add routing and limited consensus for uncertain gaps.
3) Add promptfoo evals and nightly regressions on golden set.
4) Consider vLLM for throughput if needed.
