#!/bin/zsh

setopt extendedglob

# Find the original WAV file
local audio_file=(*\(Original\).wav)

# Find the CDG ASS file specifically
local ass_file=(lyrics/*Karaoke\).ass)

# Extract the title by removing everything from " (Original).wav"
local title="${audio_file% \(Original\).wav}"

echo "Found audio file: $audio_file"
echo "Found lyrics file: $ass_file"
echo "Title: $title"

# Create a temporary copy of the ass file
cp "$ass_file" preview.ass

# Run ffmpeg with the temporary file
ffmpeg -f lavfi -i color=c=black:s=3840x2160:r=30 \
    -i "$audio_file" \
    -vf "ass=preview.ass" \
    -c:v libx264 -preset ultrafast \
    -tune stillimage \
    -crf 28 \
    -movflags +faststart \
    -pix_fmt yuv420p \
    -c:a aac -b:a 320k \
    -shortest \
    preview.mp4

# Clean up the temporary file
rm preview.ass
