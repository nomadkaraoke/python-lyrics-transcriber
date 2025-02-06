import { useMemo } from 'react'
import { Paper, Typography, Box } from '@mui/material'
import { ReferenceViewProps } from './shared/types'
import { calculateReferenceLinePositions } from './shared/utils/referenceLineCalculator'
import { SourceSelector } from './shared/components/SourceSelector'
import { HighlightedText } from './shared/components/HighlightedText'
import { WordCorrection } from '@/types'

export default function ReferenceView({
    referenceTexts,
    anchors,
    onElementClick,
    onWordClick,
    flashingType,
    corrected_segments,
    currentSource,
    onSourceChange,
    highlightInfo,
    mode,
    gaps
}: ReferenceViewProps) {
    // Get available sources from referenceTexts object
    const availableSources = useMemo(() =>
        Object.keys(referenceTexts) as Array<string>,
        [referenceTexts]
    )

    const { linePositions } = useMemo(() =>
        calculateReferenceLinePositions(
            corrected_segments,
            anchors,
            currentSource
        ),
        [corrected_segments, anchors, currentSource]
    )

    // Create a mapping of reference words to their corrections
    const referenceCorrections = useMemo(() => {
        const corrections = new Map<string, string>();

        console.log('Building referenceCorrections map:', {
            gapsCount: gaps.length,
            currentSource,
        });

        gaps.forEach(gap => {
            gap.corrections.forEach((correction: WordCorrection) => {
                // Get the reference position for this correction
                const referencePosition = correction.reference_positions?.[currentSource];

                if (typeof referencePosition === 'number') {
                    const wordId = `${currentSource}-word-${referencePosition}`;
                    corrections.set(wordId, correction.corrected_word);

                    console.log('Adding correction mapping:', {
                        wordId,
                        correctedWord: correction.corrected_word,
                        referencePosition,
                        correction
                    });
                }
            });
        });

        console.log('Final referenceCorrections map:', {
            size: corrections.size,
            entries: Array.from(corrections.entries())
        });

        return corrections;
    }, [gaps, currentSource]);

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    Reference Text
                </Typography>
                <SourceSelector
                    currentSource={currentSource}
                    onSourceChange={onSourceChange}
                    availableSources={availableSources}
                />
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <HighlightedText
                    text={referenceTexts[currentSource]}
                    anchors={anchors}
                    onElementClick={onElementClick}
                    onWordClick={onWordClick}
                    flashingType={flashingType}
                    highlightInfo={highlightInfo}
                    mode={mode}
                    isReference={true}
                    currentSource={currentSource}
                    linePositions={linePositions}
                    referenceCorrections={referenceCorrections}
                    gaps={gaps}
                />
            </Box>
        </Paper>
    )
} 