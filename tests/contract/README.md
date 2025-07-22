# Backend-Frontend Contract Testing

This directory contains contract tests that ensure data compatibility between the Python backend and TypeScript frontend. These tests prevent critical issues where the frontend becomes unusable due to data format mismatches.

## Background

The contract testing infrastructure was created to address a critical bug where:

1. **Backend** generated anchor sequences in old format (`words`, `text`, `length`) when loading from cache
2. **Frontend** expected new format (`id`, `transcribed_word_ids`, `reference_word_ids`) per Zod validation schema
3. **Result** Complete frontend failure with validation errors

Despite having 548 comprehensive tests with 64% coverage, this issue wasn't caught because there were no tests validating the contract between backend serialization and frontend validation.

## Test Structure

### Contract Tests (`test_frontend_schemas.py`)
- **Purpose**: Validate that backend `to_dict()` outputs match frontend Zod schemas
- **Key Tests**:
  - `test_anchor_sequence_schema_compatibility()` - Would have caught the original bug
  - `test_old_format_anchor_sequence_frontend_compatibility()` - Regression test for cache format conversion
  - `test_correction_result_full_compatibility()` - End-to-end validation of complete data pipeline

### End-to-End Tests (`test_end_to_end_data_pipeline.py`)
- **Purpose**: Test complete data flow without mocking serialization/deserialization
- **Key Tests**:
  - `test_complete_anchor_sequence_pipeline_no_mocks()` - Full anchor sequence generation and validation
  - `test_old_cached_data_compatibility_pipeline()` - Cache format migration testing
  - `test_correction_result_end_to_end_pipeline()` - Complete correction workflow validation

## How It Works

### 1. Frontend Schema Validation Script
The Node.js script `lyrics_transcriber/frontend/scripts/validate-schemas.js`:
- Exports all frontend Zod schemas for external validation
- Can be called from Python tests to validate data structures
- Returns detailed validation errors for debugging

```bash
# Example usage
node validate-schemas.js --schema=anchorSequence --data='{"id":"test","transcribed_word_ids":["w1"],...}'
```

### 2. Python Contract Test Framework
The `FrontendSchemaValidator` class:
- Calls the Node.js validation script from Python tests
- Handles error reporting and debugging
- Provides clean integration with pytest

```python
def test_my_data_structure(validator):
    data = my_backend_object.to_dict()
    result = validator.validate_data("anchorSequence", data)
    assert result["success"], f"Validation failed: {result.get('errors')}"
```

## Running Contract Tests

### Prerequisites
1. **Node.js**: Required for frontend schema validation
2. **Frontend Dependencies**: Run `cd lyrics_transcriber/frontend && yarn install`

### Running Tests

```bash
# Run all contract tests
pytest tests/contract/ -v

# Run specific contract test file
pytest tests/contract/test_frontend_schemas.py -v

# Run with Node.js validation (requires Node.js setup)
pytest tests/contract/ -v --tb=short

# Skip Node.js tests if not available
pytest tests/contract/ -v -k "not validator"
```

### CI Integration
Contract tests automatically skip when Node.js is not available, making them CI-friendly:

```python
try:
    validator.validate_data("test", test_data)
except RuntimeError as e:
    if "Node.js not found" in str(e):
        pytest.skip("Node.js not available for frontend validation")
```

## Adding New Contract Tests

### For New Backend Types

1. **Add schema to validation script**:
```javascript
// In validate-schemas.js
const MyNewTypeSchema = z.object({
    id: z.string(),
    // ... other fields
})

const schemas = {
    // ... existing schemas
    myNewType: MyNewTypeSchema
}
```

2. **Add contract test**:
```python
def test_my_new_type_schema_compatibility(validator):
    """Test that MyNewType.to_dict() matches frontend schema."""
    obj = MyNewType(id="test", ...)
    serialized = obj.to_dict()
    
    result = validator.validate_data("myNewType", serialized)
    assert result["success"], f"Validation failed: {result.get('errors')}"
```

### For Schema Changes

When changing data structures:

1. **Update frontend schema first** in `validation.ts`
2. **Update validation script** in `validate-schemas.js`
3. **Run contract tests** to see what backend changes are needed
4. **Update backend serialization** to match new schema
5. **Add migration logic** if backwards compatibility is needed

## Frontend Testing Setup

The frontend now has a complete testing infrastructure:

### Vitest Configuration
- **Test runner**: Vitest (fast, Vite-native)
- **DOM environment**: jsdom
- **Coverage**: v8 coverage provider
- **UI**: Vitest UI for interactive testing

### Package Scripts
```bash
cd lyrics_transcriber/frontend

# Run tests
yarn test

# Run tests with UI
yarn test:ui

# Run tests once (CI mode)
yarn test:run

# Run with coverage
yarn test:coverage

# Validate schemas (contract testing)
yarn validate-schemas
```

### Frontend Unit Tests
Example test structure in `validation.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { validateCorrectionData } from './validation'

describe('Frontend Validation', () => {
  it('should validate correct anchor sequence format', () => {
    const validData = {
      id: "anchor-1",
      transcribed_word_ids: ["word1", "word2"],
      // ... other required fields
    }
    
    expect(() => validateCorrectionData(validData)).not.toThrow()
  })
})
```

## Benefits

This contract testing infrastructure provides:

1. **Early Detection**: Catches backend-frontend mismatches before deployment
2. **Documentation**: Tests serve as living documentation of the data contract
3. **Confidence**: Ensures schema changes don't break the frontend
4. **Regression Prevention**: Prevents the specific bug that motivated this work
5. **Migration Safety**: Validates that data format migrations work correctly

## The Specific Bug This Prevents

The original bug occurred because:

1. `AnchorSequence.to_dict()` returned old format when `_words` was present
2. Frontend expected new format with `id`, `transcribed_word_ids`, `reference_word_ids`
3. No tests validated this contract

The contract test `test_old_format_anchor_sequence_frontend_compatibility()` would have caught this by:

1. Creating old format cached data
2. Loading it through backend logic
3. Validating the output against frontend schema
4. **Failing** when old format fields were present

## Future Improvements

1. **Automated Schema Sync**: Auto-generate TypeScript types from Python dataclasses
2. **Performance Testing**: Validate schema validation performance impact
3. **Mock Data Generation**: Generate test data from schemas
4. **Contract Versioning**: Track contract changes over time
5. **Distribution Testing**: Validate PyPI packages against frontend schemas 