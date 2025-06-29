# Test Restoration Plan for Python Lyrics Transcriber

## Overview

This project has 243 skipped tests out of 447 total tests that were disabled due to functional changes in the codebase. The tests were systematically disabled by adding them to a `SKIP_PATTERNS` list in `tests/conftest.py` with the reason "Skipped due to codebase changes".

## Root Cause Analysis

The main breaking change was the evolution of the `GapSequence` and `AnchorSequence` APIs from using direct word data to ID-based references. The old API looked like:

```python
# Old API (broken)
gap = GapSequence(
    words=("hello", "world"),
    transcription_position=0,
    preceding_anchor=None,
    following_anchor=None,
    reference_words={"genius": ["hello", "world"]}
)
```

The new API uses ID-based references:

```python
# New API (current)
gap = GapSequence(
    id="gap_123",
    transcribed_word_ids=["word_1", "word_2"],
    transcription_position=0,
    preceding_anchor_id=None,
    following_anchor_id=None,
    reference_word_ids={"genius": ["ref_word_1", "ref_word_2"]}
)
```

## Skipped Test Inventory

### Currently Skipped Test Modules (Full Files)
- `tests/correction/handlers/test_extra_words.py` (7 tests)
- `tests/correction/handlers/test_levenshtein.py` (5 tests)  
- `tests/correction/handlers/test_repeat.py` (5 tests)
- `tests/correction/handlers/test_sound_alike.py` (6 tests)
- `tests/correction/handlers/test_word_count_match.py` (9 tests)
- `tests/correction/test_anchor_sequence_1.py` (25 tests)
- `tests/correction/test_anchor_sequence_2.py` (13 tests)
- `tests/correction/test_corrector.py` (7 tests)
- `tests/core/test_controller.py` (26 tests)
- `tests/output/ass/test_lyrics_line.py` (12 tests)
- `tests/output/ass/test_lyrics_screen.py` (18 tests) 
- `tests/output/ass/test_section_detector.py` (10 tests)
- `tests/output/test_generator.py` (10 tests)
- `tests/output/test_lyrics_file.py` (7 tests)
- `tests/output/test_plain_text.py` (8 tests)
- `tests/output/test_segment_resizer.py` (22 tests)
- `tests/output/test_subtitles.py` (17 tests)
- `tests/output/test_video.py` (12 tests)

### Currently Skipped Specific Test Functions
- `tests/cli/test_cli_main.py::test_create_arg_parser`
- `tests/cli/test_cli_main.py::test_create_configs`
- `tests/correction/test_phrase_analyzer.py::test_error_handling`
- `tests/correction/test_text_utils.py::test_punctuation_removal`
- `tests/correction/test_text_utils.py::test_hyphenated_words`
- `tests/correction/test_text_utils.py::test_whitespace_normalization`
- `tests/correction/test_text_utils.py::test_mixed_cases`
- `tests/correction/test_text_utils.py::test_empty_and_special_cases`
- `tests/lyrics/test_base_lyrics_provider.py::test_word_to_dict`
- `tests/lyrics/test_base_lyrics_provider.py::test_lyrics_segment_to_dict`
- `tests/lyrics/test_base_lyrics_provider.py::test_fetch_lyrics_with_cache`
- `tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_init_with_token`
- `tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_convert_result_format`
- `tests/lyrics/test_genius_provider.py::TestGeniusProvider::test_convert_result_format_missing_fields`
- `tests/lyrics/test_spotify_provider.py::TestSpotifyProvider::test_convert_result_format`
- `tests/lyrics/test_spotify_provider.py::TestSpotifyProvider::test_convert_result_format_minimal`
- `tests/output/ass/test_config.py::test_screen_config_defaults`
- `tests/transcribers/test_base_transcriber.py::TestTranscriptionData::test_data_creation`
- `tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_transcribe_implementation`
- `tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_caching_mechanism`
- `tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_cache_file_structure`
- `tests/transcribers/test_base_transcriber.py::TestBaseTranscriber::test_invalid_cache_handling`
- `tests/transcribers/test_whisper.py::TestWhisperTranscriber::test_perform_transcription_success`

## Phased Restoration Plan

### Phase 1: Foundation & Core Types (Week 1)
**Priority: Critical - Everything depends on this**

#### Goals:
- Establish patterns for new API usage
- Create reusable test utilities
- Fix the central orchestrator

#### Tasks:
1. **Create Test Utilities** (`tests/test_helpers.py`)
   ```python
   def create_test_word(word_id: str, text: str, start_time: float, end_time: float) -> Word
   def create_test_gap_sequence(words: List[str], reference_words: Dict[str, List[str]]) -> GapSequence  
   def create_test_anchor_sequence(...) -> AnchorSequence
   def create_word_map(words: List[Word]) -> Dict[str, Word]
   ```

2. **Fix Core Controller Tests**
   - File: `tests/core/test_controller.py` (26 skipped tests)
   - This orchestrates the entire correction pipeline
   - Establish API usage patterns for other phases

#### Success Criteria:
- All controller tests passing
- Test utility patterns established
- Documentation of new API usage

### Phase 2: Correction Engine (Weeks 2-3)  
**Priority: High - Core functionality**

#### Goals:
- Restore correction handler functionality
- Fix gap and anchor sequence logic
- Ensure correction pipeline works end-to-end

#### Tasks:
1. **Correction Handler Tests** (32 tests total)
   - `tests/correction/handlers/test_extra_words.py` (7 tests)
   - `tests/correction/handlers/test_levenshtein.py` (5 tests)
   - `tests/correction/handlers/test_repeat.py` (5 tests)
   - `tests/correction/handlers/test_sound_alike.py` (6 tests)
   - `tests/correction/handlers/test_word_count_match.py` (9 tests)

2. **Correction Core Logic** (45 tests total)
   - `tests/correction/test_corrector.py` (7 tests)
   - `tests/correction/test_anchor_sequence_1.py` (25 tests)
   - `tests/correction/test_anchor_sequence_2.py` (13 tests)

3. **Correction Utilities** (6 tests total)
   - `tests/correction/test_text_utils.py` (5 specific functions)
   - `tests/correction/test_phrase_analyzer.py::test_error_handling` (1 test)

#### Success Criteria:
- All correction handlers working with new API
- Gap and anchor sequence tests passing
- End-to-end correction pipeline functional

### Phase 3: Output Generation (Weeks 4-5)
**Priority: Medium-High - User-facing functionality**

#### Goals:
- Restore all output format generation
- Fix ASS subtitle generation (primary format)
- Ensure video and other outputs work

#### Tasks:
1. **ASS Format Output** (40 tests total)
   - `tests/output/ass/test_lyrics_line.py` (12 tests)
   - `tests/output/ass/test_lyrics_screen.py` (18 tests)
   - `tests/output/ass/test_section_detector.py` (10 tests)

2. **Other Output Formats** (76 tests total)
   - `tests/output/test_generator.py` (10 tests)
   - `tests/output/test_lyrics_file.py` (7 tests)
   - `tests/output/test_plain_text.py` (8 tests)
   - `tests/output/test_subtitles.py` (17 tests)
   - `tests/output/test_video.py` (12 tests)
   - `tests/output/test_segment_resizer.py` (22 tests)

3. **Configuration Tests** (1 test)
   - `tests/output/ass/test_config.py::test_screen_config_defaults`

#### Success Criteria:
- All output formats generating correctly
- ASS subtitle output fully functional
- Video generation pipeline working

### Phase 4: Data Providers & CLI (Week 6)
**Priority: Medium - Important but less critical**

#### Goals:
- Fix data provider integrations
- Restore CLI functionality
- Complete transcriber test coverage

#### Tasks:
1. **Lyrics Provider Tests** (8 tests total)
   - `tests/lyrics/test_base_lyrics_provider.py` (3 specific functions)
   - `tests/lyrics/test_genius_provider.py` (3 specific functions)
   - `tests/lyrics/test_spotify_provider.py` (2 specific functions)

2. **CLI Tests** (2 tests total)
   - `tests/cli/test_cli_main.py::test_create_arg_parser`
   - `tests/cli/test_cli_main.py::test_create_configs`

3. **Transcriber Tests** (6 tests total)
   - `tests/transcribers/test_base_transcriber.py` (5 specific functions)
   - `tests/transcribers/test_whisper.py` (1 specific function)

#### Success Criteria:
- All data providers working
- CLI properly configured and functional
- Transcription pipeline fully tested

## Implementation Strategy

### Development Approach
1. **One Phase at a Time**: Complete each phase before moving to the next
2. **Incremental Progress**: Update `SKIP_PATTERNS` as tests are fixed
3. **Frequent Testing**: Run test suite after each fix to catch regressions
4. **Documentation**: Document API changes and patterns discovered

### Context Window Management
For large files, we'll:
- Focus on one test class/function at a time
- Use search tools to understand current API before making changes
- Create focused work sessions on specific test files
- Reference this plan document to maintain continuity

### Quality Assurance
- Each fixed test must pass consistently
- No regressions in previously working tests
- Follow established patterns from Phase 1
- Maintain code quality and readability

## Test Restoration Checklist

### Phase 1 (Foundation) ✅ COMPLETED
- [x] Create test utilities (`tests/test_helpers.py`)
- [x] Fix `tests/core/test_controller.py` (26 tests) - ALL PASSING!
- [x] Document new API patterns
- [x] Update `SKIP_PATTERNS` for completed tests

### Phase 2 (Correction Engine) 
- [ ] Fix correction handler tests (32 tests)
- [ ] Fix correction core logic tests (45 tests)
- [ ] Fix correction utility tests (6 tests)
- [ ] Update `SKIP_PATTERNS` for completed tests

### Phase 3 (Output Generation)
- [ ] Fix ASS format tests (40 tests)
- [ ] Fix other output format tests (76 tests)
- [ ] Fix configuration tests (1 test)
- [ ] Update `SKIP_PATTERNS` for completed tests

### Phase 4 (Data Providers & CLI)
- [ ] Fix lyrics provider tests (8 tests)
- [ ] Fix CLI tests (2 tests) 
- [ ] Fix transcriber tests (6 tests)
- [ ] Update `SKIP_PATTERNS` for completed tests

### Final Cleanup
- [ ] Remove all entries from `SKIP_PATTERNS` 
- [ ] Verify full test suite passes (447/447 tests)
- [ ] Clean up temporary test utilities if needed
- [ ] Update project documentation

## Key API Migration Patterns

### GapSequence Migration
```python
# Old Pattern (Broken)
gap = GapSequence(
    words=("hello", "world"),
    reference_words={"source": ["hello", "world"]}
)

# New Pattern (Fixed)
words = [create_test_word("w1", "hello", 0.0, 1.0), create_test_word("w2", "world", 1.0, 2.0)]
word_map = create_word_map(words)
gap = GapSequence(
    id="gap_1",
    transcribed_word_ids=["w1", "w2"], 
    reference_word_ids={"source": ["ref_w1", "ref_w2"]}
)
```

### Handler Testing Pattern
```python
# Tests need access to word_map for ID resolution
data = {"word_map": word_map}
can_handle, handler_data = handler.can_handle(gap, data)
corrections = handler.handle(gap, data)
```

## Success Metrics

- **Total Tests**: 447 → All passing
- **Skipped Tests**: 243 → 0
- **Test Coverage**: Maintain or improve current coverage
- **Performance**: No significant regression in test execution time
- **Maintainability**: Clear patterns established for future development

## Notes

- The `conftest.py` file contains the complete list of skipped patterns
- Some tests use `@pytest.mark.skip` decorators that also need removal
- Language model tests in `test_phrase_analyzer.py` may skip due to missing models (acceptable)
- Integration tests should be run separately to ensure end-to-end functionality 