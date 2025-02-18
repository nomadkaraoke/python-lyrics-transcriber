import { useMemo } from 'react'
import { Paper, Typography, Box } from '@mui/material'
import { ReferenceViewProps } from './shared/types'
import { calculateReferenceLinePositions } from './shared/utils/referenceLineCalculator'
import { SourceSelector } from './shared/components/SourceSelector'
import { HighlightedText } from './shared/components/HighlightedText'
import { TranscriptionWordPosition } from './shared/types'
import { getWordsFromIds } from './shared/utils/wordUtils'

export default function ReferenceView({
    referenceSources,
    anchors,
    onElementClick,
    onWordClick,
    flashingType,
    corrected_segments,
    currentSource,
    onSourceChange,
    highlightInfo,
    mode,
    gaps,
    corrections
}: ReferenceViewProps) {
    // Get available sources from referenceSources object
    const availableSources = useMemo(() =>
        Object.keys(referenceSources),
        [referenceSources]
    )

    // Ensure we always have a valid currentSource
    const effectiveCurrentSource = useMemo(() =>
        currentSource || (availableSources.length > 0 ? availableSources[0] : ''),
        [currentSource, availableSources]
    )

    // Create word positions for the reference view
    const referenceWordPositions = useMemo(() => {
        const positions: TranscriptionWordPosition[] = [];
        const allPositions = new Map<number, TranscriptionWordPosition[]>();

        // Map anchor words
        anchors?.forEach(anchor => {
            const position = anchor.reference_positions[effectiveCurrentSource];
            if (position === undefined) return;

            if (!allPositions.has(position)) {
                allPositions.set(position, []);
            }

            const referenceWords = getWordsFromIds(
                referenceSources[effectiveCurrentSource].segments,
                anchor.reference_word_ids[effectiveCurrentSource] || []
            );

            referenceWords.forEach(word => {
                const wordPosition: TranscriptionWordPosition = {
                    word: {
                        id: word.id,
                        text: word.text,
                        start_time: word.start_time ?? undefined,
                        end_time: word.end_time ?? undefined
                    },
                    type: 'anchor',
                    sequence: anchor,
                    isInRange: true
                };
                allPositions.get(position)!.push(wordPosition);
            });
        });

        // Map gap words
        gaps?.forEach(gap => {
            const precedingAnchor = gap.preceding_anchor_id ?
                anchors?.find(a => a.id === gap.preceding_anchor_id) :
                undefined;
            const followingAnchor = gap.following_anchor_id ?
                anchors?.find(a => a.id === gap.following_anchor_id) :
                undefined;

            const position = precedingAnchor?.reference_positions[effectiveCurrentSource] ??
                followingAnchor?.reference_positions[effectiveCurrentSource];

            if (position === undefined) return;

            const gapPosition = precedingAnchor ? position + 1 : position - 1;

            if (!allPositions.has(gapPosition)) {
                allPositions.set(gapPosition, []);
            }

            const referenceWords = getWordsFromIds(
                referenceSources[effectiveCurrentSource].segments,
                gap.reference_word_ids[effectiveCurrentSource] || []
            );

            referenceWords.forEach(word => {
                // Find if this word has a correction
                const isWordCorrected = corrections?.some(correction =>
                    correction.reference_positions?.[effectiveCurrentSource]?.toString() === word.id &&
                    gap.transcribed_word_ids.includes(correction.word_id)
                );

                const wordPosition: TranscriptionWordPosition = {
                    word: {
                        id: word.id,
                        text: word.text,
                        start_time: word.start_time ?? undefined,
                        end_time: word.end_time ?? undefined
                    },
                    type: 'gap',
                    sequence: gap,
                    isInRange: true,
                    isCorrected: isWordCorrected
                };
                allPositions.get(gapPosition)!.push(wordPosition);
            });
        });

        // Sort by position and flatten
        Array.from(allPositions.entries())
            .sort(([a], [b]) => a - b)
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            .forEach(([_, words]) => {
                positions.push(...words);
            });

        return positions;
    }, [anchors, gaps, effectiveCurrentSource, referenceSources, corrections]);

    const { linePositions } = useMemo(() =>
        calculateReferenceLinePositions(
            corrected_segments,
            anchors,
            effectiveCurrentSource
        ),
        [corrected_segments, anchors, effectiveCurrentSource]
    )

    // Create a mapping of reference words to their corrections
    const referenceCorrections = useMemo(() => {
        const correctionMap = new Map<string, string>();

        corrections?.forEach(correction => {
            const referencePosition = correction.reference_positions?.[effectiveCurrentSource];
            if (referencePosition !== undefined) {
                correctionMap.set(referencePosition.toString(), correction.corrected_word);
            }
        });

        return correctionMap;
    }, [corrections, effectiveCurrentSource]);

    // Get the segments for the current source
    const currentSourceSegments = referenceSources[effectiveCurrentSource]?.segments || [];

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    Reference Text
                </Typography>
                <SourceSelector
                    currentSource={effectiveCurrentSource}
                    onSourceChange={onSourceChange}
                    availableSources={availableSources}
                />
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                <HighlightedText
                    wordPositions={referenceWordPositions}
                    segments={currentSourceSegments}
                    anchors={anchors}
                    onElementClick={onElementClick}
                    onWordClick={onWordClick}
                    flashingType={flashingType}
                    highlightInfo={highlightInfo}
                    mode={mode}
                    isReference={true}
                    currentSource={effectiveCurrentSource}
                    linePositions={linePositions}
                    referenceCorrections={referenceCorrections}
                    gaps={gaps}
                    preserveSegments={true}
                />
            </Box>
        </Paper>
    )
} 