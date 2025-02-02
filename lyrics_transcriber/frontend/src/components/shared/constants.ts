import { keyframes } from '@mui/system'

export const COLORS = {
    anchor: '#e3f2fd', // Pale blue
    corrected: '#e8f5e9', // Pale green
    uncorrectedGap: '#fff3e0', // Pale orange
    highlighted: '#ffeb3b',  // or any color you prefer for highlighting
    playing: '#1976d2', // Blue
} as const

export const flashAnimation = keyframes`
  0%, 100% { 
    opacity: 1;
    background-color: inherit;
  }
  50% { 
    opacity: 0.6;
    background-color: ${COLORS.highlighted};
  }
` 