import { LyricsData, LyricsSegment } from '../../../types'
import { LinePosition } from '../types'

export function calculateReferenceLinePositions(
    corrected_segments: LyricsSegment[],
    anchors: LyricsData['anchor_sequences'],
    currentSource: string
): { linePositions: LinePosition[] } {
    const linePositions: LinePosition[] = []
    let currentReferencePosition = 0

    // First, find all anchor sequences that cover entire lines
    const fullLineAnchors = anchors.map(anchor => {
        const referencePos = anchor.reference_positions[currentSource]
        if (referencePos === undefined) return null

        return {
            referenceStart: referencePos,
            referenceLength: anchor.length,
            transcriptionLine: corrected_segments.findIndex((segment, segmentIndex) => {
                const words = segment.words
                if (!words.length) return false

                // Calculate the absolute position of the first and last words in this segment
                let absolutePosition = 0
                for (let i = 0; i < segmentIndex; i++) {
                    absolutePosition += corrected_segments[i].words.length
                }

                const firstWordPosition = absolutePosition
                const lastWordPosition = absolutePosition + words.length - 1

                return firstWordPosition >= anchor.transcription_position &&
                    lastWordPosition < anchor.transcription_position + anchor.length
            })
        }
    }).filter((a): a is NonNullable<typeof a> => a !== null)

    // Sort by reference position to process in order
    fullLineAnchors.sort((a, b) => a.referenceStart - b.referenceStart)

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
            position: anchor.referenceStart,
            lineNumber: currentLine
        })
        currentLine++
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