import { AnchorSequence, GapSequence, CorrectionData } from '../../../types'
import { WordPosition } from '../types'

export function calculateWordPositions(data: CorrectionData): WordPosition[] {
    const wordPositions: WordPosition[] = []
    const words = data.corrected_text.split(/(\s+)/g)
    let wordIndex = 0
    let lastWasNewline = false

    words.forEach((word) => {
        // Skip empty strings from the split
        if (word === '') return

        // Handle whitespace
        if (/^\s+$/.test(word)) {
            if (word.includes('\n')) {
                if (!lastWasNewline) {
                    wordPositions.push({
                        word: '\n',
                        position: -1,
                        type: 'other',
                        sequence: undefined,
                        isInRange: false
                    })
                    lastWasNewline = true
                }
            } else if (!lastWasNewline) {
                wordPositions.push({
                    word: ' ',
                    position: -1,
                    type: 'other',
                    sequence: undefined,
                    isInRange: false
                })
            }
            return
        }

        lastWasNewline = false
        const normalizedWord = normalizeWord(word)

        const anchor = findAnchorForPosition(data.anchor_sequences, wordIndex, normalizedWord)
        const gap = !anchor ? findGapForPosition(data.gap_sequences, wordIndex, normalizedWord) : undefined

        wordPositions.push({
            word,
            position: wordIndex,
            type: anchor ? 'anchor' : gap ? 'gap' : 'other',
            sequence: anchor || gap,
            isInRange: isWordInSequenceRange(normalizedWord, wordIndex, anchor || gap)
        })

        wordIndex++
    })

    // Run sanity checks after calculating positions
    sanityCheckAnchors(wordPositions, data.anchor_sequences)

    return wordPositions
}

// Helper function to normalize words for comparison
function normalizeWord(word: string): string {
    return word.toLowerCase().replace(/[.,!?']|'s\b/g, '')
}

function findAnchorForPosition(
    anchors: AnchorSequence[],
    position: number,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _word: string  // Keep parameter for API compatibility but don't use it
): AnchorSequence | undefined {
    for (const anchor of anchors) {
        const start = anchor.transcription_position
        const end = start + anchor.length

        // Only check if position is in range
        if (position >= start && position < end) {
            return anchor
        }
    }

    return undefined
}

// Similarly simplify findGapForPosition
function findGapForPosition(
    gaps: GapSequence[],
    position: number,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _word: string  // Keep parameter for API compatibility but don't use it
): GapSequence | undefined {
    for (const gap of gaps) {
        const start = gap.transcription_position
        const end = start + gap.length

        if (position >= start && position < end) {
            return gap
        }
    }

    return undefined
}

function isWordInSequenceRange(
    word: string,
    position: number,
    sequence?: AnchorSequence | GapSequence
): boolean {
    if (!sequence) return false

    const start = sequence.transcription_position
    const end = start + sequence.length
    const normalizedWord = normalizeWord(word)
    const wordIndex = sequence.words.findIndex(w => normalizeWord(w) === normalizedWord)

    return wordIndex !== -1 && position >= start && position < end
}

export function getRelativePosition(
    absolutePosition: number,
    sequence: AnchorSequence | GapSequence
): number {
    return absolutePosition - sequence.transcription_position
}

export function debugWordPosition(
    word: string,
    position: number,
    anchors: AnchorSequence[],
    gaps: GapSequence[]
): void {
    const normalizedWord = normalizeWord(word)

    // Find matching sequences
    const matchingAnchor = findAnchorForPosition(anchors, position, word)
    const matchingGap = !matchingAnchor ? findGapForPosition(gaps, position, word) : undefined

    // Find sequences that contain this position
    const containingSequences = {
        anchors: anchors
            .filter(a => position >= a.transcription_position && position < (a.transcription_position + a.length))
            .map(a => ({
                start: a.transcription_position,
                length: a.length,
                end: a.transcription_position + a.length,
                words: a.words,
                relativePosition: position - a.transcription_position,
                referencePositions: a.reference_positions,
                confidence: a.confidence,
                totalScore: a.total_score
            })),
        gaps: gaps
            .filter(g => position >= g.transcription_position && position < (g.transcription_position + g.length))
            .map(g => ({
                start: g.transcription_position,
                length: g.length,
                end: g.transcription_position + g.length,
                words: g.words,
                relativePosition: position - g.transcription_position
            }))
    }

    // Add highlight info debug
    const highlightInfo = matchingAnchor ? {
        type: 'anchor' as const,
        transcriptionIndex: matchingAnchor.transcription_position,
        transcriptionLength: matchingAnchor.length,
        referenceIndices: matchingAnchor.reference_positions,
        referenceLength: matchingAnchor.length
    } : matchingGap ? {
        type: 'gap' as const,
        transcriptionIndex: matchingGap.transcription_position,
        transcriptionLength: matchingGap.length,
        referenceIndices: {},
        referenceLength: matchingGap.length
    } : null

    console.log(JSON.stringify({
        clicked: {
            word,
            position,
            normalized: normalizedWord,
            type: matchingAnchor ? 'anchor' : matchingGap ? 'gap' : 'other'
        },
        matching: {
            anchor: matchingAnchor ? {
                start: matchingAnchor.transcription_position,
                length: matchingAnchor.length,
                words: matchingAnchor.words,
                referencePositions: matchingAnchor.reference_positions,
                confidence: matchingAnchor.confidence,
                totalScore: matchingAnchor.total_score
            } : null,
            gap: matchingGap ? {
                start: matchingGap.transcription_position,
                length: matchingGap.length,
                words: matchingGap.words
            } : null
        },
        containing_sequences: containingSequences,
        highlight_info: highlightInfo,
        // Add the first few words of each sequence for context
        sequence_context: {
            anchors: anchors.slice(0, 3).map(a => ({
                start: a.transcription_position,
                length: a.length,
                words: a.words.slice(0, 5),
                referencePositions: a.reference_positions
            }))
        }
    }, null, 2))
}

function sanityCheckAnchors(
    wordPositions: WordPosition[],
    anchors: AnchorSequence[]
): void {
    anchors.forEach((anchor, anchorIndex) => {
        const start = anchor.transcription_position
        const expectedWords = anchor.words.map(normalizeWord)
        const actualWords = wordPositions
            .filter(wp => wp.position >= start && wp.position < start + anchor.length)
            .map(wp => normalizeWord(wp.word))

        const mismatches = expectedWords.filter((word, i) => {
            const actualWord = actualWords[i]
            return actualWord !== word
        })

        const unclaimedWords = wordPositions
            .filter(wp =>
                wp.position >= start &&
                wp.position < start + anchor.length &&
                wp.type !== 'anchor'
            )

        if (mismatches.length > 0 || unclaimedWords.length > 0) {
            console.log(`Anchor ${anchorIndex} (position ${start}):`, {
                expectedLength: anchor.length,
                actualLength: actualWords.length,
                mismatches: mismatches.length > 0 ? mismatches : undefined,
                unclaimedWords: unclaimedWords.length > 0 ?
                    unclaimedWords.map(w => ({
                        word: w.word,
                        normalizedWord: normalizeWord(w.word),
                        position: w.position,
                        type: w.type
                    })) :
                    undefined
            })
        }
    })
} 