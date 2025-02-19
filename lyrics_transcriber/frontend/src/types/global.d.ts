declare global {
    interface Window {
        toggleAudioPlayback?: () => void;
        seekAndPlayAudio?: (startTime: number) => void;
        isAudioPlaying?: boolean;
    }
}

export {} 