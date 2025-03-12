import { useMemo } from 'react'
import { Paper, Typography, Box, IconButton } from '@mui/material'
import { ReferenceViewProps } from './shared/types'
import { calculateReferenceLinePositions } from './shared/utils/referenceLineCalculator'
import { SourceSelector } from './shared/components/SourceSelector'
import { HighlightedText } from './shared/components/HighlightedText'
import { TranscriptionWordPosition } from './shared/types'
import { getWordsFromIds } from './shared/utils/wordUtils'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { styled } from '@mui/material/styles'

const SegmentControls = styled(Box)({
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
    paddingTop: '1px',
    paddingRight: '4px'
})

const TextContainer = styled(Box)({
    flex: 1,
    minWidth: 0,
})

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
    corrections,
    onAddLyrics
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

    // Helper function to copy text to clipboard
    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    return (
        <Paper sx={{ p: 0.8, position: 'relative' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                <Typography variant="h6" sx={{ fontSize: '0.9rem', mb: 0 }}>
                    Reference Lyrics
                </Typography>
                <SourceSelector
                    availableSources={availableSources}
                    currentSource={effectiveCurrentSource}
                    onSourceChange={onSourceChange}
                    onAddLyrics={onAddLyrics}
                />
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.2 }}>
                {currentSourceSegments.map((segment, index) => (
                    <Box 
                        key={index} 
                        sx={{ 
                            display: 'flex', 
                            alignItems: 'flex-start', 
                            width: '100%', 
                            mb: 0,
                            '&:hover': {
                                backgroundColor: 'rgba(0, 0, 0, 0.03)'
                            }
                        }}
                    >
                        <SegmentControls>
                            <IconButton
                                size="small"
                                onClick={() => copyToClipboard(segment.words.map(w => w.text).join(' '))}
                                sx={{ 
                                    padding: '1px',
                                    height: '18px',
                                    width: '18px',
                                    minHeight: '18px',
                                    minWidth: '18px'
                                }}
                            >
                                <ContentCopyIcon sx={{ fontSize: '0.9rem' }} />
                            </IconButton>
                        </SegmentControls>
                        <TextContainer>
                            <HighlightedText
                                wordPositions={referenceWordPositions.filter(wp => 
                                    segment.words.some(w => w.id === wp.word.id)
                                )}
                                segments={[segment]}
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
                        </TextContainer>
                    </Box>
                ))}
            </Box>
        </Paper>
    )
} 