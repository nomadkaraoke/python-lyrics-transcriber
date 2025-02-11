import { AnchorSequence, LyricsSegment, Word } from '../../../types'
import { LinePosition } from '../types'

export function calculateReferenceLinePositions(
    corrected_segments: LyricsSegment[],
    anchors: AnchorSequence[],
    currentSource: string
): { linePositions: LinePosition[] } {
    const linePositions: LinePosition[] = []
    let currentReferencePosition = 0

    // First, find all anchor sequences that cover entire lines
    const fullLineAnchors = anchors?.map(anchor => {
        // Check if we have reference words for this source
        const referenceWords = anchor.reference_words[currentSource]
        if (!referenceWords?.length) return null

        // Get the IDs of reference words
        const referenceWordIds = referenceWords.map((w: Word) => w.id)
        if (!referenceWordIds.length) return null

        return {
            referenceWordIds,
            transcriptionLine: corrected_segments.findIndex((segment) => {
                const wordIds = segment.words.map(w => w.id)
                if (!wordIds.length) return false

                // Check if all word IDs in this segment are part of the anchor's transcribed words
                return wordIds.every(id =>
                    anchor.transcribed_words.some(w => w.id === id)
                )
            })
        }
    })?.filter((a): a is NonNullable<typeof a> => a !== null) ?? []

    // Sort by first reference word ID to process in order
    fullLineAnchors.sort((a, b) => {
        const firstIdA = a.referenceWordIds[0]
        const firstIdB = b.referenceWordIds[0]
        return firstIdA.localeCompare(firstIdB)
    })

    // Add line positions with padding
    let currentLine = 0
    fullLineAnchors.forEach(anchor => {
        // Add empty lines if needed to match transcription line number
        while (currentLine < anchor.transcriptionLine) {
            linePositions.push({
                position: currentReferencePosition,
                lineNumber: currentLine,
                isEmpty: false
            })
            currentReferencePosition += 1
            currentLine++
        }

        // Add the actual line position
        linePositions.push({
            position: currentReferencePosition,
            lineNumber: currentLine,
            isEmpty: false
        })
        currentLine++
        currentReferencePosition++
    })

    // Add any remaining lines after the last anchor
    while (currentLine < corrected_segments.length) {
        linePositions.push({
            position: currentReferencePosition,
            lineNumber: currentLine,
            isEmpty: false
        })
        currentReferencePosition += 1
        currentLine++
    }

    return { linePositions }
} 