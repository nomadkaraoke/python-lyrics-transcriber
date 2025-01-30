import { styled } from '@mui/system'
import { flashAnimation } from './constants'

export const HighlightedWord = styled('span')<{ shouldFlash: boolean }>(
    ({ shouldFlash }) => ({
        display: 'inline-block',
        marginRight: '0.25em',
        transition: 'background-color 0.2s ease',
        ...(shouldFlash && {
            animation: `${flashAnimation} 0.4s ease-in-out 3`,
        }),
    })
) 