import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
    TextField,
    Button,
    Typography,
    Switch,
    FormControlLabel,
    Divider,
    List,
    ListItem,
    ListItemText,
    Paper,
    Alert,
    Tooltip,
    CircularProgress
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useState, useEffect } from 'react'
import { CorrectionData } from '../types'

interface MatchPreview {
    segmentIndex: number
    wordIndex?: number  // Optional for full text mode
    wordIndices?: number[]  // For full text mode with multiple words
    segmentText: string
    wordText: string
    replacement: string
    willBeRemoved: boolean
    isMultiWord?: boolean
}

interface FindReplaceModalProps {
    open: boolean
    onClose: () => void
    onReplace: (findText: string, replaceText: string, options: { caseSensitive: boolean, useRegex: boolean, fullTextMode: boolean }) => void
    data: CorrectionData
}

export default function FindReplaceModal({
    open,
    onClose,
    onReplace,
    data
}: FindReplaceModalProps) {
    const [findText, setFindText] = useState('')
    const [replaceText, setReplaceText] = useState('')
    const [caseSensitive, setCaseSensitive] = useState(false)
    const [useRegex, setUseRegex] = useState(false)
    const [fullTextMode, setFullTextMode] = useState(false)
    const [matchPreviews, setMatchPreviews] = useState<MatchPreview[]>([])
    const [regexError, setRegexError] = useState<string | null>(null)
    const [isSearching, setIsSearching] = useState(false)
    const [hasEmptyReplacements, setHasEmptyReplacements] = useState(false)

    // Reset state when modal opens
    useEffect(() => {
        if (open) {
            setMatchPreviews([])
            setRegexError(null)
            setHasEmptyReplacements(false)
        }
    }, [open])

    // Find matches whenever search parameters change
    useEffect(() => {
        if (!open || !findText) {
            setMatchPreviews([])
            setRegexError(null)
            setHasEmptyReplacements(false)
            return
        }

        setIsSearching(true)
        
        // Use setTimeout to prevent UI freezing for large datasets
        const timeoutId = setTimeout(() => {
            try {
                const matches = fullTextMode 
                    ? findMatchesFullText(data, findText, replaceText, { caseSensitive, useRegex })
                    : findMatches(data, findText, replaceText, { caseSensitive, useRegex });
                
                setMatchPreviews(matches)
                
                // Check if any replacements would result in empty words
                const hasEmpty = matches.some(match => match.willBeRemoved)
                setHasEmptyReplacements(hasEmpty)
                
                setRegexError(null)
            } catch (error) {
                if (error instanceof Error) {
                    setRegexError(error.message)
                } else {
                    setRegexError('Invalid regex pattern')
                }
                setMatchPreviews([])
                setHasEmptyReplacements(false)
            } finally {
                setIsSearching(false)
            }
        }, 300)

        return () => clearTimeout(timeoutId)
    }, [open, data, findText, replaceText, caseSensitive, useRegex, fullTextMode])

    const handleReplace = () => {
        if (!findText || regexError) return
        onReplace(findText, replaceText, { caseSensitive, useRegex, fullTextMode })
        onClose()
    }

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (event.key === 'Enter' && !event.shiftKey && !regexError && findText) {
            event.preventDefault()
            handleReplace()
        }
    }

    // Function to find matches at the word level (original implementation)
    const findMatches = (
        data: CorrectionData, 
        findText: string, 
        replaceText: string, 
        options: { caseSensitive: boolean, useRegex: boolean }
    ): MatchPreview[] => {
        const matches: MatchPreview[] = []
        
        if (!findText) return matches

        try {
            const segments = data.corrected_segments || []
            
            segments.forEach((segment, segmentIndex) => {
                segment.words.forEach((word, wordIndex) => {
                    let pattern: RegExp
                    const replacement = replaceText
                    
                    if (options.useRegex) {
                        // Create regex with or without case sensitivity
                        pattern = new RegExp(findText, options.caseSensitive ? 'g' : 'gi')
                    } else {
                        // Escape special regex characters for literal search
                        const escapedFindText = findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                        pattern = new RegExp(escapedFindText, options.caseSensitive ? 'g' : 'gi')
                    }
                    
                    // Check if there's a match
                    if (pattern.test(word.text)) {
                        // Reset regex lastIndex
                        pattern.lastIndex = 0
                        
                        // Create replacement preview
                        const replacedText = word.text.replace(pattern, replacement)
                        const willBeRemoved = replacedText.trim() === ''
                        
                        matches.push({
                            segmentIndex,
                            wordIndex,
                            segmentText: segment.text,
                            wordText: word.text,
                            replacement: replacedText,
                            willBeRemoved
                        })
                    }
                })
            })
            
            return matches
        } catch (error) {
            if (options.useRegex) {
                throw new Error('Invalid regex pattern')
            }
            throw error
        }
    }

    // Function to find matches across word boundaries (full text mode)
    const findMatchesFullText = (
        data: CorrectionData, 
        findText: string, 
        replaceText: string, 
        options: { caseSensitive: boolean, useRegex: boolean }
    ): MatchPreview[] => {
        const matches: MatchPreview[] = []
        
        if (!findText) return matches

        try {
            const segments = data.corrected_segments || []
            
            segments.forEach((segment, segmentIndex) => {
                let pattern: RegExp
                
                if (options.useRegex) {
                    // Create regex with or without case sensitivity
                    pattern = new RegExp(findText, options.caseSensitive ? 'g' : 'gi')
                } else {
                    // Escape special regex characters for literal search
                    const escapedFindText = findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                    pattern = new RegExp(escapedFindText, options.caseSensitive ? 'g' : 'gi')
                }
                
                // Get the full segment text
                const segmentText = segment.text;
                
                // Find all matches in the segment text
                let match;
                while ((match = pattern.exec(segmentText)) !== null) {
                    const matchText = match[0];
                    const startIndex = match.index;
                    const endIndex = startIndex + matchText.length;
                    
                    // Find which words are affected by this match
                    const affectedWordIndices: number[] = [];
                    let startWordIndex = -1;
                    let currentPosition = 0;
                    
                    for (let i = 0; i < segment.words.length; i++) {
                        const word = segment.words[i];
                        const wordStart = currentPosition;
                        const wordEnd = wordStart + word.text.length;
                        
                        // Add spaces between words for position calculation
                        if (i > 0) currentPosition += 1;
                        
                        // Check if this word is part of the match
                        if (wordEnd > startIndex && wordStart < endIndex) {
                            affectedWordIndices.push(i);
                            if (startWordIndex === -1) startWordIndex = i;
                        }
                        
                        currentPosition += word.text.length;
                    }
                    
                    if (affectedWordIndices.length > 0) {
                        // Create replacement preview
                        const willBeRemoved = replaceText.trim() === '';
                        
                        matches.push({
                            segmentIndex,
                            wordIndices: affectedWordIndices,
                            segmentText,
                            wordText: matchText,
                            replacement: replaceText,
                            willBeRemoved,
                            isMultiWord: affectedWordIndices.length > 1
                        });
                    }
                }
            })
            
            return matches
        } catch (error) {
            if (options.useRegex) {
                throw new Error('Invalid regex pattern')
            }
            throw error
        }
    }

    const getContextualMatch = (preview: MatchPreview) => {
        if (preview.isMultiWord && preview.wordIndices) {
            // For multi-word matches in full text mode
            const segment = data.corrected_segments[preview.segmentIndex];
            const words = segment.words;
            
            // Get context words before and after the match
            const firstMatchedWordIdx = preview.wordIndices[0];
            const lastMatchedWordIdx = preview.wordIndices[preview.wordIndices.length - 1];
            
            const startContextIdx = Math.max(0, firstMatchedWordIdx - 2);
            const endContextIdx = Math.min(words.length - 1, lastMatchedWordIdx + 2);
            
            const beforeWords = words.slice(startContextIdx, firstMatchedWordIdx).map(w => w.text).join(' ');
            const matchedWords = words.slice(firstMatchedWordIdx, lastMatchedWordIdx + 1).map(w => w.text).join(' ');
            const afterWords = words.slice(lastMatchedWordIdx + 1, endContextIdx + 1).map(w => w.text).join(' ');
            
            return (
                <Box>
                    {beforeWords && <Typography component="span" color="text.secondary">{beforeWords} </Typography>}
                    <Typography component="span" color="error" fontWeight="bold">{matchedWords}</Typography>
                    {afterWords && <Typography component="span" color="text.secondary"> {afterWords}</Typography>}
                    <Typography variant="body2" color="primary" sx={{ mt: 0.5 }}>
                        {preview.willBeRemoved ? (
                            <Typography component="span" color="warning.main" fontWeight="bold">
                                ↳ Text will be removed
                            </Typography>
                        ) : (
                            <>↳ <b>{preview.replacement}</b></>
                        )}
                    </Typography>
                </Box>
            );
        } else {
            // For single word matches (original implementation)
            const words = data.corrected_segments[preview.segmentIndex].words;
            const wordIndex = preview.wordIndex || 0;
            
            // Get a few words before and after for context
            const startIdx = Math.max(0, wordIndex - 2);
            const endIdx = Math.min(words.length - 1, wordIndex + 2);
            
            const beforeWords = words.slice(startIdx, wordIndex).map(w => w.text).join(' ');
            const afterWords = words.slice(wordIndex + 1, endIdx + 1).map(w => w.text).join(' ');
            
            return (
                <Box>
                    {beforeWords && <Typography component="span" color="text.secondary">{beforeWords} </Typography>}
                    <Typography component="span" color="error" fontWeight="bold">{preview.wordText}</Typography>
                    {afterWords && <Typography component="span" color="text.secondary"> {afterWords}</Typography>}
                    <Typography variant="body2" color="primary" sx={{ mt: 0.5 }}>
                        {preview.willBeRemoved ? (
                            <Typography component="span" color="warning.main" fontWeight="bold">
                                ↳ Word will be removed
                            </Typography>
                        ) : (
                            <>↳ <b>{preview.replacement}</b></>
                        )}
                    </Typography>
                </Box>
            );
        }
    }

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            onKeyDown={handleKeyDown}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1 }}>Find and Replace</Box>
                <IconButton onClick={onClose}>
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            <DialogContent dividers>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <TextField
                            label="Find"
                            value={findText}
                            onChange={(e) => setFindText(e.target.value)}
                            fullWidth
                            size="small"
                            autoFocus
                            error={!!regexError}
                            helperText={regexError}
                        />
                        <TextField
                            label="Replace with"
                            value={replaceText}
                            onChange={(e) => setReplaceText(e.target.value)}
                            fullWidth
                            size="small"
                        />
                        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                            <FormControlLabel
                                control={
                                    <Switch 
                                        checked={caseSensitive}
                                        onChange={(e) => setCaseSensitive(e.target.checked)}
                                    />
                                }
                                label="Case sensitive"
                            />
                            <FormControlLabel
                                control={
                                    <Switch 
                                        checked={useRegex}
                                        onChange={(e) => setUseRegex(e.target.checked)}
                                    />
                                }
                                label={
                                    <Tooltip title="Use JavaScript regular expressions for advanced pattern matching">
                                        <span>Use regex</span>
                                    </Tooltip>
                                }
                            />
                            <FormControlLabel
                                control={
                                    <Switch 
                                        checked={fullTextMode}
                                        onChange={(e) => setFullTextMode(e.target.checked)}
                                    />
                                }
                                label={
                                    <Tooltip title="Search across word boundaries to find and replace text that spans multiple words">
                                        <span>Full text mode</span>
                                    </Tooltip>
                                }
                            />
                        </Box>
                    </Box>
                    
                    <Divider />
                    
                    <Box>
                        <Typography variant="subtitle1" gutterBottom>
                            Preview {isSearching ? <CircularProgress size={16} sx={{ ml: 1 }} /> : null}
                        </Typography>
                        
                        {hasEmptyReplacements && (
                            <Alert severity="warning" sx={{ mb: 2 }}>
                                Some replacements will result in empty words, which will be removed.
                            </Alert>
                        )}
                        
                        {fullTextMode && (
                            <Alert severity="info" sx={{ mb: 2 }}>
                                Full text mode is enabled. Matches can span across multiple words.
                            </Alert>
                        )}
                        
                        {!isSearching && findText && matchPreviews.length === 0 && !regexError && (
                            <Alert severity="info">No matches found</Alert>
                        )}
                        
                        {!isSearching && matchPreviews.length > 0 && (
                            <>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    {matchPreviews.length} {matchPreviews.length === 1 ? 'match' : 'matches'} found
                                </Typography>
                                <Paper variant="outlined" sx={{ maxHeight: 300, overflow: 'auto' }}>
                                    <List dense>
                                        {matchPreviews.slice(0, 50).map((preview, index) => (
                                            <ListItem key={index} divider={index < matchPreviews.length - 1}>
                                                <ListItemText
                                                    primary={getContextualMatch(preview)}
                                                    secondary={`Segment ${preview.segmentIndex + 1}${preview.isMultiWord ? ' (spans multiple words)' : ''}`}
                                                />
                                            </ListItem>
                                        ))}
                                        {matchPreviews.length > 50 && (
                                            <ListItem>
                                                <ListItemText 
                                                    primary={`${matchPreviews.length - 50} more matches not shown`} 
                                                    primaryTypographyProps={{ color: 'text.secondary' }}
                                                />
                                            </ListItem>
                                        )}
                                    </List>
                                </Paper>
                            </>
                        )}
                    </Box>
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button 
                    onClick={handleReplace}
                    disabled={!findText || !!regexError || matchPreviews.length === 0}
                    variant="contained"
                >
                    Replace All ({matchPreviews.length})
                </Button>
            </DialogActions>
        </Dialog>
    )
} 