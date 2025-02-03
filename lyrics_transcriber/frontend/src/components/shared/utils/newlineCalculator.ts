import { LyricsData, LyricsSegment } from '../../../types'

export function calculateNewlineIndices(
    corrected_segments: LyricsSegment[],
    anchors: LyricsData['anchor_sequences'],
    currentSource: string
): Set<number> {
    return new Set(
        corrected_segments.slice(0, -1).map((segment, segmentIndex) => {
            const segmentText = segment.text.trim()
            const segmentWords = segmentText.split(/\s+/)
            const segmentStartWord = corrected_segments
                .slice(0, segmentIndex)
                .reduce((acc, s) => acc + s.text.trim().split(/\s+/).length, 0)
            const lastWordPosition = segmentStartWord + segmentWords.length - 1

            const matchingAnchor = anchors.find(a => {
                const start = a.transcription_position
                const end = start + a.length - 1
                return lastWordPosition >= start && lastWordPosition <= end
            })

            if (matchingAnchor?.reference_positions[currentSource] !== undefined) {
                const anchorWords = matchingAnchor.words
                const wordIndex = anchorWords.findIndex(w =>
                    w.toLowerCase() === segmentWords[segmentWords.length - 1].toLowerCase()
                )

                if (wordIndex !== -1) {
                    return matchingAnchor.reference_positions[currentSource] + wordIndex
                }
            }

            return null
        }).filter((pos): pos is number => pos !== null && pos >= 0)
    )
} 