import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Box,
    Button,
    Typography,
    Slider,
    ButtonGroup
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutline'
import StopCircleIcon from '@mui/icons-material/StopCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import ZoomInIcon from '@mui/icons-material/ZoomIn'
import ZoomOutIcon from '@mui/icons-material/ZoomOut'
import { LyricsSegment, Word } from '../types'
import { useState, useEffect, useCallback, useRef } from 'react'
import TimelineEditor from './TimelineEditor'

interface GlobalSyncEditorProps {
    open: boolean
    onClose: () => void
    segments: LyricsSegment[]
    onSave: (updatedSegments: LyricsSegment[]) => void
    onPlaySegment?: (startTime: number) => void
    currentTime?: number
    setModalSpacebarHandler: (handler: (() => (e: KeyboardEvent) => void) | undefined) => void
}

// Zoom levels in seconds per screen width - more granular at the lower end
const ZOOM_LEVELS = [5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300, 600, 1200];

interface FlattenedWord {
    word: Word;
    segmentIndex: number;
    wordIndex: number;
}

export default function GlobalSyncEditor({
    open,
    onClose,
    segments,
    onSave,
    onPlaySegment,
    currentTime = 0,
    setModalSpacebarHandler
}: GlobalSyncEditorProps) {
    const [editedSegments, setEditedSegments] = useState<LyricsSegment[]>([]);
    const [allWords, setAllWords] = useState<FlattenedWord[]>([]);
    const [isManualSyncing, setIsManualSyncing] = useState(false);
    const [syncWordIndex, setSyncWordIndex] = useState<number>(-1);
    const [zoomLevel, setZoomLevel] = useState<number>(3); // Default to 20 seconds per screen
    const [scrollPosition, setScrollPosition] = useState<number>(0);
    const [songDuration, setSongDuration] = useState<number>(0);
    const [visibleTimeRange, setVisibleTimeRange] = useState<{start: number, end: number}>({start: 0, end: 20});
    const [isPlaying, setIsPlaying] = useState(false);
    const timelineContainerRef = useRef<HTMLDivElement>(null);
    
    // Initialize the edited segments and flatten all words when the modal opens
    useEffect(() => {
        if (open && segments) {
            const segmentsCopy = [...segments];
            setEditedSegments(segmentsCopy);
            
            // Create flattened word list with references to original segment and word indices
            const flattenedWords: FlattenedWord[] = [];
            segmentsCopy.forEach((segment, segmentIndex) => {
                segment.words.forEach((word, wordIndex) => {
                    flattenedWords.push({
                        word,
                        segmentIndex,
                        wordIndex
                    });
                });
            });
            
            // Sort words by start time
            flattenedWords.sort((a, b) => {
                const aStart = a.word.start_time ?? 0;
                const bStart = b.word.start_time ?? 0;
                return aStart - bStart;
            });
            
            setAllWords(flattenedWords);
            
            // Calculate song duration
            const allEndTimes = flattenedWords.map(item => item.word.end_time).filter((t): t is number => t !== null);
            const duration = allEndTimes.length > 0 ? Math.max(...allEndTimes) + 5 : 60; // Add 5 seconds padding
            setSongDuration(duration);
            
            // Reset scroll position
            setScrollPosition(0);
            updateVisibleTimeRange(0, zoomLevel);
        }
    }, [open, segments, zoomLevel]);
    
    // Update visible time range when scroll position or zoom level changes
    const updateVisibleTimeRange = useCallback((scrollPos: number, zoom: number) => {
        const secondsPerScreen = ZOOM_LEVELS[zoom];
        const start = scrollPos * songDuration / 100;
        const end = start + secondsPerScreen;
        setVisibleTimeRange({start, end});
    }, [songDuration]);
    
    // Handle scroll position change
    const handleScroll = useCallback(() => {
        if (!timelineContainerRef.current) return;
        
        const container = timelineContainerRef.current;
        const scrollPercentage = (container.scrollLeft / (container.scrollWidth - container.clientWidth)) * 100;
        setScrollPosition(scrollPercentage);
        updateVisibleTimeRange(scrollPercentage, zoomLevel);
    }, [zoomLevel, updateVisibleTimeRange]);
    
    // Handle zoom level change
    const handleZoomChange = useCallback((_event: React.SyntheticEvent | Event, newValue: number | number[]) => {
        const newZoom = Array.isArray(newValue) ? newValue[0] : newValue;
        setZoomLevel(newZoom);
        updateVisibleTimeRange(scrollPosition, newZoom);
    }, [scrollPosition, updateVisibleTimeRange]);
    
    // Handle word update
    const handleWordUpdate = useCallback((flatWordIndex: number, updates: Partial<Word>) => {
        if (flatWordIndex < 0 || flatWordIndex >= allWords.length) return;
        
        const { segmentIndex, wordIndex } = allWords[flatWordIndex];
        const newSegments = [...editedSegments];
        
        if (segmentIndex < 0 || segmentIndex >= newSegments.length) return;
        const segment = newSegments[segmentIndex];
        
        if (wordIndex < 0 || wordIndex >= segment.words.length) return;
        
        // Update the word
        const newWords = [...segment.words];
        newWords[wordIndex] = {
            ...newWords[wordIndex],
            ...updates
        };
        
        // Update segment start/end times based on words
        const validStartTimes = newWords.map(w => w.start_time).filter((t): t is number => t !== null);
        const validEndTimes = newWords.map(w => w.end_time).filter((t): t is number => t !== null);
        
        const segmentStartTime = validStartTimes.length > 0 ? Math.min(...validStartTimes) : segment.start_time;
        const segmentEndTime = validEndTimes.length > 0 ? Math.max(...validEndTimes) : segment.end_time;
        
        newSegments[segmentIndex] = {
            ...segment,
            words: newWords,
            start_time: segmentStartTime,
            end_time: segmentEndTime
        };
        
        setEditedSegments(newSegments);
        
        // Update the flattened words array
        const newAllWords = [...allWords];
        newAllWords[flatWordIndex] = {
            ...newAllWords[flatWordIndex],
            word: {
                ...newAllWords[flatWordIndex].word,
                ...updates
            }
        };
        setAllWords(newAllWords);
    }, [allWords, editedSegments]);
    
    // Create a custom manual sync hook for the global timeline
    const useGlobalManualSync = () => {
        const [isSpacebarPressed, setIsSpacebarPressed] = useState(false);
        const wordStartTimeRef = useRef<number | null>(null);
        const spacebarPressTimeRef = useRef<number | null>(null);
        const currentTimeRef = useRef(currentTime);
        
        // Keep currentTimeRef up to date
        useEffect(() => {
            currentTimeRef.current = currentTime;
        }, [currentTime]);
        
        const cleanupManualSync = useCallback(() => {
            setIsManualSyncing(false);
            setSyncWordIndex(-1);
            setIsSpacebarPressed(false);
            wordStartTimeRef.current = null;
            spacebarPressTimeRef.current = null;
        }, []);
        
        const startManualSyncFromBeginning = useCallback(() => {
            if (isManualSyncing) {
                cleanupManualSync();
                return;
            }
            
            if (!onPlaySegment || allWords.length === 0) return;
            
            setIsManualSyncing(true);
            setSyncWordIndex(0);
            setIsSpacebarPressed(false);
            wordStartTimeRef.current = null;
            spacebarPressTimeRef.current = null;
            
            // Start playing 3 seconds before the first word
            const firstWordStartTime = allWords[0].word.start_time ?? 0;
            onPlaySegment(Math.max(0, firstWordStartTime - 3));
            setIsPlaying(true);
        }, [isManualSyncing, allWords, onPlaySegment, cleanupManualSync]);
        
        const startManualSyncFromCurrent = useCallback(() => {
            if (isManualSyncing) {
                cleanupManualSync();
                return;
            }
            
            if (!onPlaySegment || allWords.length === 0) return;
            
            // Find the word closest to the current time
            const currentT = currentTimeRef.current;
            let closestIndex = 0;
            let minDiff = Number.MAX_VALUE;
            
            allWords.forEach((item, index) => {
                const wordStart = item.word.start_time ?? 0;
                const diff = Math.abs(wordStart - currentT);
                if (diff < minDiff) {
                    minDiff = diff;
                    closestIndex = index;
                }
            });
            
            setIsManualSyncing(true);
            setSyncWordIndex(closestIndex);
            setIsSpacebarPressed(false);
            wordStartTimeRef.current = null;
            spacebarPressTimeRef.current = null;
            
            // Start playing 3 seconds before the selected word
            const wordStartTime = allWords[closestIndex].word.start_time ?? 0;
            onPlaySegment(Math.max(0, wordStartTime - 3));
            setIsPlaying(true);
        }, [isManualSyncing, allWords, onPlaySegment, cleanupManualSync, currentTimeRef]);
        
        const handleKeyDown = useCallback((e: KeyboardEvent) => {
            if (e.code !== 'Space') return;
            
            console.log('GlobalSyncEditor - Spacebar pressed down', {
                isManualSyncing,
                syncWordIndex,
                currentTime: currentTimeRef.current
            });
            
            e.preventDefault();
            e.stopPropagation();
            
            if (isManualSyncing && !isSpacebarPressed && syncWordIndex >= 0 && syncWordIndex < allWords.length) {
                const currentWord = allWords[syncWordIndex];
                console.log('GlobalSyncEditor - Recording word start time', {
                    wordIndex: syncWordIndex,
                    wordText: currentWord.word.text,
                    time: currentTimeRef.current
                });
                
                setIsSpacebarPressed(true);
                
                // Record the start time of the current word
                wordStartTimeRef.current = currentTimeRef.current;
                
                // Record when the spacebar was pressed (for tap detection)
                spacebarPressTimeRef.current = Date.now();
                
                // Update the word's start time immediately
                handleWordUpdate(syncWordIndex, { start_time: currentTimeRef.current });
            } else if (!isManualSyncing && onPlaySegment) {
                // Toggle playback when not in manual sync mode
                if (window.toggleAudioPlayback) {
                    window.toggleAudioPlayback();
                    setIsPlaying(prev => !prev);
                }
            }
        }, [isManualSyncing, syncWordIndex, allWords, isSpacebarPressed, handleWordUpdate, onPlaySegment]);
        
        const handleKeyUp = useCallback((e: KeyboardEvent) => {
            if (e.code !== 'Space') return;
            
            console.log('GlobalSyncEditor - Spacebar released', {
                isManualSyncing,
                syncWordIndex,
                currentTime: currentTimeRef.current,
                wordStartTime: wordStartTimeRef.current
            });
            
            e.preventDefault();
            e.stopPropagation();
            
            if (isManualSyncing && isSpacebarPressed && syncWordIndex >= 0 && syncWordIndex < allWords.length) {
                const currentWord = allWords[syncWordIndex];
                const pressDuration = spacebarPressTimeRef.current ? Date.now() - spacebarPressTimeRef.current : 0;
                const isTap = pressDuration < 200; // If pressed for less than 200ms, consider it a tap
                
                console.log('GlobalSyncEditor - Recording word end time', {
                    wordIndex: syncWordIndex,
                    wordText: currentWord.word.text,
                    startTime: wordStartTimeRef.current,
                    endTime: currentTimeRef.current,
                    pressDuration: `${pressDuration}ms`,
                    isTap,
                    duration: (currentTimeRef.current - (wordStartTimeRef.current || 0)).toFixed(2) + 's'
                });
                
                setIsSpacebarPressed(false);
                
                // Set the end time for the current word based on whether it was a tap or hold
                if (isTap) {
                    // For a tap, set a default duration of 1 second
                    const defaultEndTime = (wordStartTimeRef.current || currentTimeRef.current) + 1.0;
                    handleWordUpdate(syncWordIndex, { end_time: defaultEndTime });
                } else {
                    // For a hold, use the current time as the end time
                    handleWordUpdate(syncWordIndex, { end_time: currentTimeRef.current });
                }
                
                // Move to the next word
                if (syncWordIndex === allWords.length - 1) {
                    // If this was the last word, finish manual sync
                    console.log('GlobalSyncEditor - Completed manual sync for all words');
                    setIsManualSyncing(false);
                    setSyncWordIndex(-1);
                    wordStartTimeRef.current = null;
                    spacebarPressTimeRef.current = null;
                } else {
                    // Otherwise, move to the next word
                    const nextWord = allWords[syncWordIndex + 1];
                    console.log('GlobalSyncEditor - Moving to next word', {
                        nextWordIndex: syncWordIndex + 1,
                        nextWordText: nextWord.word.text
                    });
                    setSyncWordIndex(syncWordIndex + 1);
                    
                    // If the next word's start time would overlap with the current word's end time,
                    // adjust the next word's start time
                    const currentEndTime = currentWord.word.end_time;
                    const nextStartTime = nextWord.word.start_time;
                    
                    if (currentEndTime !== null && nextStartTime !== null && currentEndTime > nextStartTime) {
                        handleWordUpdate(syncWordIndex + 1, { start_time: currentEndTime + 0.01 });
                    }
                }
            }
        }, [isManualSyncing, syncWordIndex, allWords, isSpacebarPressed, handleWordUpdate]);
        
        // Combine the key handlers into a single function for external use
        const handleSpacebar = useCallback((e: KeyboardEvent) => {
            if (e.type === 'keydown') {
                handleKeyDown(e);
            } else if (e.type === 'keyup') {
                handleKeyUp(e);
            }
        }, [handleKeyDown, handleKeyUp]);
        
        return {
            isSpacebarPressed,
            startManualSyncFromBeginning,
            startManualSyncFromCurrent,
            cleanupManualSync,
            handleSpacebar
        };
    };
    
    const {
        isSpacebarPressed,
        startManualSyncFromBeginning,
        startManualSyncFromCurrent,
        cleanupManualSync,
        handleSpacebar
    } = useGlobalManualSync();
    
    // Update the spacebar handler when modal state changes
    useEffect(() => {
        const spacebarHandler = handleSpacebar; // Capture the current handler
        
        if (open) {
            console.log('GlobalSyncEditor - Setting up modal spacebar handler');
            
            // Create a function that will be called by the global event listeners
            const handleKeyEvent = (e: KeyboardEvent) => {
                if (e.code === 'Space') {
                    spacebarHandler(e);
                }
            };
            
            // Wrap the handler function to match the expected signature
            setModalSpacebarHandler(() => () => handleKeyEvent);
            
            // Only cleanup when the effect is re-run or the modal is closed
            return () => {
                if (!open) {
                    console.log('GlobalSyncEditor - Cleanup: clearing modal spacebar handler');
                    setModalSpacebarHandler(undefined);
                }
            };
        }
    }, [
        open,
        handleSpacebar,
        setModalSpacebarHandler
    ]);
    
    // Update isPlaying state when currentTime changes
    useEffect(() => {
        if (window.isAudioPlaying !== undefined) {
            setIsPlaying(window.isAudioPlaying);
        }
    }, [currentTime]);
    
    const handleClose = useCallback(() => {
        cleanupManualSync();
        onClose();
    }, [onClose, cleanupManualSync]);
    
    const handleSave = useCallback(() => {
        onSave(editedSegments);
        onClose();
    }, [editedSegments, onSave, onClose]);
    
    const handlePlayFromTime = useCallback((time: number) => {
        if (onPlaySegment) {
            onPlaySegment(time);
            setIsPlaying(true);
        }
    }, [onPlaySegment]);
    
    const handlePlayPause = useCallback(() => {
        if (window.toggleAudioPlayback) {
            window.toggleAudioPlayback();
            setIsPlaying(prev => !prev);
        }
    }, []);
    
    const handleStop = useCallback(() => {
        if (window.isAudioPlaying && window.toggleAudioPlayback) {
            window.toggleAudioPlayback(); // Pause the audio
            setIsPlaying(false);
        }
    }, []);
    
    // Scroll to current time
    const scrollToCurrentTime = useCallback(() => {
        if (!timelineContainerRef.current) return;
        
        const container = timelineContainerRef.current;
        const totalWidth = container.scrollWidth;
        const viewportWidth = container.clientWidth;
        
        // Calculate the position of the current time as a percentage of the total duration
        const currentTimePosition = (currentTime / songDuration) * totalWidth;
        
        // Calculate the scroll position to center the current time in the viewport
        const scrollLeft = Math.max(0, currentTimePosition - (viewportWidth / 2));
        
        // Smoothly scroll to the position
        container.scrollTo({
            left: scrollLeft,
            behavior: 'smooth'
        });
    }, [currentTime, songDuration]);
    
    // Early return if no segments
    if (!segments || segments.length === 0) return null;
    
    // Calculate zoom-related values
    const secondsPerScreen = ZOOM_LEVELS[zoomLevel];
    const totalWidthPercentage = (songDuration / secondsPerScreen) * 100;
    
    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: {
                    height: '80vh',
                    display: 'flex',
                    flexDirection: 'column'
                }
            }}
        >
            <DialogTitle>
                Edit Sync - All Words
                <IconButton
                    aria-label="close"
                    onClick={handleClose}
                    sx={{
                        position: 'absolute',
                        right: 8,
                        top: 8,
                        color: (theme) => theme.palette.grey[500],
                    }}
                >
                    <CloseIcon />
                </IconButton>
            </DialogTitle>
            
            <DialogContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* Zoom controls */}
                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="body2">Zoom:</Typography>
                    <IconButton 
                        size="small" 
                        onClick={() => setZoomLevel(Math.max(0, zoomLevel - 1))}
                        disabled={zoomLevel === 0}
                    >
                        <ZoomOutIcon />
                    </IconButton>
                    
                    <Slider
                        value={zoomLevel}
                        min={0}
                        max={ZOOM_LEVELS.length - 1}
                        step={1}
                        onChange={handleZoomChange}
                        marks
                        sx={{ flexGrow: 1, maxWidth: 300 }}
                    />
                    
                    <IconButton 
                        size="small" 
                        onClick={() => setZoomLevel(Math.min(ZOOM_LEVELS.length - 1, zoomLevel + 1))}
                        disabled={zoomLevel === ZOOM_LEVELS.length - 1}
                    >
                        <ZoomInIcon />
                    </IconButton>
                    
                    <Typography variant="body2">
                        {ZOOM_LEVELS[zoomLevel]} seconds per screen
                    </Typography>
                </Box>
                
                {/* Playback and manual sync controls */}
                <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <ButtonGroup variant="outlined">
                        <Button
                            onClick={handlePlayPause}
                            startIcon={isPlaying ? <PauseCircleOutlineIcon /> : <PlayCircleOutlineIcon />}
                        >
                            {isPlaying ? "Pause" : "Play"}
                        </Button>
                        <Button
                            onClick={handleStop}
                            startIcon={<StopCircleIcon />}
                            disabled={!isPlaying}
                        >
                            Stop
                        </Button>
                        <Button
                            onClick={scrollToCurrentTime}
                            disabled={!currentTime}
                        >
                            Go to Current Time
                        </Button>
                    </ButtonGroup>
                    
                    <Button
                        variant={isManualSyncing ? "outlined" : "contained"}
                        onClick={startManualSyncFromBeginning}
                        disabled={!onPlaySegment || allWords.length === 0}
                        startIcon={isManualSyncing ? <CancelIcon /> : <PlayCircleOutlineIcon />}
                        color={isManualSyncing ? "error" : "primary"}
                    >
                        {isManualSyncing ? "Cancel Sync" : "Sync From Start"}
                    </Button>
                    
                    <Button
                        variant="contained"
                        onClick={startManualSyncFromCurrent}
                        disabled={!onPlaySegment || allWords.length === 0 || isManualSyncing}
                        startIcon={<PlayCircleOutlineIcon />}
                    >
                        Sync From Current Time
                    </Button>
                </Box>
                
                {/* Manual sync status */}
                {isManualSyncing && syncWordIndex >= 0 && syncWordIndex < allWords.length && (
                    <Box sx={{ mb: 2 }}>
                        <Typography variant="body2">
                            Word {syncWordIndex + 1} of {allWords.length}: <strong>{allWords[syncWordIndex].word.text || ''}</strong>
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            {isSpacebarPressed ? 
                                "Holding spacebar... Release when word ends" : 
                                "Press spacebar when word starts (tap for short words, hold for long words)"}
                        </Typography>
                    </Box>
                )}
                
                {/* Timeline container with horizontal scrolling */}
                <Box 
                    ref={timelineContainerRef}
                    sx={{ 
                        flexGrow: 1, 
                        overflowX: 'auto',
                        overflowY: 'hidden',
                        position: 'relative',
                        '&::-webkit-scrollbar': {
                            height: '10px',
                        },
                        '&::-webkit-scrollbar-thumb': {
                            backgroundColor: 'rgba(0,0,0,0.2)',
                            borderRadius: '10px',
                        },
                    }}
                    onScroll={handleScroll}
                >
                    <Box sx={{ 
                        width: `${totalWidthPercentage}%`, 
                        minWidth: '100%',
                        height: '100%',
                        position: 'relative',
                    }}>
                        {/* Timeline editor */}
                        <TimelineEditor
                            words={allWords.map(item => item.word)}
                            startTime={0}
                            endTime={songDuration}
                            onWordUpdate={(index, updates) => handleWordUpdate(index, updates)}
                            currentTime={currentTime}
                            onPlaySegment={handlePlayFromTime}
                            showPlaybackIndicator={false} // Disable the built-in indicator to avoid duplication
                        />
                        
                        {/* Custom current time indicator */}
                        {currentTime >= 0 && currentTime <= songDuration && (
                            <Box
                                sx={{
                                    position: 'absolute',
                                    top: 0,
                                    left: `${(currentTime / songDuration) * 100}%`,
                                    width: '2px',
                                    height: '100%',
                                    backgroundColor: 'error.main',
                                    zIndex: 10,
                                }}
                            />
                        )}
                    </Box>
                </Box>
                
                {/* Time range indicator */}
                <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">
                        Visible: {visibleTimeRange.start.toFixed(1)}s - {visibleTimeRange.end.toFixed(1)}s
                    </Typography>
                    <Typography variant="body2">
                        Total Duration: {songDuration.toFixed(1)}s
                    </Typography>
                </Box>
                
                {/* Word count indicator */}
                <Typography variant="body2" sx={{ mt: 1 }}>
                    Total Words: {allWords.length}
                </Typography>
            </DialogContent>
            
            <DialogActions>
                <Button onClick={handleClose}>Cancel</Button>
                <Button onClick={handleSave} variant="contained" color="primary">Save</Button>
            </DialogActions>
        </Dialog>
    );
} 