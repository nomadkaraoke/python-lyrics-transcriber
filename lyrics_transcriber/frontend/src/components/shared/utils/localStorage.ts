import { CorrectionData, LyricsSegment } from '../../../types'

// Simple hash function for generating storage keys
export const generateStorageKey = (text: string): string => {
    let hash = 0
    for (let i = 0; i < text.length; i++) {
        const char = text.charCodeAt(i)
        hash = ((hash << 5) - hash) + char
        hash = hash & hash // Convert to 32-bit integer
    }
    return `song_${hash}`
}

const stripIds = (obj: CorrectionData): LyricsSegment[] => {
    const clone = JSON.parse(JSON.stringify(obj))
    return clone.corrected_segments.map((segment: LyricsSegment) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { id: _id, ...strippedSegment } = segment
        return {
            ...strippedSegment,
            words: segment.words.map(word => {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const { id: _wordId, ...strippedWord } = word
                return strippedWord
            })
        }
    })
}

export const loadSavedData = (initialData: CorrectionData): CorrectionData | null => {
    const storageKey = generateStorageKey(initialData.transcribed_text)
    const savedDataStr = localStorage.getItem('lyrics_analyzer_data')
    const savedDataObj = savedDataStr ? JSON.parse(savedDataStr) : {}

    if (savedDataObj[storageKey]) {
        try {
            const parsed = savedDataObj[storageKey]
            if (parsed.transcribed_text === initialData.transcribed_text) {
                const strippedSaved = stripIds(parsed)
                const strippedInitial = stripIds(initialData)
                const hasChanges = JSON.stringify(strippedSaved) !== JSON.stringify(strippedInitial)

                if (hasChanges) {
                    return parsed
                } else {
                    // Clean up storage if no changes
                    delete savedDataObj[storageKey]
                    localStorage.setItem('lyrics_analyzer_data', JSON.stringify(savedDataObj))
                }
            }
        } catch (error) {
            console.error('Failed to parse saved data:', error)
            delete savedDataObj[storageKey]
            localStorage.setItem('lyrics_analyzer_data', JSON.stringify(savedDataObj))
        }
    }
    return null
}

export const saveData = (data: CorrectionData, initialData: CorrectionData): void => {
    const storageKey = generateStorageKey(initialData.transcribed_text)
    const savedDataStr = localStorage.getItem('lyrics_analyzer_data')
    const savedDataObj = savedDataStr ? JSON.parse(savedDataStr) : {}

    savedDataObj[storageKey] = data
    localStorage.setItem('lyrics_analyzer_data', JSON.stringify(savedDataObj))
}

export const clearSavedData = (transcribedText: string): void => {
    const storageKey = generateStorageKey(transcribedText)
    const savedDataStr = localStorage.getItem('lyrics_analyzer_data')
    const savedDataObj = savedDataStr ? JSON.parse(savedDataStr) : {}

    delete savedDataObj[storageKey]
    localStorage.setItem('lyrics_analyzer_data', JSON.stringify(savedDataObj))
} 