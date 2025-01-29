import React from 'react'
import { HighlightedWord } from '../../styles'
import { COLORS } from '../../constants'
import { WordProps } from '../types'
import { getRelativePosition } from '../utils/positionCalculator'

declare global {
    interface Window {
        _debugWord?: string;
    }
}

export function Word({
    word,
    position,
    anchor,
    gap,
    shouldFlash,
    onClick,
    onDoubleClick
}: WordProps) {
    const belongsToAnchor = anchor && anchor.words.includes(word)
    const belongsToGap = gap && gap.words.includes(word)
    const hasCorrections = Boolean(gap?.corrections?.length)

    const getBackgroundColor = () => {
        if (belongsToAnchor) return COLORS.anchor
        if (hasCorrections) return COLORS.corrected
        if (belongsToGap) return COLORS.uncorrectedGap
        return 'transparent'
    }

    const handleSingleClick = (e: React.MouseEvent) => {
        if (e.detail === 1) {
            // Use setTimeout to handle single click without interfering with double click
            setTimeout(() => {
                if (!e.defaultPrevented) {
                    onClick(e)
                }
            }, 200)
        }
    }

    const handleDoubleClick = (e: React.MouseEvent) => {
        e.preventDefault()
        onDoubleClick(e)
    }

    // Debug word position when needed
    const debugWord = () => {
        if (window._debugWord === word) {
            console.group(`Word component debug for "${word}"`)
            console.log({
                position,
                belongsToAnchor,
                belongsToGap,
                hasCorrections,
                anchorPosition: anchor?.transcription_position,
                gapPosition: gap?.transcription_position,
                relativePosition: anchor 
                    ? getRelativePosition(position, anchor)
                    : gap 
                        ? getRelativePosition(position, gap)
                        : null
            })
            console.groupEnd()
        }
    }

    // Call debug function
    React.useEffect(debugWord, [word, position, anchor, gap])

    return (
        <HighlightedWord
            shouldFlash={shouldFlash}
            style={{
                backgroundColor: getBackgroundColor(),
                padding: (belongsToAnchor || belongsToGap) ? '2px 4px' : '0',
                borderRadius: '3px',
                cursor: 'pointer',
            }}
            onClick={handleSingleClick}
            onDoubleClick={handleDoubleClick}
        >
            {word}
        </HighlightedWord>
    )
}

// Memoize the component to prevent unnecessary re-renders
export default React.memo(Word) 