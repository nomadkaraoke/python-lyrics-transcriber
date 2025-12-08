# Data Model: Agentic AI Corrector

## Core Entities

### AICorrection
**Purpose**: Represents a correction suggested by the agentic AI system

**Attributes**:
- `id`: str - Unique correction identifier
- `original_text`: str - Original transcribed text
- `corrected_text`: str - AI-suggested corrected text
- `confidence_score`: float - AI confidence in correction (0.0-1.0)
- `reasoning`: str - AI explanation for the correction
- `model_used`: str - Identifier of AI model that made correction
- `correction_type`: CorrectionType - Categorization of error type
- `processing_time_ms`: int - Time taken to generate correction
- `tokens_used`: int - Token count for cost tracking
- `created_at`: datetime - Timestamp of correction generation
- `word_position`: int - Position of corrected word in transcription
- `session_id`: str - Reference to CorrectionSession

**Validation Rules**:
- `confidence_score` must be between 0.0 and 1.0
- `original_text` and `corrected_text` must not be identical
- `model_used` must be valid registered model identifier
- `processing_time_ms` must be positive

**State Transitions**:
- GENERATED → ACCEPTED (human reviewer accepts)
- GENERATED → REJECTED (human reviewer rejects)  
- GENERATED → MODIFIED (human reviewer modifies)

### HumanFeedback
**Purpose**: Captures human reviewer corrections and annotations

**Attributes**:
- `id`: str - Unique feedback identifier
- `ai_correction_id`: str - Reference to original AICorrection
- `reviewer_action`: ReviewerAction - ACCEPT, REJECT, MODIFY
- `final_text`: str - Final text after human review
- `reason_category`: FeedbackCategory - Structured reason for correction
- `reason_detail`: str - Optional detailed explanation
- `reviewer_confidence`: float - Human confidence in correction (0.0-1.0)
- `review_time_ms`: int - Time spent on review
- `reviewer_id`: str - Optional reviewer identifier
- `created_at`: datetime - Timestamp of feedback
- `session_id`: str - Reference to CorrectionSession

**Validation Rules**:
- `reviewer_action` required for all feedback
- `final_text` required when action is MODIFY
- `reason_category` required when action is REJECT or MODIFY
- `review_time_ms` must be positive
- `reviewer_confidence` must be between 0.0 and 1.0

**Relationships**:
- Belongs to one AICorrection (many-to-one)
- Belongs to one CorrectionSession (many-to-one)

### CorrectionSession
**Purpose**: Represents a complete correction cycle from initial AI processing through final human review

**Attributes**:
- `id`: str - Unique session identifier
- `audio_file_hash`: str - Hash of source audio file
- `session_type`: SessionType - FULL_CORRECTION, PARTIAL_REVIEW, REPROCESSING
- `ai_model_config`: dict - Configuration of AI models used
- `total_corrections`: int - Count of corrections made
- `accepted_corrections`: int - Count of AI corrections accepted
- `human_modifications`: int - Count of human modifications
- `session_duration_ms`: int - Total processing time
- `accuracy_improvement`: float - Percentage improvement achieved
- `started_at`: datetime - Session start timestamp
- `completed_at`: datetime - Session completion timestamp
- `status`: SessionStatus - IN_PROGRESS, COMPLETED, FAILED

**Validation Rules**:
- `audio_file_hash` must be valid SHA-256 hash
- Counts must be non-negative integers
- `accuracy_improvement` can be negative (if AI made things worse)
- `completed_at` must be after `started_at`

**Relationships**:
- Has many AICorrections (one-to-many)
- Has many HumanFeedback entries (one-to-many)
- References one LearningData aggregation (one-to-one)

### LearningData
**Purpose**: Aggregated data from human feedback used to improve AI performance

**Attributes**:
- `id`: str - Unique learning record identifier
- `session_id`: str - Reference to source CorrectionSession
- `error_patterns`: dict - Categorized error pattern frequencies
- `correction_strategies`: dict - Successful correction approach patterns
- `model_performance`: dict - Per-model accuracy and timing metrics
- `feedback_trends`: dict - Human feedback pattern analysis
- `improvement_metrics`: dict - Performance improvement over time
- `data_quality_score`: float - Quality assessment of learning data
- `created_at`: datetime - Timestamp of aggregation
- `expires_at`: datetime - Expiration date (3-year retention)

**Validation Rules**:
- All dict fields must contain valid JSON-serializable data
- `data_quality_score` must be between 0.0 and 1.0
- `expires_at` must be exactly 3 years from `created_at`

**Relationships**:
- Derived from one CorrectionSession (one-to-one)
- Aggregates multiple HumanFeedback entries (many-to-one conceptually)

### ObservabilityMetrics
**Purpose**: System performance data for monitoring and analysis

**Attributes**:
- `id`: str - Unique metrics record identifier
- `session_id`: str - Reference to CorrectionSession
- `ai_correction_accuracy`: float - Percentage of accepted AI corrections
- `processing_time_breakdown`: dict - Time spent in each correction phase
- `human_review_duration`: int - Total human review time in milliseconds
- `model_response_times`: dict - Response times per AI model
- `error_reduction_percentage`: float - Actual error reduction achieved
- `cost_tracking`: dict - Token usage and monetary cost per provider
- `system_health_indicators`: dict - Model availability and performance
- `improvement_trends`: dict - Performance trends over time
- `recorded_at`: datetime - Timestamp of metrics collection

**Validation Rules**:
- Percentage fields must be between 0.0 and 100.0
- Time fields must be non-negative
- Cost tracking must include valid provider identifiers
- All dict fields must be JSON-serializable

**Relationships**:
- References one CorrectionSession (many-to-one)
- Aggregates data from multiple AICorrections (conceptually many-to-one)

## Enumerations

### CorrectionType
- `WORD_SUBSTITUTION`: Incorrect word transcribed
- `WORD_INSERTION`: Extra word in transcription  
- `WORD_DELETION`: Missing word from transcription
- `PUNCTUATION`: Punctuation correction
- `TIMING_ADJUSTMENT`: Word timing correction
- `LINGUISTIC_IMPROVEMENT`: Grammar/style enhancement

### ReviewerAction
- `ACCEPT`: Human accepts AI correction as-is
- `REJECT`: Human rejects AI correction, keeps original
- `MODIFY`: Human modifies AI correction to different text

### FeedbackCategory
- `AI_CORRECT`: AI suggestion was correct
- `AI_INCORRECT`: AI suggestion was wrong
- `AI_SUBOPTIMAL`: AI suggestion was correct but suboptimal
- `CONTEXT_NEEDED`: AI lacked context for good correction
- `SUBJECTIVE_PREFERENCE`: Human preference over AI choice

### SessionType
- `FULL_CORRECTION`: Complete AI-driven correction cycle
- `PARTIAL_REVIEW`: Human review of subset of corrections
- `REPROCESSING`: Re-running correction with different models

### SessionStatus
- `IN_PROGRESS`: Session currently active
- `COMPLETED`: Session finished successfully
- `FAILED`: Session terminated due to error

## Entity Relationships

```
CorrectionSession
├── AICorrection (1:many)
│   └── HumanFeedback (1:many)
├── LearningData (1:1)
└── ObservabilityMetrics (1:many)
```

## Data Flow

1. **Correction Generation**: CorrectionSession creates multiple AICorrections
2. **Human Review**: Each AICorrection receives HumanFeedback
3. **Learning Aggregation**: Session data is aggregated into LearningData
4. **Performance Tracking**: ObservabilityMetrics capture system performance
5. **Continuous Improvement**: LearningData influences future correction strategies

## Storage Considerations

- **File-based Storage**: JSON files for compatibility with existing caching pattern
- **Compression**: LearningData compressed for long-term storage
- **Retention Policy**: 3-year retention with automated cleanup
- **Privacy**: No personally identifiable information in stored data
- **Backup Strategy**: Regular backups of learning data for continuity

## Performance Optimizations

- **Indexing**: Hash-based lookups for sessions and corrections
- **Batch Processing**: Aggregate multiple corrections for efficiency
- **Lazy Loading**: Load detailed feedback only when needed
- **Caching**: In-memory cache for frequently accessed learning patterns
