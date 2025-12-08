# Countdown Padding Integration Example

This document shows how parent applications (like `karaoke-gen`) can use the countdown padding information returned by `LyricsTranscriber` to apply the same padding to other audio files.

## Overview

When `LyricsTranscriber` detects that a song starts within 3 seconds (vocals begin too quickly for karaoke singers), it:

1. Adds 3 seconds of silence to the start of the vocals audio
2. Shifts all lyrics timestamps by 3 seconds
3. Adds a "3... 2... 1..." countdown segment
4. Returns padding information in the result object

## Result Fields

The `LyricsControllerResult` object includes these fields:

```python
result.countdown_padding_added: bool       # True if padding was applied
result.countdown_padding_seconds: float    # Amount of padding (usually 3.0)
result.padded_audio_filepath: str         # Path to the padded audio file
```

## Integration Example for karaoke-gen

Here's how to integrate this into your karaoke generation workflow:

```python
from lyrics_transcriber import LyricsTranscriber
from lyrics_transcriber.core.controller import LyricsControllerResult
import subprocess
import os

def pad_audio_file(input_audio: str, output_audio: str, padding_seconds: float) -> None:
    """
    Pad an audio file with silence at the start using ffmpeg.
    
    Args:
        input_audio: Path to input audio file
        output_audio: Path for output padded audio file
        padding_seconds: Amount of silence to add in seconds
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-hide_banner",
        "-loglevel", "error",
        "-f", "lavfi",
        "-t", str(padding_seconds),
        "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
        "-i", input_audio,
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        "-c:a", "flac",  # Use lossless codec to preserve quality
        output_audio,
    ]
    
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def process_karaoke_track(
    vocals_audio: str,
    instrumental_audio: str,
    artist: str,
    title: str,
    output_dir: str,
    # ... other parameters
):
    """
    Process a karaoke track with countdown support.
    """
    
    # Step 1: Process vocals and get lyrics
    transcriber = LyricsTranscriber(
        audio_filepath=vocals_audio,
        artist=artist,
        title=title,
        # ... configs
    )
    
    result: LyricsControllerResult = transcriber.process()
    
    # Step 2: Check if countdown padding was added
    if result.countdown_padding_added:
        padding_seconds = result.countdown_padding_seconds
        print(f"Countdown padding detected: {padding_seconds}s added to vocals")
        
        # Step 3: Apply the same padding to instrumental track
        padded_instrumental = os.path.join(
            output_dir, 
            f"{artist} - {title} (Instrumental - Padded).flac"
        )
        
        print(f"Applying {padding_seconds}s padding to instrumental track...")
        pad_audio_file(instrumental_audio, padded_instrumental, padding_seconds)
        
        # Step 4: Use padded audio files for remuxing
        vocals_for_remux = result.padded_audio_filepath
        instrumental_for_remux = padded_instrumental
        
        print("✓ Both vocals and instrumental are now synchronized with countdown")
    else:
        # No padding needed - use original files
        vocals_for_remux = vocals_audio
        instrumental_for_remux = instrumental_audio
        print("No countdown padding needed - vocals start after 3 seconds")
    
    # Step 5: Continue with remuxing process using synchronized audio
    remux_karaoke_video(
        vocals_audio=vocals_for_remux,
        instrumental_audio=instrumental_for_remux,
        video_file=result.video_filepath,
        # ... other parameters
    )
    
    return result
```

## Advanced: Applying Padding to Multiple Audio Stems

If you're working with multiple stems (vocals, bass, drums, other), you can apply padding to all of them:

```python
def pad_all_stems(stems_dir: str, padding_seconds: float, output_dir: str):
    """
    Apply the same padding to all audio stems in a directory.
    
    Args:
        stems_dir: Directory containing stem files
        padding_seconds: Amount of padding to apply
        output_dir: Directory for padded stems
    """
    import glob
    
    os.makedirs(output_dir, exist_ok=True)
    
    stem_files = glob.glob(os.path.join(stems_dir, "*.flac"))
    
    for stem_file in stem_files:
        basename = os.path.basename(stem_file)
        name, ext = os.path.splitext(basename)
        output_file = os.path.join(output_dir, f"{name}_padded{ext}")
        
        print(f"Padding {basename}...")
        pad_audio_file(stem_file, output_file, padding_seconds)
    
    print(f"✓ Padded {len(stem_files)} stem files")


# Usage in your workflow:
result = transcriber.process()

if result.countdown_padding_added:
    pad_all_stems(
        stems_dir="path/to/stems",
        padding_seconds=result.countdown_padding_seconds,
        output_dir="path/to/padded_stems"
    )
```

## Key Points

1. **Always check `countdown_padding_added`** - Only apply padding to other files if this is `True`
2. **Use the exact same `padding_seconds`** value for all audio files to maintain synchronization
3. **Preserve audio quality** - Use lossless codecs (FLAC) when padding to avoid quality loss
4. **Update all references** - Make sure your remuxing/mixing code uses the padded files when padding was applied
5. **Log the padding** - Keep track of which files were padded for debugging

## Troubleshooting

**Q: The countdown appears in the video but my instrumental is still out of sync**  
A: Make sure you're using the padded instrumental file in your final mix. Check that `padding_seconds` matches exactly.

**Q: Can I disable the countdown for specific songs?**  
A: Yes, set `add_countdown=False` in `OutputConfig` when creating the transcriber.

**Q: How do I know if a pre-existing track has countdown padding?**  
A: Check the corrections JSON file - it will contain the countdown segment at the start if padding was applied.

## See Also

- [LyricsTranscriber API Documentation](README.md#using-as-a-library)
- [FFmpeg Documentation](https://ffmpeg.org/ffmpeg.html)

