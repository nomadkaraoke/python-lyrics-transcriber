import { describe, it, expect } from 'vitest'
import { validateCorrectionData } from './validation'

describe('Frontend Validation', () => {
  describe('validateCorrectionData', () => {
    it('should validate correct correction data structure', () => {
      const validCorrectionData = {
        original_segments: [],
        reference_lyrics: {},
        anchor_sequences: [],
        gap_sequences: [],
        resized_segments: [],
        corrections_made: 0,
        confidence: 0.95,
        corrections: [],
        corrected_segments: [],
        metadata: {
          anchor_sequences_count: 0,
          gap_sequences_count: 0,
          total_words: 0,
          correction_ratio: 0.0
        },
        correction_steps: [],
        word_id_map: {},
        segment_id_map: {}
      }

      expect(() => validateCorrectionData(validCorrectionData)).not.toThrow()
    })

    it('should reject invalid correction data structure', () => {
      const invalidCorrectionData = {
        // Missing required fields
        original_segments: [],
        // Missing other required fields...
      }

      expect(() => validateCorrectionData(invalidCorrectionData)).toThrow()
    })

    it('should validate anchor sequence with correct format', () => {
      const validCorrectionData = {
        original_segments: [],
        reference_lyrics: {},
        anchor_sequences: [{
          id: "anchor-1",
          transcribed_word_ids: ["word1", "word2"],
          transcription_position: 0,
          reference_positions: { "source1": 0 },
          reference_word_ids: { "source1": ["ref1", "ref2"] },
          confidence: 0.9,
          phrase_score: {
            phrase_type: "complete",
            natural_break_score: 0.8,
            length_score: 0.7,
            total_score: 0.75
          },
          total_score: 0.85
        }],
        gap_sequences: [],
        resized_segments: [],
        corrections_made: 0,
        confidence: 0.95,
        corrections: [],
        corrected_segments: [],
        metadata: {
          anchor_sequences_count: 1,
          gap_sequences_count: 0,
          total_words: 2,
          correction_ratio: 0.0
        },
        correction_steps: [],
        word_id_map: {},
        segment_id_map: {}
      }

      expect(() => validateCorrectionData(validCorrectionData)).not.toThrow()
    })

    it('should reject anchor sequence with old format fields', () => {
      const invalidCorrectionData = {
        original_segments: [],
        reference_lyrics: {},
        anchor_sequences: [{
          // Old format - should be rejected
          words: ["hello", "world"],
          text: "hello world",
          length: 2,
          transcription_position: 0,
          reference_positions: { "source1": 0 },
          confidence: 0.9
        }],
        gap_sequences: [],
        resized_segments: [],
        corrections_made: 0,
        confidence: 0.95,
        corrections: [],
        corrected_segments: [],
        metadata: {
          anchor_sequences_count: 1,
          gap_sequences_count: 0,
          total_words: 2,
          correction_ratio: 0.0
        },
        correction_steps: [],
        word_id_map: {},
        segment_id_map: {}
      }

      expect(() => validateCorrectionData(invalidCorrectionData)).toThrow()
    })
  })
}) 