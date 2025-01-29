import { AnchorSequence, GapSequence, CorrectionData } from '../../../types'
import { WordPosition } from '../types'

export function calculateWordPositions(data: CorrectionData): WordPosition[] {
    const wordPositions: WordPosition[] = []

    // Split text into words and whitespace, preserving all separators
    const words = data.corrected_text.split(/(\s+)/g)

    let wordIndex = 0
    let lastWasNewline = false

    words.forEach((word) => {
        // Handle whitespace
        if (/^\s+$/.test(word)) {
            // Check if this is a newline
            if (word.includes('\n')) {
                // Only add a single newline, avoid duplicates
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
            } else {
                // For non-newline whitespace, just add a single space
                if (!lastWasNewline) {
                    wordPositions.push({
                        word: ' ',
                        position: -1,
                        type: 'other',
                        sequence: undefined,
                        isInRange: false
                    })
                }
            }
            return
        }

        // Reset newline flag when we hit a word
        lastWasNewline = false

        const position = wordIndex
        const anchor = findAnchorForPosition(data.anchor_sequences, position, word)
        const gap = !anchor ? findGapForPosition(data.gap_sequences, position, word) : undefined

        wordPositions.push({
            word,
            position,
            type: anchor ? 'anchor' : gap ? 'gap' : 'other',
            sequence: anchor || gap,
            isInRange: isWordInSequenceRange(word, position, anchor || gap)
        })

        wordIndex++
    })

    return wordPositions
}

function findAnchorForPosition(
    anchors: AnchorSequence[],
    position: number,
    word: string
): AnchorSequence | undefined {
    return anchors.find(anchor => {
        const start = anchor.transcription_position
        const wordIndex = anchor.words.indexOf(word)

        if (wordIndex === -1) return false

        const expectedPosition = start + wordIndex
        return Math.abs(expectedPosition - position) <= 1 // Allow 1 position wiggle room
    })
}

function findGapForPosition(
    gaps: GapSequence[],
    position: number,
    word: string
): GapSequence | undefined {
    return gaps.find(gap => {
        const start = gap.transcription_position
        const end = start + gap.length
        return position >= start && position < end && gap.words.includes(word)
    })
}

function isWordInSequenceRange(
    word: string,
    position: number,
    sequence?: AnchorSequence | GapSequence
): boolean {
    if (!sequence) return false

    const start = sequence.transcription_position
    const end = start + sequence.length
    const wordIndex = sequence.words.indexOf(word)

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
    console.group(`Position debug for "${word}" at position ${position}`)

    const matchingAnchor = findAnchorForPosition(anchors, position, word)
    const matchingGap = !matchingAnchor ? findGapForPosition(gaps, position, word) : undefined

    console.log('Match results:', {
        word,
        position,
        inAnchor: matchingAnchor ? {
            text: matchingAnchor.text,
            start: matchingAnchor.transcription_position,
            wordIndex: matchingAnchor.words.indexOf(word),
            expectedPosition: matchingAnchor.transcription_position + matchingAnchor.words.indexOf(word)
        } : null,
        inGap: matchingGap ? {
            text: matchingGap.text,
            start: matchingGap.transcription_position,
            wordIndex: matchingGap.words.indexOf(word)
        } : null
    })

    console.groupEnd()
} 