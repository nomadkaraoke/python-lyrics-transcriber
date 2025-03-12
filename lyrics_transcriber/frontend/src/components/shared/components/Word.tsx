import React from 'react'
import { COLORS } from '../constants'
import { HighlightedWord } from '../styles'
import { WordProps } from '../types'
import { Tooltip } from '@mui/material'

export const WordComponent = React.memo(function Word({
    word,
    shouldFlash,
    isAnchor,
    isCorrectedGap,
    isUncorrectedGap,
    isCurrentlyPlaying,
    padding = '1px 3px',
    onClick,
    correction
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

    const wordElement = (
        <HighlightedWord
            shouldFlash={shouldFlash}
            style={{
                backgroundColor,
                padding,
                cursor: 'pointer',
                borderRadius: '2px',
                color: isCurrentlyPlaying ? '#ffffff' : 'inherit',
                textDecoration: correction ? 'underline dotted' : 'none',
                textDecorationColor: correction ? '#666' : 'inherit',
                textUnderlineOffset: '2px',
                fontSize: '0.85rem',
                lineHeight: 1.2
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

    if (correction) {
        const tooltipContent = (
            <>
                <strong>Original:</strong> "{correction.originalWord}"<br />
                <strong>Corrected by:</strong> {correction.handler}<br />
                <strong>Source:</strong> {correction.source}
            </>
        )
        
        return (
            <Tooltip title={tooltipContent} arrow placement="top">
                {wordElement}
            </Tooltip>
        )
    }

    return wordElement
}) 