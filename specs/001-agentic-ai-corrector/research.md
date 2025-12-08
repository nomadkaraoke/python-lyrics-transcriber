# Research: Agentic AI Corrector

## Research Findings

### Provider Layer Abstraction (LiteLLM/OpenRouter)

**Decision**: Use LiteLLM or OpenRouter to unify cloud/local models with retries, timeouts, and cost tracking
**Rationale**:
- Unified SDK simplifies switching between Claude, GPT, Gemini, and Ollama
- Built-in retries with backoff, request timeouts, and global rate limiting
- Native cost/latency tracking and provider health visibility
- Reduces custom wrapper complexity and future maintenance

**Alternatives Considered**:
- Custom provider wrappers (rejected: duplicated effort, fewer guardrails)
- Direct vendor SDKs only (rejected: lock-in and fragmented logic)

**Implications**:
- Add provider layer to agent routing; remove redundant custom wrappers where possible
- Centralize model configuration and environment variables

### Structured Outputs with Pydantic/Instructor

**Decision**: Enforce Pydantic schemas for LLM outputs (via Instructor or pydantic-ai)
**Rationale**:
- Eliminates brittle JSON parsing and reduces flaky corrections
- Validates fields (word ids, action type, timing deltas) before application
- Enables deterministic, idempotent correction application

**Schema Contract**:
- `CorrectionProposal`: word_id(s), action, replacement_text, timing_delta_ms, confidence, reason
- Reject/auto-retry on schema invalidation; record failures for observability

**Alternatives Considered**:
- Natural-language outputs (rejected: high variance, harder to test)

### Feedback Store: SQLite/DuckDB

**Decision**: Store AICorrection, HumanFeedback, CorrectionSession, Metrics in SQLite or DuckDB
**Rationale**:
- File-first, simple ops; strong local analytics for 3-year retention
- Better than loose JSON for queries, joins, and cohort analyses
- Keeps JSON export as artifact for portability

**Alternatives Considered**:
- Keep only JSON (rejected: poor analytics, fragile over time)
- Full DBMS (Postgres) (deferred: unnecessary operational burden for now)

### Semi-Agentic Graph (bounded)

**Decision**: Use LangGraph with constrained tools/actions and bounded loops
**Rationale**:
- Predictable latency (<10s), fewer runaway loops, easier debugging
- Keeps audit trail per action; pairs well with structured outputs

**Notes**:
- Cap per-call tokens (~500), timeouts (2–4s), and max passes (2)
- Batch small gaps carefully; concurrency with a modest cap

### LangChain/LangGraph for Agentic AI Workflows

**Decision**: LangGraph for orchestrating multi-step correction workflows with state management
**Rationale**: 
- LangGraph provides stateful, graph-based workflow orchestration ideal for complex correction logic
- Built-in support for conditional routing between different correction strategies
- Native integration with multiple AI providers through LangChain's unified interface
- Excellent observability hooks for tracking correction decisions

**Key Implementation Patterns**:
- **Correction Graph**: Input → Analysis → Strategy Selection → Correction → Validation → Output
- **State Management**: Persistent correction context across multiple AI model calls
- **Conditional Routing**: Route to different models/strategies based on error patterns
- **Human-in-the-loop**: Built-in support for approval/feedback steps

**Alternatives Considered**: 
- Pure LangChain Chains (rejected: insufficient state management for complex workflows)
- Custom orchestration (rejected: reinventing wheel, poor observability)

### LangFuse for Comprehensive Observability

**Decision**: LangFuse as primary observability platform with custom metrics
**Rationale**:
- Native LangChain/LangGraph integration for automatic trace collection
- User-friendly dashboard for non-technical stakeholders to monitor AI performance
- Built-in cost tracking across multiple AI providers
- Excellent support for human feedback integration and RLHF workflows

**Key Observability Metrics**:
- **Correction Accuracy**: Before/after error counts, success rates by error type
- **Model Performance**: Response times, token usage, cost per correction
- **Human Feedback**: Review time, correction patterns, satisfaction scores
- **System Health**: Model availability, fallback activation rates

**Integration Points**:
- Automatic trace collection from LangGraph workflows
- Custom metrics for correction-specific KPIs (70% error reduction tracking)
- Human feedback correlation with AI decisions
- A/B testing framework for model comparison

### Multi-Model AI Strategy

**Decision**: Pluggable multi-provider architecture with intelligent routing
**Rationale**:
- Different models excel at different correction types (factual vs. linguistic errors)
- Cost optimization through intelligent model selection
- Reliability through automatic failover between providers
- Performance comparison for continuous optimization

**Model Integration Approach**:
1. **Primary Models**: Claude 4 Sonnet (reasoning), GPT-5 (language), Gemini 2.5 Pro (multimodal)
2. **Local Models**: Ollama-hosted models for privacy-sensitive processing
3. **Model Chaining (Selective)**: Consensus only for high-uncertainty gaps
4. **Smart Routing**: Rules-based initially (gap type/length/uncertainty); score-based later

**Provider Abstractions**:
- Unified interface through LangChain's provider abstraction
- Consistent retry/fallback logic across all providers
- Rate limiting and cost controls per provider
- Performance monitoring and automatic A/B testing

### Ollama for Local Model Hosting

**Decision**: Ollama for local model deployment with cloud hybrid approach
**Rationale**:
- Privacy control for sensitive lyrics content
- Reduced latency for simple corrections
- Cost control for high-volume usage
- Offline capability as ultimate fallback

**Local Model Strategy**:
- **Primary Local Model**: GPT-OSS or similar for basic corrections
- **Hybrid Routing**: Local first for simple patterns, cloud for complex cases
- **Privacy Mode**: Force local-only processing for sensitive content
- **Development Environment**: Local models for faster testing/iteration

### Human Feedback Integration and Learning

**Decision**: Structured feedback collection with gradual learning integration
**Rationale**:
- Systematic collection of correction reasoning builds comprehensive training dataset
- Gradual transition from rule-based patterns to ML-driven improvement
- Clear feedback taxonomy enables targeted model fine-tuning
- Long-term vision supports advanced RLHF implementation

**Feedback Architecture**:
1. **Immediate Feedback**: Correction acceptance/rejection with reason codes
2. **Detailed Feedback**: Optional detailed explanations for training data
3. **Pattern Recognition**: Automatic categorization of common correction types
4. **Model Adaptation**: Gradual integration of feedback patterns into routing decisions

**Learning Progression**:
- **Phase 1**: Rule-based routing based on feedback patterns
- **Phase 2**: Statistical model for correction strategy selection
- **Phase 3**: Full RLHF implementation with fine-tuned models

### Testing Strategy for AI Systems

**Decision**: Multi-layered testing approach with deterministic validation
**Rationale**:
- AI systems require specialized testing approaches beyond traditional unit tests
- Contract tests ensure model interface stability
- Integration tests validate end-to-end correction workflows
- Performance tests track accuracy improvements over time

**Testing Layers**:
1. **Contract Tests**: AI model interface contracts, response format validation
2. **Integration Tests**: Full correction workflows with mocked models
3. **Performance Tests**: Correction accuracy benchmarks, timing validation
4. **Human Simulation Tests**: Automated feedback simulation for learning validation

**Test Data Strategy**:
- **Golden Dataset**: Curated set of known correction patterns for regression testing
- **Synthetic Data**: Generated error patterns for comprehensive coverage
- **Production Anonymization**: Sanitized real corrections for realistic testing
- **Benchmark Evolution**: Continuously updated test suite based on new error patterns

### Architecture Patterns for Reliability

**Decision**: Circuit breaker pattern with graceful degradation
**Rationale**:
- AI services can be unreliable; circuit breakers prevent cascade failures
- Graceful degradation maintains user functionality during outages
- Multi-layer fallback ensures system always produces usable output

**Reliability Patterns**:
- **Circuit Breakers**: Per-provider failure detection and isolation
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Fallback Hierarchy**: AI Model → Simpler AI → Rule-based → Original transcription
- **Health Monitoring**: Continuous model availability and performance tracking

## Technical Decision Summary

| Technology | Purpose | Implementation Approach |
|------------|---------|------------------------|
| **LangGraph** | Agentic workflow orchestration | Stateful correction pipelines with conditional routing |
| **LangFuse** | Observability and monitoring | Integrated tracing with custom correction metrics |
| **Multi-AI Providers** | Correction processing | Pluggable architecture with smart routing |
| **Ollama** | Local model hosting | Hybrid cloud/local with privacy controls |
| **Structured Feedback** | Continuous learning | Taxonomized feedback collection with gradual ML integration |

## Research Validation

All research findings align with constitutional requirements:
- **TDD**: Clear testing strategy for AI systems
- **Quality**: Comprehensive observability and monitoring
- **UX**: Maintains existing interface patterns
- **Performance**: Multi-model approach optimizes for 70% error reduction goal
- **Observability**: LangFuse provides comprehensive monitoring as required

## Next Steps

Research complete with no unresolved technical dependencies. Proceeding to Phase 1: Design & Contracts.
