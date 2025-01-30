import { AnchorSequence, GapSequence, LyricsData } from '../../../types'
import { TranscriptionWordPosition } from '../types'

export function calculateWordPositions(data: LyricsData): TranscriptionWordPosition[] {
    const wordPositions: TranscriptionWordPosition[] = []
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

        const anchor = findAnchorForPosition(data.anchor_sequences, wordIndex)
        const gap = !anchor ? findGapForPosition(data.gap_sequences, wordIndex) : undefined

        wordPositions.push({
            word,
            position: wordIndex,
            type: anchor ? 'anchor' : gap ? 'gap' : 'other',
            sequence: anchor || gap,
            isInRange: isWordInSequenceRange(normalizedWord, wordIndex, anchor || gap)
        })

        wordIndex++
    })

    return wordPositions
}

// Helper functions
function normalizeWord(word: string): string {
    return word.toLowerCase().replace(/[.,!?']|'s\b/g, '')
}

function findAnchorForPosition(
    anchors: AnchorSequence[],
    position: number,
): AnchorSequence | undefined {
    return anchors.find(anchor =>
        position >= anchor.transcription_position &&
        position < anchor.transcription_position + anchor.length
    )
}

function findGapForPosition(
    gaps: GapSequence[],
    position: number,
): GapSequence | undefined {
    return gaps.find(gap =>
        position >= gap.transcription_position &&
        position < gap.transcription_position + gap.length
    )
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