import ReactDOM from 'react-dom/client'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App'
import theme from './theme'
// Import version from package.json
import packageJson from '../package.json'

// Log the frontend version when the app loads
console.log(`🎵 Lyrics Transcriber Frontend v${packageJson.version}`)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <App />
  </ThemeProvider>
)
