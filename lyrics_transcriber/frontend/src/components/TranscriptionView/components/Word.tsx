import React from 'react';
import { COLORS } from '../../constants';
import { HighlightedWord } from '../../styles';

interface WordProps {
    word: string;
    shouldFlash: boolean;
    isAnchor?: boolean;
    isCorrectedGap?: boolean;
    padding?: string;
    onClick?: () => void;
    onDoubleClick?: (e: React.MouseEvent) => void;
}

export const Word = React.memo(function Word({
    word,
    shouldFlash,
    isAnchor,
    isCorrectedGap,
    padding = '2px 0',
    onClick,
    onDoubleClick
}: WordProps) {
    if (/^\s+$/.test(word)) {
        return word;
    }

    const backgroundColor = shouldFlash
        ? COLORS.highlighted
        : isAnchor
            ? COLORS.anchor
            : isCorrectedGap
                ? COLORS.corrected
                : 'transparent';

    return (
        <HighlightedWord
            shouldFlash={shouldFlash}
            style={{
                backgroundColor,
                padding,
                cursor: 'pointer',
                borderRadius: '3px'
            }}
            sx={{
                '&:hover': {
                    backgroundColor: '#e0e0e0'
                }
            }}
            onClick={onClick}
            onDoubleClick={onDoubleClick}
        >
            {word}
        </HighlightedWord>
    );
});

export default Word; 