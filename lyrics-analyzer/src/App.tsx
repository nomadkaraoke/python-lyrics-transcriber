import { useState } from 'react'
import { Box, Container, CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import FileUpload from './components/FileUpload.tsx'
import LyricsAnalyzer from './components/LyricsAnalyzer.tsx'
import { LyricsData } from './types.ts'

const theme = createTheme({
  palette: {
    mode: 'light',
  },
})

function App() {
  const [lyricsData, setLyricsData] = useState<LyricsData | null>(null)

  const handleFileUpload = (data: LyricsData) => {
    setLyricsData(data)
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="xl">
        <Box sx={{ my: 4 }}>
          {!lyricsData ? (
            <FileUpload onUpload={handleFileUpload} />
          ) : (
            <LyricsAnalyzer data={lyricsData} />
          )}
        </Box>
      </Container>
    </ThemeProvider>
  )
}

export default App
