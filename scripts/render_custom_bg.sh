#!/bin/zsh

setopt extendedglob

# Find the original WAV file
local audio_file=(*\(Original\).wav)

# Find the CDG ASS file specifically
local ass_file=(lyrics/*Karaoke\).ass)

# Find the custom background image
local bg_image=(*\(Custom\ Background\).jpg)

# Extract the title by removing everything from " (Original).wav"
local title="${audio_file% \(Original\).wav}"

echo "Found audio file: $audio_file"
echo "Found lyrics file: $ass_file"
echo "Found background: $bg_image"
echo "Title: $title"

ffmpeg -i "$audio_file" \
    -loop 1 -i "$bg_image" \
    -vf "ass='$ass_file'" \
    -c:v libx264 -preset faster \
    -tune stillimage \
    -crf 28 \
    -movflags +faststart \
    -pix_fmt yuv420p \
    -c:a aac -b:a 320k \
    -shortest \
    with-vocals-custom.mp4

# Rename the output file
mv with-vocals-custom.mp4 "$title (With Vocals Custom).mp4"
