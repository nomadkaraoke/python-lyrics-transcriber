import {
    Box,
    TextField,
    IconButton,
    Button,
    Pagination,
    Typography
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import SplitIcon from '@mui/icons-material/CallSplit'
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh'
import { Word } from '../types'
import { useState, memo, useMemo } from 'react'
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
    wordsLength,
    onTabNavigation
}: {
    word: Word
    index: number
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    onSplitWord: (index: number) => void
    onRemoveWord: (index: number) => void
    wordsLength: number
    onTabNavigation: (currentIndex: number) => void
}) {
    const handleKeyDown = (e: React.KeyboardEvent) => {
        // console.log('KeyDown event:', e.key, 'Shift:', e.shiftKey, 'Index:', index);
        if (e.key === 'Tab' && !e.shiftKey) {
            // console.log('Tab key detected, preventing default and navigating');
            e.preventDefault();
            onTabNavigation(index);
        }
    };

    return (
        <Box sx={{
            display: 'flex',
            gap: 2,
            alignItems: 'center',
            padding: '4px 0',
        }}>
            <TextField
                label={`Word ${index}`}
                value={word.text}
                onChange={(e) => onWordUpdate(index, { text: e.target.value })}
                onKeyDown={handleKeyDown}
                fullWidth
                size="small"
                id={`word-text-${index}`}
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

// Memoized word item component that includes the word row and divider
const WordItem = memo(function WordItem({
    word,
    index,
    onWordUpdate,
    onSplitWord,
    onRemoveWord,
    onAddWord,
    onMergeWords,
    onSplitSegment,
    onAddSegment,
    onMergeSegment,
    wordsLength,
    isGlobal,
    onTabNavigation
}: {
    word: Word
    index: number
    onWordUpdate: (index: number, updates: Partial<Word>) => void
    onSplitWord: (index: number) => void
    onRemoveWord: (index: number) => void
    onAddWord: (index: number) => void
    onMergeWords: (index: number) => void
    onSplitSegment?: (index: number) => void
    onAddSegment?: (index: number) => void
    onMergeSegment?: (mergeWithNext: boolean) => void
    wordsLength: number
    isGlobal: boolean
    onTabNavigation: (currentIndex: number) => void
}) {
    return (
        <Box key={word.id}>
            <WordRow
                word={word}
                index={index}
                onWordUpdate={onWordUpdate}
                onSplitWord={onSplitWord}
                onRemoveWord={onRemoveWord}
                wordsLength={wordsLength}
                onTabNavigation={onTabNavigation}
            />

            {/* Word divider with merge/split functionality */}
            {!isGlobal && (
                <WordDivider
                    onAddWord={() => onAddWord(index)}
                    onMergeWords={() => onMergeWords(index)}
                    onSplitSegment={() => onSplitSegment?.(index)}
                    onAddSegmentAfter={
                        index === wordsLength - 1
                            ? () => onAddSegment?.(index + 1)
                            : undefined
                    }
                    onMergeSegment={
                        index === wordsLength - 1
                            ? () => onMergeSegment?.(true)
                            : undefined
                    }
                    canMerge={index < wordsLength - 1}
                    isLast={index === wordsLength - 1}
                    sx={{ ml: 15 }}
                />
            )}
            {isGlobal && (
                <WordDivider
                    onAddWord={() => onAddWord(index)}
                    onMergeWords={index < wordsLength - 1 ? () => onMergeWords(index) : undefined}
                    canMerge={index < wordsLength - 1}
                    sx={{ ml: 15 }}
                />
            )}
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
    const [page, setPage] = useState(1)
    const pageSize = isGlobal ? 50 : words.length // Use pagination only in global mode
    
    const handleReplaceAllWords = () => {
        const newWords = replacementText.trim().split(/\s+/)
        newWords.forEach((text, index) => {
            if (index < words.length) {
                onWordUpdate(index, { text })
            }
        })
        setReplacementText('')
    }
    
    // Calculate pagination values
    const pageCount = Math.ceil(words.length / pageSize)
    const startIndex = (page - 1) * pageSize
    const endIndex = Math.min(startIndex + pageSize, words.length)
    
    // Get the words for the current page
    const visibleWords = useMemo(() => {
        return isGlobal 
            ? words.slice(startIndex, endIndex) 
            : words;
    }, [words, isGlobal, startIndex, endIndex]);
    
    // Handle page change
    const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
        setPage(value);
    };

    // Handle tab navigation between word text fields
    const handleTabNavigation = (currentIndex: number) => {
        // console.log('handleTabNavigation called with index:', currentIndex);
        const nextIndex = (currentIndex + 1) % words.length;
        // console.log('Next index calculated:', nextIndex, 'Total words:', words.length);
        
        // If the next word is on a different page, change the page
        if (isGlobal && (nextIndex < startIndex || nextIndex >= endIndex)) {
            // console.log('Next word is on different page. Current page:', page, 'startIndex:', startIndex, 'endIndex:', endIndex);
            const nextPage = Math.floor(nextIndex / pageSize) + 1;
            // console.log('Changing to page:', nextPage);
            setPage(nextPage);
            
            // Use setTimeout to allow the page change to render before focusing
            setTimeout(() => {
                // console.log('Timeout callback executing, trying to focus element with ID:', `word-text-${nextIndex}`);
                focusWordTextField(nextIndex);
            }, 50);
        } else {
            // console.log('Next word is on same page, trying to focus element with ID:', `word-text-${nextIndex}`);
            focusWordTextField(nextIndex);
        }
    };

    // Helper function to focus a word text field by index
    const focusWordTextField = (index: number) => {
        // Material-UI TextField uses a more complex structure
        // The actual input is inside the TextField component
        const element = document.getElementById(`word-text-${index}`);
        // console.log('Element found:', !!element);
        
        if (element) {
            // Try different selectors to find the input element
            // First try the standard input selector
            let input = element.querySelector('input');
            
            // If that doesn't work, try the MUI-specific selector
            if (!input) {
                input = element.querySelector('.MuiInputBase-input');
            }
            
            // console.log('Input element found:', !!input);
            if (input) {
                input.focus();
                input.select();
                // console.log('Focus and select called on input');
            } else {
                // As a fallback, try to focus the TextField itself
                // console.log('Trying to focus the TextField itself');
                element.focus();
            }
        }
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flexGrow: 1, minHeight: 0 }}>
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
            
            {/* Word list with scrolling */}
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
                {visibleWords.map((word, visibleIndex) => {
                    const actualIndex = isGlobal ? startIndex + visibleIndex : visibleIndex;
                    return (
                        <WordItem
                            key={word.id}
                            word={word}
                            index={actualIndex}
                            onWordUpdate={onWordUpdate}
                            onSplitWord={onSplitWord}
                            onRemoveWord={onRemoveWord}
                            onAddWord={onAddWord}
                            onMergeWords={onMergeWords}
                            onSplitSegment={onSplitSegment}
                            onAddSegment={onAddSegment}
                            onMergeSegment={onMergeSegment}
                            wordsLength={words.length}
                            isGlobal={isGlobal}
                            onTabNavigation={handleTabNavigation}
                        />
                    );
                })}
            </Box>
            
            {/* Pagination controls (only in global mode) */}
            {isGlobal && pageCount > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', mb: 1 }}>
                    <Pagination 
                        count={pageCount} 
                        page={page} 
                        onChange={handlePageChange} 
                        color="primary" 
                        size="small"
                    />
                    <Typography variant="body2" sx={{ ml: 2 }}>
                        Showing words {startIndex + 1}-{endIndex} of {words.length}
                    </Typography>
                </Box>
            )}

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