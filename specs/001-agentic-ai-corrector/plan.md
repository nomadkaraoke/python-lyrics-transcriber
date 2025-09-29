
# Implementation Plan: Agentic AI Corrector

**Branch**: `001-agentic-ai-corrector` | **Date**: 2025-09-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/andrew/Projects/karaoke-gen/lyrics_transcriber_local/specs/001-agentic-ai-corrector/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
**Primary Requirement**: Replace the existing rule-based lyrics correction system with an agentic AI system that achieves a minimum 70% reduction in errors requiring human correction, while maintaining the human review workflow for quality control and continuous learning.

**Technical Approach**: Multi-model, semi-agentic correction system using LangGraph/LangChain with constrained tool actions; provider abstraction via LiteLLM or OpenRouter; comprehensive observability via Langfuse; structured JSON outputs enforced by Pydantic/Instructor; supports cloud APIs (Gemini 2.5 Pro, GPT-5, Claude 4 Sonnet) and local models (Ollama); SQLite/DuckDB-backed feedback store with 3-year retention.

## Technical Context
**Language/Version**: Python 3.10-3.13 (existing codebase compatibility)  
**Primary Dependencies**: FastAPI (existing review server), LangGraph/LangChain (agentic workflows), Langfuse (observability), LiteLLM or OpenRouter (provider abstraction), Pydantic + Instructor (structured outputs), SQLite or DuckDB (feedback DB), Ollama (local models), OpenAI/Anthropic/Google APIs (cloud models)  
**Storage**: File-based caching (existing pattern), 3-year human feedback storage with compression  
**Testing**: pytest with 90% coverage requirement, contract tests for AI model interfaces, integration tests for correction workflows  
**Target Platform**: Cross-platform desktop/server (Linux, macOS, Windows) with web UI  
**Project Type**: Single Python project with web frontend (FastAPI + React/TypeScript)  
**Performance Goals**: 70% error reduction, <10s correction per song, variable review time by complexity; strict per-call timeouts (2–4s) and bounded iterations  
**Constraints**: Maintain output format compatibility, graceful fallback to rule-based; enforce structured schema, idempotent application, and auditable decisions  
**Scale/Scope**: Individual user processing, experimental multi-model approach, comprehensive observability instrumentation

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Test-Driven Development (NON-NEGOTIABLE)**:
- [x] All tests will be written before implementation code (TDD workflow enforced)
- [x] Contract tests planned for all AI model interfaces and correction APIs
- [x] Integration tests planned for correction workflows and human feedback loops
- [x] Minimum 90% code coverage target set for new agentic correction module

**Code Quality & Maintainability**:
- [x] Type hints planned for all agentic AI interfaces and correction functions
- [x] Comprehensive docstrings planned for public APIs with usage examples
- [x] Linting and static analysis configured (existing flake8/black/mypy pipeline)
- [x] No code duplication >15 lines (AI correction patterns will be abstracted)

**User Experience Consistency**:
- [x] CLI follows Unix conventions (maintains existing patterns, adds --ai-model flag)
- [x] Error messages are actionable (AI failures show clear fallback options)
- [x] UI changes meet accessibility standards (extends existing React components)
- [x] Consistent interaction patterns (maintains existing review UI flow)

**Performance & Reliability**:
- [x] Performance budgets defined (<10s correction time, 70% error reduction target)
- [x] External API retry logic with exponential backoff planned for all AI providers
- [x] Proper resource cleanup planned (AI model memory management, 3-year data retention)
- [x] Graceful failure handling designed (automatic fallback to rule-based correction)

**Observability & Monitoring**:
- [x] Structured logging planned with LangFuse integration and consistent formatting
- [x] Performance metrics collection designed (correction accuracy, model response times)
- [x] External AI service interactions instrumented with comprehensive tracing
- [x] Health checks planned for AI model availability and correction pipeline status

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
lyrics_transcriber/
├── correction/
│   ├── agentic/                    # NEW: Agentic AI correction system
│   │   ├── __init__.py
│   │   ├── agent.py               # Main agentic corrector
│   │   ├── models/                # AI model interfaces
│   │   ├── workflows/             # LangGraph workflows
│   │   ├── feedback/              # Human feedback processing
│   │   └── observability/         # LangFuse instrumentation
│   ├── handlers/                   # EXISTING: Rule-based handlers (fallback)
│   └── corrector.py               # MODIFIED: Route to agentic or rule-based
├── frontend/                       # EXISTING: React review interface
│   └── src/components/            # MODIFIED: Add AI feedback UI components
├── review/
│   └── server.py                  # MODIFIED: Add AI model management endpoints
└── types.py                       # MODIFIED: Add agentic correction types

tests/
├── contract/                       # NEW: AI model interface tests
│   ├── test_ai_models.py
│   └── test_correction_contracts.py
├── integration/                    # NEW: End-to-end correction workflows
│   ├── test_agentic_correction.py
│   └── test_feedback_loop.py
└── unit/                          # EXISTING: Extended with agentic module tests
    └── correction/agentic/
```

**Structure Decision**: Single Python project with web frontend. The agentic AI system will be integrated as a new submodule within the existing correction framework, maintaining compatibility with the current architecture while adding new capabilities.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh cursor`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: ✅ data-model.md, ✅ /contracts/agentic_correction_api.yaml, ✅ failing contract tests, ✅ quickstart.md, ✅ .cursor/rules/specify-rules.mdc

## Constitution Check Re-evaluation
*Post-Design Review*

**Re-evaluation Result**: ✅ PASS - All constitutional principles maintained after detailed design

**Design Validation**:
- **TDD**: Contract tests created and designed to fail initially until implementation
- **Code Quality**: OpenAPI contracts specify typed interfaces, comprehensive docstring standards planned
- **User Experience**: Design maintains existing review workflow, adds enhanced AI feedback mechanisms
- **Performance**: Specific performance budgets preserved (<10s processing, 70% error reduction)
- **Observability**: LangFuse integration designed with comprehensive metrics collection

**New Design Elements Validated**:
- Multi-model architecture maintains reliability principles through fallback design
- Human feedback loop preserves user experience consistency
- API contracts enforce quality standards through schema validation

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (data-model.md, contracts/, quickstart.md)
- **Contract Tests**: agentic_correction_api.yaml → test_agentic_correction_api.py [P]
- **Entity Models**: AICorrection, HumanFeedback, CorrectionSession, LearningData, ObservabilityMetrics [P]
- **Integration Tests**: Each quickstart scenario → comprehensive integration test
- **Implementation**: API endpoints, agentic workflows, observability integration

**Specific Task Categories**:
1. **Setup Tasks**: Project dependencies (LangChain, LangFuse, Ollama), environment configuration
2. **Model Tasks**: Data model classes with validation, type hints, serialization [P]
3. **Contract Implementation**: API endpoint implementation to pass contract tests
4. **Agentic Core**: LangGraph workflows, multi-model routing, human feedback integration
5. **Integration**: Existing corrector integration, fallback mechanisms, observability
6. **Validation**: Quickstart scenario automation, performance benchmarking

**Ordering Strategy**:
- **Phase 1**: Setup → Contract Tests → Model Classes (all [P])
- **Phase 2**: Core agentic implementation → API endpoints  
- **Phase 3**: Integration with existing system → Fallback mechanisms
- **Phase 4**: Observability → Performance validation → Quickstart automation

**Estimated Output**: 64 numbered, ordered tasks in tasks.md with clear [P] markings for parallel execution

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (via /clarify session)
- [x] Complexity deviations documented (none identified)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
