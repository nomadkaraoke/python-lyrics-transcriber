# Tasks: Agentic AI Corrector

**Input**: Design documents from `/Users/andrew/Projects/karaoke-gen/lyrics_transcriber_local/specs/001-agentic-ai-corrector/`
**Prerequisites**: plan.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓), quickstart.md (✓)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ Tech stack: Python 3.10-3.13, LangChain/LangGraph, LangFuse, FastAPI
   → ✓ Structure: Single Python project with agentic AI submodule
2. Load optional design documents:
   → ✓ data-model.md: 5 entities (AICorrection, HumanFeedback, CorrectionSession, LearningData, ObservabilityMetrics)
   → ✓ contracts/: agentic_correction_api.yaml with 6 endpoints
   → ✓ research.md: LangGraph workflows, multi-model strategy, LangFuse observability
   → ✓ quickstart.md: 5 integration test scenarios
3. Generate tasks by category: Setup → Tests → Core → Integration → Polish
4. Apply task rules: TDD enforced, [P] for parallel execution
5. Total tasks generated: 77 tasks across 8 phases
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Based on plan.md structure: Single Python project with agentic AI integration
- `lyrics_transcriber/correction/agentic/` - New agentic AI correction system
- `tests/contract/` - API contract tests
- `tests/integration/` - End-to-end integration tests

## Phase 3.1: Setup & Dependencies
- [X] T001 Install agentic AI dependencies in pyproject.toml (langchain, langgraph, langfuse, ollama)
- [X] T002 Create agentic correction module structure in lyrics_transcriber/correction/agentic/
- [X] T003 [P] Configure LangFuse observability environment variables and initialization
- [X] T004 [P] Configure Ollama local model server setup and health checks
- [ ] T005 [P] Configure multi-provider AI model authentication (OpenAI, Anthropic, Google)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests [P]
- [X] T006 [P] Contract test POST /api/v1/correction/agentic in tests/contract/test_agentic_correction_api.py
- [X] T007 [P] Contract test GET /api/v1/correction/session/{id} in tests/contract/test_agentic_correction_api.py
- [X] T008 [P] Contract test POST /api/v1/feedback in tests/contract/test_agentic_correction_api.py
- [X] T009 [P] Contract test GET /api/v1/models in tests/contract/test_agentic_correction_api.py
- [X] T010 [P] Contract test PUT /api/v1/models in tests/contract/test_agentic_correction_api.py
- [X] T011 [P] Contract test GET /api/v1/metrics in tests/contract/test_agentic_correction_api.py

### Integration Tests [P]
- [X] T012 [P] Integration test Scenario 1: Basic AI correction workflow in tests/integration/test_basic_ai_workflow.py
- [X] T013 [P] Integration test Scenario 2: Human feedback loop in tests/integration/test_human_feedback_loop.py
- [X] T014 [P] Integration test Scenario 3: Multi-model comparison in tests/integration/test_multi_model_comparison.py
- [X] T015 [P] Integration test Scenario 4: Fallback reliability in tests/integration/test_fallback_reliability.py
- [X] T016 [P] Integration test Scenario 5: Performance observability in tests/integration/test_performance_observability.py

## Phase 3.3: Core Data Models (ONLY after tests are failing)

### Entity Models [P]
- [ ] T017 [P] AICorrection model class in lyrics_transcriber/correction/agentic/models/ai_correction.py
- [ ] T018 [P] HumanFeedback model class in lyrics_transcriber/correction/agentic/models/human_feedback.py
- [ ] T019 [P] CorrectionSession model class in lyrics_transcriber/correction/agentic/models/correction_session.py
- [ ] T020 [P] LearningData model class in lyrics_transcriber/correction/agentic/models/learning_data.py
- [ ] T021 [P] ObservabilityMetrics model class in lyrics_transcriber/correction/agentic/models/observability_metrics.py

### Enumerations and Types [P]
- [ ] T022 [P] CorrectionType, ReviewerAction, FeedbackCategory enums in lyrics_transcriber/correction/agentic/models/enums.py
- [ ] T023 [P] Model validation and serialization utilities in lyrics_transcriber/correction/agentic/models/utils.py

## Phase 3.4: Agentic AI Core Implementation

### AI Model Interfaces
- [X] T024 [P] Base AI provider interface in lyrics_transcriber/correction/agentic/providers/base.py
- [ ] T025 [P] OpenAI provider implementation in lyrics_transcriber/correction/agentic/providers/openai.py
- [ ] T026 [P] Anthropic provider implementation in lyrics_transcriber/correction/agentic/providers/anthropic.py
- [ ] T027 [P] Google provider implementation in lyrics_transcriber/correction/agentic/providers/google.py
- [ ] T028 [P] Ollama provider implementation in lyrics_transcriber/correction/agentic/providers/ollama.py

### Provider Abstraction Layer
- [X] T065 Integrate LiteLLM or OpenRouter SDK for unified provider layer in lyrics_transcriber/correction/agentic/providers/bridge.py
- [ ] T066 [P] Configure retries, timeouts, and circuit breakers with provider-wide settings

### LangGraph Workflows
- [ ] T029 Core correction workflow graph in lyrics_transcriber/correction/agentic/workflows/correction_graph.py
- [ ] T030 Multi-model consensus workflow in lyrics_transcriber/correction/agentic/workflows/consensus_workflow.py
- [ ] T031 Human feedback processing workflow in lyrics_transcriber/correction/agentic/workflows/feedback_workflow.py

### Structured Output Enforcement
- [X] T067 [P] Define Pydantic schemas (CorrectionProposal) in lyrics_transcriber/correction/agentic/models/schemas.py
- [ ] T068 [P] Integrate Instructor/pydantic-ai to enforce JSON outputs in workflows

### Agent Implementation
- [X] T032 Main agentic corrector class in lyrics_transcriber/correction/agentic/agent.py
- [X] T033 Model routing and selection logic in lyrics_transcriber/correction/agentic/router.py

### Feedback Store
- [ ] T069 Introduce SQLite or DuckDB store in lyrics_transcriber/correction/agentic/feedback/store.py
- [ ] T070 [P] Migrate HumanFeedback writes from JSON to DB, keep JSON exports
- [ ] T071 [P] Implement 3-year retention cleanup job

## Phase 3.5: API Implementation & Integration

### FastAPI Endpoints
- [X] T034 POST /correction/agentic endpoint implementation in lyrics_transcriber/review/server.py
- [X] T035 GET /correction/session/{id} endpoint implementation in lyrics_transcriber/review/server.py
- [X] T036 POST /feedback endpoint implementation in lyrics_transcriber/review/server.py
- [X] T037 GET /models and PUT /models endpoint implementation in lyrics_transcriber/review/server.py
- [X] T038 GET /metrics endpoint implementation in lyrics_transcriber/review/server.py

### System Integration
- [ ] T039 Integration with existing corrector.py (routing to agentic vs rule-based)
- [ ] T040 Fallback mechanism implementation when AI services unavailable
- [X] T041 Existing review server API extension in lyrics_transcriber/review/server.py

## Phase 3.6: Observability & Feedback

### LangFuse Integration
- [ ] T042 [P] LangFuse tracing setup in lyrics_transcriber/correction/agentic/observability/langfuse_integration.py
- [ ] T043 [P] Custom metrics collection in lyrics_transcriber/correction/agentic/observability/metrics.py
- [ ] T044 [P] Performance monitoring in lyrics_transcriber/correction/agentic/observability/performance.py
- [ ] T072 [P] Add custom metrics: acceptance_rate, gap_fix_rate, error_reduction, tokens, latency, cost

### Human Feedback Processing
- [ ] T045 Feedback collection and storage in lyrics_transcriber/correction/agentic/feedback/collector.py
- [ ] T046 Learning data aggregation in lyrics_transcriber/correction/agentic/feedback/aggregator.py
- [ ] T047 3-year retention policy implementation in lyrics_transcriber/correction/agentic/feedback/retention.py

## Phase 3.7: Frontend Enhancement

### Review UI Extensions
- [ ] T048 AI feedback UI components in lyrics_transcriber/frontend/src/components/AIFeedbackModal.tsx
- [ ] T049 Model selection interface in lyrics_transcriber/frontend/src/components/ModelSelector.tsx
- [ ] T050 Performance metrics dashboard in lyrics_transcriber/frontend/src/components/MetricsDashboard.tsx

## Phase 3.8: Polish & Validation

### Unit Tests [P]
- [ ] T051 [P] Unit tests for AI provider interfaces in tests/unit/correction/agentic/test_providers.py
- [ ] T052 [P] Unit tests for model classes in tests/unit/correction/agentic/test_models.py
- [ ] T053 [P] Unit tests for workflows in tests/unit/correction/agentic/test_workflows.py
- [ ] T054 [P] Unit tests for observability in tests/unit/correction/agentic/test_observability.py

### Performance Validation
- [ ] T055 Performance benchmark tests (70% error reduction target) in tests/performance/test_accuracy_benchmarks.py
- [ ] T056 Processing time validation (<10 seconds per song) in tests/performance/test_timing_benchmarks.py
- [ ] T073 [P] WER/CER evaluation using jiwer across golden dataset in tests/performance/test_wer_cer.py

### Documentation & Configuration
- [ ] T057 [P] CLI help text updates with --ai-model and --use-agentic-ai flags
- [ ] T058 [P] Configuration validation for AI model setup
- [ ] T059 [P] Error handling and user-friendly error messages
- [ ] T074 [P] Document provider layer configuration and environment variables

### CLI Implementation
- [ ] T064 CLI argument parsing implementation for --ai-model and --use-agentic-ai flags in lyrics_transcriber/cli/cli_main.py

### Quickstart Automation
- [ ] T060 Automated quickstart scenario runner in tests/integration/quickstart_runner.py
- [ ] T061 Test fixture creation (sample audio files with known errors)
- [ ] T062 End-to-end validation script matching quickstart.md scenarios
- [ ] T075 [P] Prompt evaluations with promptfoo in tests/promptfoo/
- [ ] T076 [P] Nightly regression script comparing models and routing strategies

### Reliability & Safeguards
- [ ] T077 Implement circuit breakers and backoff policies at provider and workflow level

### Output Format Compatibility
- [ ] T063 Output format compatibility validation (ASS, LRC, CDG, video) in tests/integration/test_output_format_compatibility.py

## Dependencies
**Critical Dependency Chains**:
- Tests (T006-T016) MUST complete before implementation (T017+)
- Models (T017-T023) before workflows (T029-T031)
- Providers (T024-T028) before agent (T032-T033)
- Agent (T032-T033) before API endpoints (T034-T038)
- Core implementation (T017-T041) before observability (T042-T047)
- Backend complete before frontend (T048-T050)
- Implementation complete before polish (T051-T062)

## Parallel Execution Examples

### Phase 3.1 - Setup (All Parallel)
```
Task: "Install agentic AI dependencies in pyproject.toml"
Task: "Configure LangFuse observability environment setup"
Task: "Configure Ollama local model server setup"
Task: "Configure multi-provider AI model authentication"
```

### Phase 3.2 - Contract Tests (All Parallel)
```
Task: "Contract test POST /api/v1/correction/agentic"
Task: "Contract test GET /api/v1/correction/session/{id}"
Task: "Contract test POST /api/v1/feedback"
Task: "Contract test GET /api/v1/models"
Task: "Contract test PUT /api/v1/models"  
Task: "Contract test GET /api/v1/metrics"
```

### Phase 3.3 - Entity Models (All Parallel)
```
Task: "AICorrection model class implementation"
Task: "HumanFeedback model class implementation"
Task: "CorrectionSession model class implementation"
Task: "LearningData model class implementation"
Task: "ObservabilityMetrics model class implementation"
```

### Phase 3.4 - AI Providers (All Parallel)
```
Task: "OpenAI provider implementation"
Task: "Anthropic provider implementation" 
Task: "Google provider implementation"
Task: "Ollama provider implementation"
```

## Validation Checklist
*GATE: Checked by implementation validation*

- [x] All contracts have corresponding tests (T006-T011)
- [x] All entities have model tasks (T017-T021)
- [x] All quickstart scenarios have integration tests (T012-T016)
- [x] All tests come before implementation (Phase 3.2 before 3.3+)
- [x] Parallel tasks truly independent (marked [P])
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] TDD workflow enforced (tests fail first, then implement)
- [x] Constitutional requirements maintained (90% coverage, performance targets)

## Task Generation Rules Applied
*Applied during task creation*

1. **From Contracts**: agentic_correction_api.yaml → 6 contract test tasks [P]
2. **From Data Model**: 5 entities → 5 model creation tasks [P] + 2 utility tasks [P]
3. **From Quickstart**: 5 scenarios → 5 integration test tasks [P]
4. **From Research**: LangGraph workflows, multi-provider architecture, LangFuse integration

## Success Criteria Validation
- **70% Error Reduction**: Validated by T055 performance benchmarks
- **<10s Processing Time**: Validated by T056 timing benchmarks
- **Multi-Model Support**: Implemented by T025-T028 provider tasks
- **Fallback Reliability**: Validated by T015 integration test and T040 implementation
- **Human Feedback Loop**: Implemented by T031, T045-T047, validated by T013
- **Comprehensive Observability**: Implemented by T042-T044, validated by T016

---

**Total Tasks**: 77 tasks across 8 phases
**Parallel Tasks**: 33 marked [P] for efficient execution
**Ready for Implementation**: All contract tests designed to fail initially, driving TDD workflow
