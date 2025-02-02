interface LinePosition {
    position: number
    lineNumber: number
}

export function calculateReferenceLinePositions(): { linePositions: LinePosition[] } {
    const linePositions: LinePosition[] = []
    let lineNumber = 0

    // Simply add a line position at the start of each line
    linePositions.push({
        position: 0,
        lineNumber: lineNumber++
    })

    return { linePositions }
} 