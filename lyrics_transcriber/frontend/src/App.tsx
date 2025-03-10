import UploadFileIcon from '@mui/icons-material/UploadFile'
import { Alert, Box, Button, Modal, Typography } from '@mui/material'
import { useEffect, useState } from 'react'
import { ApiClient, FileOnlyClient, LiveApiClient } from './api'
import CorrectionMetrics from './components/CorrectionMetrics'
import LyricsAnalyzer from './components/LyricsAnalyzer'
import { CorrectionData } from './types'

export default function App() {
  const [data, setData] = useState<CorrectionData | null>(null)
  const [showMetadata, setShowMetadata] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [apiClient, setApiClient] = useState<ApiClient | null>(null)
  const [isReadOnly, setIsReadOnly] = useState(true)
  const [audioHash, setAudioHash] = useState<string>('')

  useEffect(() => {
    // Parse query parameters
    const params = new URLSearchParams(window.location.search)
    const encodedApiUrl = params.get('baseApiUrl')
    const audioHashParam = params.get('audioHash')

    if (encodedApiUrl) {
      const baseApiUrl = decodeURIComponent(encodedApiUrl)
      setApiClient(new LiveApiClient(baseApiUrl))
      setIsReadOnly(false)
      if (audioHashParam) {
        setAudioHash(audioHashParam)
      }
      // Fetch initial data
      fetchData(baseApiUrl)
    } else {
      setApiClient(new FileOnlyClient())
      setIsReadOnly(true)
    }
  }, [])

  const fetchData = async (baseUrl: string) => {
    try {
      const client = new LiveApiClient(baseUrl)
      const data = await client.getCorrectionData()
      // console.log('Full correction data from API:', data)
      setData(data)
    } catch (err) {
      const error = err as Error
      setError(`Failed to fetch data: ${error.message}`)
    }
  }

  const handleFileLoad = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'

    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const parsedData = JSON.parse(text) as CorrectionData
        console.log('File data loaded:', {
          sampleGap: parsedData.gap_sequences?.[0],
          sampleWord: parsedData.corrected_segments?.[0]?.words?.[0],
          sampleCorrection: parsedData.corrections?.[0]
        })

        // Validate the structure
        if (!parsedData.corrected_segments || !parsedData.gap_sequences) {
          throw new Error('Invalid file format: missing required fields')
        }

        setData(parsedData)
      } catch (err) {
        const error = err as Error
        setError(`Error loading file: ${error.message}. Please make sure it is a valid JSON file.`)
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
              Total Words
            </Typography>
            <Typography>
              {data.metadata.total_words}
            </Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Gap Sequences
            </Typography>
            <Typography>
              {data.metadata.gap_sequences_count}
            </Typography>
          </Box>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Corrections Made
            </Typography>
            <Typography>
              {data.corrections_made}
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
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {isReadOnly ? (
          <>
            <Alert severity="info" sx={{ mb: 2 }}>
              Running in read-only mode. Connect to an API to enable editing.
            </Alert>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h4">
                Lyrics Correction Review
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
              <CorrectionMetrics />
            </Box>
          </>
        ) : (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
            <Typography variant="h6" color="text.secondary">
              Loading Lyrics Correction Review...
            </Typography>
          </Box>
        )}
      </Box>
    )
  }

  return (
    <Box sx={{
      p: 1.5,
      pb: 3,
      maxWidth: '100%',
      overflowX: 'hidden'
    }}>
      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {isReadOnly && (
        <Alert severity="info" sx={{ mb: 1 }}>
          Running in read-only mode. Connect to an API to enable editing.
        </Alert>
      )}
      <LyricsAnalyzer
        data={data}
        onFileLoad={handleFileLoad}
        onShowMetadata={() => setShowMetadata(true)}
        apiClient={apiClient}
        isReadOnly={isReadOnly}
        audioHash={audioHash}
      />
      {renderMetadataModal()}
    </Box>
  )
}
