import React from 'react'
import { COLORS } from '../constants'
import { HighlightedWord } from '../styles'
import { WordProps } from '../types'

export const Word = React.memo(function Word({
    word,
    shouldFlash,
    isAnchor,
    isCorrectedGap,
    isUncorrectedGap,
    isCurrentlyPlaying,
    padding = '2px 4px',
    onClick,
}: WordProps) {
    if (/^\s+$/.test(word)) {
        return word
    }

    const backgroundColor = isCurrentlyPlaying
        ? COLORS.playing
        : shouldFlash
            ? COLORS.highlighted
            : isAnchor
                ? COLORS.anchor
                : isCorrectedGap
                    ? COLORS.corrected
                    : isUncorrectedGap
                        ? COLORS.uncorrectedGap
                        : 'transparent'

    return (
        <HighlightedWord
            shouldFlash={shouldFlash}
            style={{
                backgroundColor,
                padding,
                cursor: 'pointer',
                borderRadius: '3px',
                color: isCurrentlyPlaying ? '#ffffff' : 'inherit',
            }}
            sx={{
                '&:hover': {
                    backgroundColor: '#e0e0e0'
                }
            }}
            onClick={onClick}
        >
            {word}
        </HighlightedWord>
    )
}) 