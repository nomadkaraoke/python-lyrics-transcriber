import { Paper, Box, Typography, Chip, Tooltip } from '@mui/material'
import { WordCorrection } from '../types'
import { useMemo } from 'react'

interface GapCategoryMetric {
    category: string
    count: number
    avgConfidence: number
    corrections: WordCorrection[]
}

interface AgenticCorrectionMetricsProps {
    corrections: WordCorrection[]
    onCategoryClick?: (category: string) => void
    onConfidenceFilterClick?: (filter: 'low' | 'high') => void
}

export default function AgenticCorrectionMetrics({
    corrections,
    onCategoryClick,
    onConfidenceFilterClick
}: AgenticCorrectionMetricsProps) {
    
    const metrics = useMemo(() => {
        // Filter only agentic corrections
        const agenticCorrections = corrections.filter(c => c.handler === 'AgenticCorrector')
        
        // Parse category from reason string (format: "reason [CATEGORY] (confidence: XX%)")
        const categoryMap = new Map<string, GapCategoryMetric>()
        
        agenticCorrections.forEach(correction => {
            const categoryMatch = correction.reason?.match(/\[([A-Z_]+)\]/)
            const category = categoryMatch ? categoryMatch[1] : 'UNKNOWN'
            
            if (!categoryMap.has(category)) {
                categoryMap.set(category, {
                    category,
                    count: 0,
                    avgConfidence: 0,
                    corrections: []
                })
            }
            
            const metric = categoryMap.get(category)!
            metric.count++
            metric.corrections.push(correction)
        })
        
        // Calculate average confidence for each category
        categoryMap.forEach((metric) => {
            const totalConfidence = metric.corrections.reduce((sum, c) => sum + c.confidence, 0)
            metric.avgConfidence = totalConfidence / metric.count
        })
        
        // Convert to array and sort by count descending
        const sortedMetrics = Array.from(categoryMap.values()).sort((a, b) => b.count - a.count)
        
        // Calculate overall stats
        const totalCorrections = agenticCorrections.length
        const avgConfidence = totalCorrections > 0
            ? agenticCorrections.reduce((sum, c) => sum + c.confidence, 0) / totalCorrections
            : 0
        
        const lowConfidenceCount = agenticCorrections.filter(c => c.confidence < 0.6).length
        const highConfidenceCount = agenticCorrections.filter(c => c.confidence >= 0.8).length
        
        return {
            categories: sortedMetrics,
            totalCorrections,
            avgConfidence,
            lowConfidenceCount,
            highConfidenceCount
        }
    }, [corrections])
    
    // Format category name for display
    const formatCategory = (category: string): string => {
        return category
            .split('_')
            .map(word => word.charAt(0) + word.slice(1).toLowerCase())
            .join(' ')
    }
    
    // Get emoji/icon for category
    const getCategoryIcon = (category: string): string => {
        const icons: Record<string, string> = {
            'SOUND_ALIKE': '🎵',
            'PUNCTUATION_ONLY': '✏️',
            'BACKGROUND_VOCALS': '🎤',
            'EXTRA_WORDS': '➕',
            'REPEATED_SECTION': '🔁',
            'COMPLEX_MULTI_ERROR': '🔧',
            'AMBIGUOUS': '❓',
            'NO_ERROR': '✅'
        }
        return icons[category] || '📝'
    }
    
    return (
        <Paper
            sx={{
                p: 0.8,
                height: '100%',
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 0.5, fontSize: '0.7rem' }}>
                Agentic AI Corrections
            </Typography>
            
            {/* Overall stats */}
            <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontSize: '0.75rem', mb: 0.3 }}>
                    Total: <strong>{metrics.totalCorrections}</strong>
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.75rem', mb: 0.5 }}>
                    Avg Confidence: <strong>{(metrics.avgConfidence * 100).toFixed(0)}%</strong>
                </Typography>
                
                {/* Quick filters */}
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    <Chip
                        label={`Low (<60%): ${metrics.lowConfidenceCount}`}
                        size="small"
                        variant="outlined"
                        color="warning"
                        onClick={() => onConfidenceFilterClick?.('low')}
                        sx={{ fontSize: '0.65rem', height: '20px', cursor: 'pointer' }}
                    />
                    <Chip
                        label={`High (≥80%): ${metrics.highConfidenceCount}`}
                        size="small"
                        variant="outlined"
                        color="success"
                        onClick={() => onConfidenceFilterClick?.('high')}
                        sx={{ fontSize: '0.65rem', height: '20px', cursor: 'pointer' }}
                    />
                </Box>
            </Box>
            
            {/* Category breakdown */}
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 0.5, fontSize: '0.7rem' }}>
                By Category
            </Typography>
            <Box sx={{ flex: 1, overflow: 'auto' }}>
                {metrics.categories.map((metric) => (
                    <Box
                        key={metric.category}
                        sx={{
                            mb: 0.5,
                            p: 0.5,
                            borderRadius: 1,
                            cursor: 'pointer',
                            '&:hover': {
                                bgcolor: 'action.hover'
                            }
                        }}
                        onClick={() => onCategoryClick?.(metric.category)}
                    >
                        <Tooltip
                            title={`${metric.count} correction${metric.count !== 1 ? 's' : ''} • Avg confidence: ${(metric.avgConfidence * 100).toFixed(0)}%`}
                            placement="right"
                        >
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                    <span style={{ fontSize: '0.85rem' }}>{getCategoryIcon(metric.category)}</span>
                                    <Typography variant="body2" sx={{ fontSize: '0.7rem' }}>
                                        {formatCategory(metric.category)}
                                    </Typography>
                                </Box>
                                <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                                    <Typography variant="body2" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                                        {(metric.avgConfidence * 100).toFixed(0)}%
                                    </Typography>
                                    <Typography
                                        variant="body2"
                                        sx={{
                                            fontSize: '0.7rem',
                                            fontWeight: 600,
                                            bgcolor: 'action.selected',
                                            px: 0.5,
                                            borderRadius: 0.5,
                                            minWidth: '24px',
                                            textAlign: 'center'
                                        }}
                                    >
                                        {metric.count}
                                    </Typography>
                                </Box>
                            </Box>
                        </Tooltip>
                    </Box>
                ))}
                {metrics.categories.length === 0 && (
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.7rem', fontStyle: 'italic' }}>
                        No agentic corrections
                    </Typography>
                )}
            </Box>
        </Paper>
    )
}

