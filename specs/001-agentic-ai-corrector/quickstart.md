# Quickstart: Agentic AI Corrector

## Overview

This quickstart guide validates the core functionality of the Agentic AI Corrector through integration test scenarios derived from user stories. Each scenario represents a critical user journey that must work correctly.

## Prerequisites

- Python 3.10+ environment with lyrics-transcriber installed
- AI model API keys configured (OpenAI, Anthropic, Google, or local Ollama setup)
- Sample audio files for testing (provided in test fixtures)
- LangFuse observability configured (optional but recommended)

## Test Scenarios

### Scenario 1: Basic AI Correction Workflow
**User Story**: As a lyrics transcriber user, I want the AI to automatically correct transcription errors so I spend less time on manual review.

**Setup**:
```bash
# Prepare test audio file with known transcription errors
export AUDIO_FILE="tests/fixtures/sample_with_errors.mp3"
export REFERENCE_LYRICS="tests/fixtures/sample_reference.txt"

# Configure AI model (choose one)
export OPENAI_API_KEY="your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"  
# OR ensure Ollama is running locally
```

**Steps**:
1. **Transcribe with existing system** (to establish baseline):
   ```bash
   lyrics-transcriber $AUDIO_FILE --skip-correction --output-dir baseline/
   ```

2. **Process with agentic AI corrector**:
   ```bash
   lyrics-transcriber $AUDIO_FILE --use-agentic-ai --ai-model claude-4-sonnet --output-dir agentic/
   ```

3. **Validate improvements**:
   ```bash
   # Compare error counts between baseline and agentic results
   python -c "
   import json
   with open('baseline/corrections.json') as f:
       baseline = json.load(f)
   with open('agentic/corrections.json') as f:
       agentic = json.load(f)
   
   baseline_errors = len(baseline.get('corrections', []))
   agentic_errors = len([c for c in agentic.get('corrections', []) if c.get('requires_human_review')])
   
   error_reduction = (baseline_errors - agentic_errors) / baseline_errors * 100
   print(f'Error reduction: {error_reduction:.1f}%')
   assert error_reduction >= 70, f'Expected 70% reduction, got {error_reduction:.1f}%'
   print('✓ 70% error reduction achieved')
   "
   ```

**Expected Results**:
- ✅ AI processing completes within 10 seconds per song
- ✅ At least 70% reduction in errors requiring human review
- ✅ Output formats (ASS, LRC) generated correctly
- ✅ Observability metrics collected (if LangFuse configured)

### Scenario 2: Human Review and Feedback Loop
**User Story**: As a human reviewer, I want to provide feedback on AI corrections so the system learns from my input.

**Setup**:
```bash
# Start the review server
lyrics-transcriber-server --port 8000 &
SERVER_PID=$!

# Process a file that will require some human corrections
export TEST_FILE="tests/fixtures/complex_lyrics.mp3"
```

**Steps**:
1. **Generate AI corrections**:
   ```bash
   lyrics-transcriber $TEST_FILE --use-agentic-ai --enable-review --output-dir review_test/
   ```

2. **Review interface should auto-open at http://localhost:8000**
   - Verify AI corrections are displayed with confidence scores
   - Verify feedback interface allows categorizing corrections
   - Make test corrections with different feedback categories:
     - Accept 2 AI suggestions (AI_CORRECT)
     - Reject 1 AI suggestion (AI_INCORRECT) 
     - Modify 1 AI suggestion (AI_SUBOPTIMAL)

3. **Validate feedback collection**:
   ```bash
   python -c "
   import json
   with open('review_test/corrections.json') as f:
       data = json.load(f)
   
   feedback = data.get('human_feedback', [])
   assert len(feedback) >= 4, f'Expected 4 feedback entries, got {len(feedback)}'
   
   categories = [f.get('reason_category') for f in feedback]
   assert 'AI_CORRECT' in categories, 'Missing AI_CORRECT feedback'
   assert 'AI_INCORRECT' in categories, 'Missing AI_INCORRECT feedback' 
   assert 'AI_SUBOPTIMAL' in categories, 'Missing AI_SUBOPTIMAL feedback'
   
   print('✓ Human feedback collected successfully')
   "
   ```

4. **Cleanup**:
   ```bash
   kill $SERVER_PID
   ```

**Expected Results**:
- ✅ Review interface displays AI corrections with explanations
- ✅ Human feedback is captured with proper categorization
- ✅ Feedback is stored for future learning (3-year retention policy)
- ✅ Session metrics recorded accurately

### Scenario 3: Multi-Model Comparison and Selection
**User Story**: As a system operator, I want to compare different AI models to optimize correction accuracy.

**Setup**:
```bash
# Ensure multiple models are configured
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key" 
export GOOGLE_API_KEY="your-google-key"

# Test file with diverse error types
export COMPARISON_FILE="tests/fixtures/multi_error_types.mp3"
```

**Steps**:
1. **Process with different models**:
   ```bash
   # Test Claude 4 Sonnet
   lyrics-transcriber $COMPARISON_FILE --ai-model claude-4-sonnet --output-dir claude_test/
   
   # Test GPT-5
   lyrics-transcriber $COMPARISON_FILE --ai-model gpt-5 --output-dir gpt_test/
   
   # Test Gemini 2.5 Pro
   lyrics-transcriber $COMPARISON_FILE --ai-model gemini-2.5-pro --output-dir gemini_test/
   
   # Test model chaining (experimental)
   lyrics-transcriber $COMPARISON_FILE --ai-models claude-4-sonnet,gpt-5 --use-consensus --output-dir consensus_test/
   ```

2. **Compare model performance**:
   ```bash
   python -c "
   import json
   from pathlib import Path
   
   models = ['claude', 'gpt', 'gemini', 'consensus']
   results = {}
   
   for model in models:
       with open(f'{model}_test/corrections.json') as f:
           data = json.load(f)
           results[model] = {
               'accuracy': data.get('accuracy_estimate', 0),
               'processing_time': data.get('processing_time_ms', 0),
               'cost': data.get('cost_tracking', {}).get('total_cost', 0)
           }
   
   print('Model Comparison Results:')
   for model, metrics in results.items():
       print(f'{model:10}: {metrics[\"accuracy\"]:.2%} accuracy, {metrics[\"processing_time\"]}ms, \${metrics[\"cost\"]:.4f}')
   
   print('✓ Multi-model comparison completed')
   "
   ```

**Expected Results**:
- ✅ All configured models process successfully
- ✅ Performance metrics collected for each model
- ✅ Cost tracking works across providers
- ✅ Consensus mode (if implemented) shows improved accuracy

### Scenario 4: Fallback and Reliability
**User Story**: As a user, I want the system to work even when AI services are unavailable.

**Setup**:
```bash
# Simulate AI service unavailability
export OPENAI_API_KEY="invalid-key-to-trigger-failure"
export TEST_FALLBACK_FILE="tests/fixtures/standard_test.mp3"
```

**Steps**:
1. **Attempt AI correction with invalid credentials**:
   ```bash
   lyrics-transcriber $TEST_FALLBACK_FILE --ai-model gpt-5 --enable-fallback --output-dir fallback_test/
   ```

2. **Verify fallback activation**:
   ```bash
   python -c "
   import json
   with open('fallback_test/corrections.json') as f:
       data = json.load(f)
   
   assert data.get('fallback_used') == True, 'Fallback should have been activated'
   assert data.get('fallback_reason'), 'Fallback reason should be recorded'
   assert len(data.get('corrections', [])) > 0, 'Rule-based corrections should be present'
   
   print('✓ Fallback system working correctly')
   print(f'Fallback reason: {data.get(\"fallback_reason\")}')
   "
   ```

**Expected Results**:
- ✅ System automatically falls back to rule-based correction
- ✅ Fallback reason is logged and reported
- ✅ Processing completes successfully despite AI failure
- ✅ User receives usable output

### Scenario 5: Performance and Observability
**User Story**: As a system operator, I want to monitor AI correction performance and system health.

**Setup**:
```bash
# Configure LangFuse (optional but recommended)
export LANGFUSE_SECRET_KEY="your-langfuse-key"
export LANGFUSE_PUBLIC_KEY="your-public-key"

# Test with monitoring enabled
export MONITOR_FILE="tests/fixtures/performance_test.mp3"
```

**Steps**:
1. **Process with full observability**:
   ```bash
   lyrics-transcriber $MONITOR_FILE --ai-model claude-4-sonnet --enable-monitoring --output-dir monitor_test/
   ```

2. **Validate metrics collection**:
   ```bash
   # Check local metrics
   python -c "
   import json
   with open('monitor_test/corrections.json') as f:
       data = json.load(f)
   
   metrics = data.get('observability_metrics', {})
   assert metrics.get('ai_correction_accuracy') is not None
   assert metrics.get('processing_time_breakdown') is not None
   assert metrics.get('model_response_times') is not None
   
   print('✓ Observability metrics collected')
   print(f'AI accuracy: {metrics.get(\"ai_correction_accuracy\", 0):.1%}')
   print(f'Processing time: {metrics.get(\"processing_time_breakdown\", {}).get(\"total\", 0)}ms')
   "
   
   # Check LangFuse dashboard (if configured)
   echo "Check LangFuse dashboard for detailed traces and metrics"
   ```

3. **Health check validation**:
   ```bash
   # Test metrics API endpoint
   curl -s http://localhost:8000/api/v1/metrics | python -m json.tool
   
   # Test model status
   curl -s http://localhost:8000/api/v1/models | python -m json.tool
   ```

**Expected Results**:
- ✅ Comprehensive metrics collected automatically
- ✅ LangFuse traces show detailed AI interaction flow
- ✅ Health check endpoints respond correctly
- ✅ Performance meets constitutional requirements (<10s processing)

## Integration Test Validation

### Automated Test Suite
Run the complete integration test suite to validate all scenarios:

```bash
# Run contract tests (should initially fail)
pytest tests/contract/ -v

# Run integration tests
pytest tests/integration/test_agentic_correction.py -v

# Run end-to-end scenario validation
python tests/integration/test_quickstart_scenarios.py
```

### Success Criteria Validation

After completing all scenarios, validate overall success criteria:

```bash
python -c "
import json
from pathlib import Path

# Collect metrics from all test runs
test_dirs = ['agentic', 'review_test', 'fallback_test', 'monitor_test']
total_error_reduction = 0
processing_times = []

for test_dir in test_dirs:
    corrections_file = Path(f'{test_dir}/corrections.json')
    if corrections_file.exists():
        with open(corrections_file) as f:
            data = json.load(f)
        
        if 'error_reduction_percentage' in data:
            total_error_reduction += data['error_reduction_percentage']
        if 'processing_time_ms' in data:
            processing_times.append(data['processing_time_ms'])

avg_error_reduction = total_error_reduction / len(test_dirs)
avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

print('🎯 Overall Success Criteria Validation:')
print(f'Average error reduction: {avg_error_reduction:.1f}% (target: 70%+)')
print(f'Average processing time: {avg_processing_time:.0f}ms (target: <10,000ms)')

assert avg_error_reduction >= 70, f'Failed: Error reduction {avg_error_reduction:.1f}% < 70%'
assert avg_processing_time < 10000, f'Failed: Processing time {avg_processing_time:.0f}ms >= 10s'

print('✅ All success criteria met!')
print('🚀 Agentic AI Corrector ready for production use')
"
```

## Troubleshooting

### Common Issues
- **AI API failures**: Check API keys and model availability
- **Slow processing**: Verify model response times and network connectivity
- **Missing feedback**: Ensure review server is running and accessible
- **Test failures**: Check that all dependencies are installed and services are running

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
export LYRICS_TRANSCRIBER_LOG_LEVEL=DEBUG
lyrics-transcriber --help  # Shows additional debug options
```

### Support Resources
- Check LangFuse dashboard for AI interaction traces
- Review local log files in `~/.lyrics-transcriber/logs/`
- Examine correction JSON files for detailed processing information
