import { useState } from 'react'
import { Box, Button, Typography, Grid, Paper, Modal } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import LyricsAnalyzer from './components/LyricsAnalyzer'
import { LyricsData } from './types'
import { COLORS } from './components/constants'

export default function App() {
  const [data, setData] = useState<LyricsData | null>(null)
  const [showMetadata, setShowMetadata] = useState(false)

  const handleFileLoad = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'

    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const newData = JSON.parse(text)
        setData(newData)
      } catch (error) {
        console.error('Error loading file:', error)
        alert('Error loading file. Please make sure it is a valid JSON file.')
      }
    }

    input.click()
  }

  const renderMetadataModal = () => {
    if (!data) return null

    return (
      <Modal
        open={showMetadata}
        onClose={() => setShowMetadata(false)}
        aria-labelledby="metadata-modal"
      >
        <Box sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 400,
          bgcolor: 'background.paper',
          boxShadow: 24,
          p: 4,
          borderRadius: 1,
        }}>
          <Typography variant="h6" gutterBottom>
            Correction Process Details
          </Typography>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Strategy
            </Typography>
            <Typography>
              {data.metadata.correction_strategy}
            </Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Total Words
            </Typography>
            <Typography>
              {data.metadata.total_words}
            </Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Correction Ratio
            </Typography>
            <Typography>
              {(data.metadata.correction_ratio * 100).toFixed(1)}%
            </Typography>
          </Box>
          {/* Add any other metadata fields that are available */}
        </Box>
      </Modal>
    )
  }

  if (!data) {
    return (
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">
            Lyrics Analysis
          </Typography>
          <Button
            variant="outlined"
            startIcon={<UploadFileIcon />}
            onClick={handleFileLoad}
          >
            Load File
          </Button>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Grid container spacing={2}>
            <Grid item xs={3}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Box
                    sx={{
                      width: 16,
                      height: 16,
                      borderRadius: 1,
                      bgcolor: COLORS.anchor,
                      mr: 1,
                    }}
                  />
                  <Typography variant="subtitle2" color="text.secondary">
                    Anchor Sequences
                  </Typography>
                </Box>
                <Typography variant="h6">
                  -
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Matched sections between transcription and reference
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={3}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Box
                    sx={{
                      width: 16,
                      height: 16,
                      borderRadius: 1,
                      bgcolor: COLORS.corrected,
                      mr: 1,
                    }}
                  />
                  <Typography variant="subtitle2" color="text.secondary">
                    Corrections Made
                  </Typography>
                </Box>
                <Typography variant="h6">
                  -
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Successfully fixed transcription errors
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={3}>
              <Paper sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Box
                    sx={{
                      width: 16,
                      height: 16,
                      borderRadius: 1,
                      bgcolor: COLORS.uncorrectedGap,
                      mr: 1,
                    }}
                  />
                  <Typography variant="subtitle2" color="text.secondary">
                    Uncorrected Gaps
                  </Typography>
                </Box>
                <Typography variant="h6">
                  -
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Sections that may need manual review
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={3}>
              <Paper
                sx={{
                  p: 2,
                  cursor: 'default', // Don't show pointer when there's no data
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Confidence Score
                  </Typography>
                </Box>
                <Typography variant="h6">
                  -
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Click for correction process details
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
          <Typography variant="h6" color="text.secondary">
            Select a lyrics analysis file to begin
          </Typography>
        </Box>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <LyricsAnalyzer
        data={data}
        onFileLoad={handleFileLoad}
        onShowMetadata={() => setShowMetadata(true)}
      />
      {renderMetadataModal()}
    </Box>
  )
}
