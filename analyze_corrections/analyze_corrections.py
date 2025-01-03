#! /usr/bin/env python3
import json
import os
import webbrowser
from pathlib import Path
import tempfile
from typing import Dict, List
import html


def split_preserve_whitespace(text: str) -> List[tuple[str, str]]:
    """Split text into words and whitespace while preserving both."""
    parts = []
    current_word = []
    current_whitespace = []

    for char in text:
        if char.isspace():
            if current_word:
                parts.append(("word", "".join(current_word)))
                current_word = []
            current_whitespace.append(char)
        else:
            if current_whitespace:
                parts.append(("space", "".join(current_whitespace)))
                current_whitespace = []
            current_word.append(char)

    if current_word:
        parts.append(("word", "".join(current_word)))
    if current_whitespace:
        parts.append(("space", "".join(current_whitespace)))

    return parts


def load_lyrics_json(file_path: str) -> Dict:
    """Load and parse a lyrics correction JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_tooltip_content(anchor: Dict) -> str:
    """Create detailed HTML tooltip content for an anchor sequence."""
    sources = list(anchor["reference_positions"].keys())
    source_text = "both sources" if len(sources) > 1 else sources[0]

    return f"""
        <div class='tooltip-content'>
            <div><strong>Text:</strong> "{anchor['text']}"</div>
            <div><strong>Found in:</strong> {source_text}</div>
            <div><strong>Confidence:</strong> {anchor['confidence']:.2%}</div>
            <div><strong>Length:</strong> {len(anchor['words'])} words</div>
            <div><strong>Position:</strong> word {anchor['transcription_position']}</div>
            <div><strong>Phrase type:</strong> {anchor['phrase_score']['phrase_type']}</div>
            <div><strong>Scores:</strong>
                <ul>
                    <li>Total: {anchor['total_score']:.2f}</li>
                    <li>Natural break: {anchor['phrase_score']['natural_break_score']:.2f}</li>
                    <li>Length: {anchor['phrase_score']['length_score']:.2f}</li>
                    <li>Phrase: {anchor['phrase_score']['total_score']:.2f}</li>
                </ul>
            </div>
        </div>
    """


def create_anchor_data(anchor: Dict) -> Dict:
    """Create a clean dictionary of anchor data for JSON serialization."""
    sources = list(anchor["reference_positions"].keys())
    return {
        "text": anchor["text"],
        "sources": "both sources" if len(sources) > 1 else sources[0],
        "confidence": anchor["confidence"],
        "length": len(anchor["words"]),
        "position": anchor["transcription_position"],
        "phraseType": anchor["phrase_score"]["phrase_type"],
        "scores": {
            "total": anchor["total_score"],
            "naturalBreak": anchor["phrase_score"]["natural_break_score"],
            "length": anchor["phrase_score"]["length_score"],
            "phrase": anchor["phrase_score"]["total_score"],
        },
    }


def highlight_text_with_anchors(text: str, anchors: List[Dict], source: str = None) -> str:
    """Highlight anchor sequences within text.
    If source is provided, only highlight sequences found in that source."""
    text_parts = split_preserve_whitespace(text)
    word_index = 0
    highlighted_parts = []
    active_anchors = []

    for part_type, part_text in text_parts:
        if part_type == "word":
            # Check if this word starts any new anchor sequences
            new_anchors = []
            if source:
                # For reference texts, only use anchors that exist in this source
                new_anchors = [a for a in anchors if source in a["reference_positions"] and a["reference_positions"][source] == word_index]
            else:
                # For transcribed text, use transcription_position
                new_anchors = [a for a in anchors if a["transcription_position"] == word_index]

            for anchor in new_anchors:
                seq_length = len(anchor["words"])
                active_anchors.append((anchor, word_index + seq_length))

            # Remove completed anchor sequences
            active_anchors = [(a, end) for a, end in active_anchors if word_index < end]

            if active_anchors:
                anchor = active_anchors[0][0]
                sources = set(anchor["reference_positions"].keys())
                color_class = "both-sources" if len(sources) > 1 else "spotify-only" if "spotify" in sources else "genius-only"
                anchor_data = create_anchor_data(anchor)
                highlighted_parts.append(
                    f'<span class="anchor {color_class}" ' f'data-info="{html.escape(json.dumps(anchor_data))}">{part_text}</span>'
                )
            else:
                highlighted_parts.append(part_text)

            word_index += 1
        else:
            highlighted_parts.append(part_text)

    return "".join(highlighted_parts)


def create_html_visualization(data: Dict) -> str:
    """Create an HTML visualization with highlighted anchor sequences and reference text."""
    # Get the data
    text = data["transcribed_text"]
    anchors = sorted(data["anchor_sequences"], key=lambda x: x["transcription_position"])
    reference_texts = data["reference_texts"]

    # Create the highlighted versions
    highlighted_transcription = highlight_text_with_anchors(text, anchors)
    highlighted_references = {
        source: highlight_text_with_anchors(ref_text, anchors, source=source) for source, ref_text in reference_texts.items()
    }

    with open("analyze_corrections/template.html", "r", encoding="utf-8") as f:
        template = f.read()

    return template.format(
        metadata=json.dumps(
            {"total_anchors": len(anchors), "confidence": data["confidence"], "corrections_made": data["corrections_made"]}
        ),
        highlighted_transcription=highlighted_transcription,
        reference_texts=json.dumps(highlighted_references),
    )


def analyze_file(file_path: str) -> None:
    """Analyze a single lyrics correction file and open visualization in browser."""
    # Load the JSON data
    data = load_lyrics_json(file_path)

    # Create HTML content
    html_content = create_html_visualization(data)

    # Create a temporary HTML file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html", encoding="utf-8") as f:
        f.write(html_content)
        temp_path = f.name

    # Open the HTML file in the default browser
    webbrowser.open("file://" + temp_path)


def main():
    """Main function to handle command line usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analyze_corrections.py <path_to_json_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    analyze_file(file_path)


if __name__ == "__main__":
    main()
