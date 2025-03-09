import { createTheme } from '@mui/material/styles';

// Create a theme with smaller typography and spacing
const theme = createTheme({
  typography: {
    // Scale down all typography by about 20%
    fontSize: 14, // Default is 16
    h1: {
      fontSize: '2.5rem', // Default is ~3rem
    },
    h2: {
      fontSize: '2rem', // Default is ~2.5rem
    },
    h3: {
      fontSize: '1.5rem', // Default is ~1.75rem
    },
    h4: {
      fontSize: '1.2rem', // Default is ~1.5rem
      marginBottom: '0.5rem',
    },
    h5: {
      fontSize: '1rem', // Default is ~1.25rem
    },
    h6: {
      fontSize: '0.9rem', // Default is ~1.1rem
      marginBottom: '0.5rem',
    },
    body1: {
      fontSize: '0.85rem', // Default is ~1rem
    },
    body2: {
      fontSize: '0.75rem', // Default is ~0.875rem
    },
    button: {
      fontSize: '0.8rem', // Default is ~0.875rem
    },
    caption: {
      fontSize: '0.7rem', // Default is ~0.75rem
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          padding: '3px 10px', // Further reduced from 4px 12px
          minHeight: '30px', // Further reduced from 32px
        },
        sizeSmall: {
          padding: '1px 6px', // Further reduced from 2px 8px
          minHeight: '24px', // Further reduced from 28px
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          padding: '4px', // Further reduced from 6px
        },
        sizeSmall: {
          padding: '2px', // Further reduced from 4px
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiInputBase-root': {
            minHeight: '32px', // Further reduced from 36px
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          padding: '8px', // Further reduced from 12px
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          padding: '8px 12px', // Further reduced from 12px 16px
        },
      },
    },
    MuiDialogContent: {
      styleOverrides: {
        root: {
          padding: '6px 12px', // Further reduced from 8px 16px
        },
      },
    },
    MuiDialogActions: {
      styleOverrides: {
        root: {
          padding: '6px 12px', // Further reduced from 8px 16px
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          padding: '8px', // Further reduced from 12px
        },
      },
    },
    MuiList: {
      styleOverrides: {
        root: {
          padding: '2px 0', // Further reduced from 4px 0
        },
      },
    },
    MuiListItem: {
      styleOverrides: {
        root: {
          padding: '2px 8px', // Further reduced from 4px 12px
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          padding: '4px 8px', // Further reduced from 8px 12px
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          padding: '8px',
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: '8px',
          '&:last-child': {
            paddingBottom: '8px',
          },
        },
      },
    },
    MuiCardHeader: {
      styleOverrides: {
        root: {
          padding: '8px',
        },
      },
    },
    MuiCardActions: {
      styleOverrides: {
        root: {
          padding: '4px 8px',
        },
      },
    },
    MuiGrid: {
      styleOverrides: {
        container: {
          marginTop: '-4px',
          marginLeft: '-4px',
          width: 'calc(100% + 8px)',
        },
        item: {
          paddingTop: '4px',
          paddingLeft: '4px',
        },
      },
    },
  },
  spacing: (factor: number) => `${0.6 * factor}rem`, // Further reduced from 0.8 * factor
});

export default theme; 