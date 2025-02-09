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

ffmpeg -f lavfi -i color=c=green:s=3840x2160:r=30 \
    -i "$audio_file" \
    -vf "ass='$ass_file'" \
    -c:v libx264 -preset faster \
    -tune stillimage \
    -crf 28 \
    -movflags +faststart \
    -pix_fmt yuv420p \
    -c:a aac -b:a 320k \
    -shortest \
    with-vocals-greenscreen.mp4

# Rename the output file
mv with-vocals-greenscreen.mp4 "$title (With Vocals GreenScreen).mp4"
