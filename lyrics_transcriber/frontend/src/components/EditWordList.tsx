import {
    Box,
    TextField,
    IconButton,
    Button,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import SplitIcon from '@mui/icons-material/CallSplit'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import { Word } from '../types'
import { useState, memo } from 'react'
import WordDivider from './WordDivider'

interface EditWordListProps {
    words: Word[]
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    onSplitWord: (index: number) => void
    onMergeWords: (index: number) => void
    onAddWord: (index?: number) => void
    onRemoveWord: (index: number) => void
    onSplitSegment?: (wordIndex: number) => void
    onAddSegment?: (beforeIndex: number) => void
    onMergeSegment?: (mergeWithNext: boolean) => void
    isGlobal?: boolean
}

// Create a memoized word row component to prevent re-renders
const WordRow = memo(function WordRow({
    word,
    index,
    onWordUpdate,
    onSplitWord,
    onRemoveWord,
    wordsLength
}: {
    word: Word
    index: number
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    onSplitWord: (index: number) => void
    onRemoveWord: (index: number) => void
    wordsLength: number
}) {
    return (
        <Box sx={{
            display: 'flex',
            gap: 2,
            alignItems: 'center',
        }}>
            <TextField
                label={`Word ${index}`}
                value={word.text}
                onChange={(e) => onWordUpdate(index, { text: e.target.value })}
                fullWidth
                size="small"
            />
            <TextField
                label="Start Time"
                value={word.start_time?.toFixed(2) ?? ''}
                onChange={(e) => onWordUpdate(index, { start_time: parseFloat(e.target.value) })}
                type="number"
                inputProps={{ step: 0.01 }}
                sx={{ width: '150px' }}
                size="small"
            />
            <TextField
                label="End Time"
                value={word.end_time?.toFixed(2) ?? ''}
                onChange={(e) => onWordUpdate(index, { end_time: parseFloat(e.target.value) })}
                type="number"
                inputProps={{ step: 0.01 }}
                sx={{ width: '150px' }}
                size="small"
            />
            <IconButton
                onClick={() => onSplitWord(index)}
                title="Split Word"
                sx={{ color: 'primary.main' }}
                size="small"
            >
                <SplitIcon fontSize="small" />
            </IconButton>
            <IconButton
                onClick={() => onRemoveWord(index)}
                disabled={wordsLength <= 1}
                title="Remove Word"
                sx={{ color: 'error.main' }}
                size="small"
            >
                <DeleteIcon fontSize="small" />
            </IconButton>
        </Box>
    );
});

export default function EditWordList({
    words,
    onWordUpdate,
    onSplitWord,
    onMergeWords,
    onAddWord,
    onRemoveWord,
    onSplitSegment,
    onAddSegment,
    onMergeSegment,
    isGlobal = false
}: EditWordListProps) {
    const [replacementText, setReplacementText] = useState('')

    const handleReplaceAllWords = () => {
        const newWords = replacementText.trim().split(/\s+/)
        newWords.forEach((text, index) => {
            if (index < words.length) {
                onWordUpdate(index, { text })
            }
        })
        setReplacementText('')
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flexGrow: 1, minHeight: 0 }}>
            <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5,
                flexGrow: 1,
                overflowY: 'auto',
                mb: 0,
                pt: 1,
                '&::-webkit-scrollbar': {
                    width: '8px',
                },
                '&::-webkit-scrollbar-thumb': {
                    backgroundColor: 'rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                },
                scrollbarWidth: 'thin',
                msOverflowStyle: 'autohiding-scrollbar',
            }}>
                {/* Initial divider with Add Segment Before button */}
                {!isGlobal && (
                    <WordDivider
                        onAddWord={() => onAddWord(-1)}
                        onAddSegmentBefore={() => onAddSegment?.(0)}
                        onMergeSegment={() => onMergeSegment?.(false)}
                        isFirst={true}
                        sx={{ ml: 15 }}
                    />
                )}
                {isGlobal && (
                    <WordDivider
                        onAddWord={() => onAddWord(-1)}
                        sx={{ ml: 15 }}
                    />
                )}

                {words.map((word, index) => (
                    <Box key={word.id}>
                        <WordRow
                            word={word}
                            index={index}
                            onWordUpdate={onWordUpdate}
                            onSplitWord={onSplitWord}
                            onRemoveWord={onRemoveWord}
                            wordsLength={words.length}
                        />

                        {/* Word divider with merge/split functionality */}
                        {!isGlobal && (
                            <WordDivider
                                onAddWord={() => onAddWord(index)}
                                onMergeWords={() => onMergeWords(index)}
                                onSplitSegment={() => onSplitSegment?.(index)}
                                onAddSegmentAfter={
                                    index === words.length - 1
                                        ? () => onAddSegment?.(index + 1)
                                        : undefined
                                }
                                onMergeSegment={
                                    index === words.length - 1
                                        ? () => onMergeSegment?.(true)
                                        : undefined
                                }
                                canMerge={index < words.length - 1}
                                isLast={index === words.length - 1}
                                sx={{ ml: 15 }}
                            />
                        )}
                        {isGlobal && (
                            <WordDivider
                                onAddWord={() => onAddWord(index)}
                                onMergeWords={index < words.length - 1 ? () => onMergeWords(index) : undefined}
                                canMerge={index < words.length - 1}
                                sx={{ ml: 15 }}
                            />
                        )}
                    </Box>
                ))}
            </Box>

            <Box sx={{ display: 'flex', gap: 2, mb: 0.6 }}>
                <TextField
                    value={replacementText}
                    onChange={(e) => setReplacementText(e.target.value)}
                    placeholder="Replace all words"
                    size="small"
                    sx={{ flexGrow: 1, maxWidth: 'calc(100% - 140px)' }}
                />
                <Button
                    onClick={handleReplaceAllWords}
                    startIcon={<AutoFixHighIcon />}
                    size="small"
                    sx={{ whiteSpace: 'nowrap' }}
                >
                    Replace All
                </Button>
            </Box>
        </Box>
    )
} 