// Add a global ref for the modal handler
let currentModalHandler: ((e: KeyboardEvent) => void) | undefined
let isModalOpen = false

type KeyboardState = {
    setIsShiftPressed: (value: boolean) => void
    setIsCtrlPressed: (value: boolean) => void
    modalHandler?: {
        isOpen: boolean
        onSpacebar?: (e: KeyboardEvent) => void
    }
}

// Add functions to update the modal handler state
export const setModalHandler = (handler: ((e: KeyboardEvent) => void) | undefined, open: boolean) => {
    currentModalHandler = handler
    isModalOpen = open
}

export const setupKeyboardHandlers = (state: KeyboardState) => {
    const handlerId = Math.random().toString(36).substr(2, 9)
    console.log(`Setting up keyboard handlers [${handlerId}]`)

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
            console.log(`[${handlerId}] Ignoring keydown in input/textarea`)
            return
        }

        if (e.key === 'Shift') {
            state.setIsShiftPressed(true)
            document.body.style.userSelect = 'none'
        } else if (e.key === 'Meta') {
            state.setIsCtrlPressed(true)
        } else if (e.key === ' ' || e.code === 'Space') {
            console.log(`[${handlerId}] Spacebar pressed:`, {
                modalOpen: isModalOpen,
                hasModalHandler: !!currentModalHandler,
                hasGlobalToggle: !!window.toggleAudioPlayback
            })
            
            e.preventDefault()
            
            // If modal is open and has a handler, use that
            if (isModalOpen && currentModalHandler) {
                console.log(`[${handlerId}] Using modal spacebar handler`)
                currentModalHandler(e)
            } 
            // Otherwise use global audio control
            else if (window.toggleAudioPlayback && !isModalOpen) {
                console.log(`[${handlerId}] Using global audio toggle`)
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