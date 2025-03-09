// Add a global ref for the modal handler
let currentModalHandler: ((e: KeyboardEvent) => void) | undefined
let isModalOpen = false

type KeyboardState = {
    setIsShiftPressed: (value: boolean) => void
    setIsCtrlPressed?: (value: boolean) => void
    modalHandler?: {
        isOpen: boolean
        onSpacebar?: (e: KeyboardEvent) => void
    }
}

// Add functions to update the modal handler state
export const setModalHandler = (handler: ((e: KeyboardEvent) => void) | undefined, open: boolean) => {
    console.log('setModalHandler called', {
        hasHandler: !!handler,
        open,
        previousState: {
            hadHandler: !!currentModalHandler,
            wasOpen: isModalOpen
        }
    })
    currentModalHandler = handler
    isModalOpen = open
}

export const setupKeyboardHandlers = (state: KeyboardState) => {
    const handlerId = Math.random().toString(36).substr(2, 9)
    console.log(`Setting up keyboard handlers [${handlerId}]`)

    const handleKeyDown = (e: KeyboardEvent) => {
        console.log(`Keyboard event captured [${handlerId}]`, {
            key: e.key,
            code: e.code,
            type: e.type,
            target: e.target,
            currentTarget: e.currentTarget,
            eventPhase: e.eventPhase,
            isModalOpen,
            hasModalHandler: !!currentModalHandler
        })

        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
            console.log(`[${handlerId}] Ignoring keydown in input/textarea`)
            return
        }

        if (e.key === 'Shift') {
            state.setIsShiftPressed(true)
            document.body.style.userSelect = 'none'
        } else if (e.key === 'Meta') {
            state.setIsCtrlPressed?.(true)
        } else if (e.key === ' ' || e.code === 'Space') {
            console.log('Keyboard handler - Spacebar pressed down', {
                modalOpen: isModalOpen,
                hasModalHandler: !!currentModalHandler,
                hasGlobalToggle: !!window.toggleAudioPlayback,
                target: e.target,
                eventPhase: e.eventPhase,
                handlerFunction: currentModalHandler?.toString().slice(0, 100)
            })

            e.preventDefault()

            if (isModalOpen && currentModalHandler) {
                console.log('Keyboard handler - Delegating to modal handler')
                currentModalHandler(e)
            } else if (window.toggleAudioPlayback && !isModalOpen) {
                console.log('Keyboard handler - Using global audio toggle')
                window.toggleAudioPlayback()
            }
        }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
        console.log(`Keyboard up event captured [${handlerId}]`, {
            key: e.key,
            code: e.code,
            type: e.type,
            target: e.target,
            eventPhase: e.eventPhase,
            isModalOpen,
            hasModalHandler: !!currentModalHandler
        })

        if (e.key === 'Shift') {
            state.setIsShiftPressed(false)
            document.body.style.userSelect = ''
        } else if (e.key === 'Meta') {
            state.setIsCtrlPressed?.(false)
        } else if (e.key === ' ' || e.code === 'Space') {
            console.log('Keyboard handler - Spacebar released', {
                modalOpen: isModalOpen,
                hasModalHandler: !!currentModalHandler,
                target: e.target,
                eventPhase: e.eventPhase
            })

            e.preventDefault()

            if (isModalOpen && currentModalHandler) {
                console.log('Keyboard handler - Delegating keyup to modal handler')
                currentModalHandler(e)
            }
        }
    }

    return { handleKeyDown, handleKeyUp }
}

// Export these for external use
export const getModalState = () => ({
    currentModalHandler,
    isModalOpen
}) 