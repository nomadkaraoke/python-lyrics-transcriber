type KeyboardState = {
    setIsShiftPressed: (value: boolean) => void
    setIsCtrlPressed: (value: boolean) => void
}

export const setupKeyboardHandlers = (state: KeyboardState) => {
    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
            return
        }

        if (e.key === 'Shift') {
            state.setIsShiftPressed(true)
            document.body.style.userSelect = 'none'
        } else if (e.key === 'Meta') {
            state.setIsCtrlPressed(true)
        } else if (e.key === ' ' || e.code === 'Space') {
            e.preventDefault()
            if (window.toggleAudioPlayback) {
                window.toggleAudioPlayback()
            }
        }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
        if (e.key === 'Shift') {
            state.setIsShiftPressed(false)
            document.body.style.userSelect = ''
        } else if (e.key === 'Meta') {
            state.setIsCtrlPressed(false)
        }
    }

    return { handleKeyDown, handleKeyUp }
} 