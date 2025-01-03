#! /usr/bin/env python3
import json
import os
import webbrowser
from pathlib import Path
import tempfile
from typing import Dict, List


def load_lyrics_json(file_path: str) -> Dict:
    """Load and parse a lyrics correction JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_html_visualization(data: Dict) -> str:
    """Create an HTML visualization with transcribed text, anchor sequences, and reference text."""
    
    # Get the data
    text = data['transcribed_text']
    anchors = sorted(data['anchor_sequences'], key=lambda x: x['transcription_position'])
    reference_texts = data['reference_texts']
    
    # Split text into words while preserving whitespace and newlines
    def split_preserve_whitespace(text):
        parts = []
        current_word = []
        current_whitespace = []
        
        for char in text:
            if char.isspace():
                if current_word:
                    parts.append(('word', ''.join(current_word)))
                    current_word = []
                current_whitespace.append(char)
            else:
                if current_whitespace:
                    parts.append(('space', ''.join(current_whitespace)))
                    current_whitespace = []
                current_word.append(char)
                
        if current_word:
            parts.append(('word', ''.join(current_word)))
        if current_whitespace:
            parts.append(('space', ''.join(current_whitespace)))
            
        return parts

    # Process text into words and spaces
    text_parts = split_preserve_whitespace(text)
    
    # Create highlighted text
    word_index = 0
    highlighted_parts = []
    active_anchors = []
    
    for part_type, part_text in text_parts:
        if part_type == 'word':
            # Check if this word starts any new anchor sequences
            new_anchors = [a for a in anchors if a['transcription_position'] == word_index]
            for anchor in new_anchors:
                active_anchors.append((anchor, word_index + len(anchor['words'])))
            
            # Remove completed anchor sequences
            active_anchors = [(a, end) for a, end in active_anchors if word_index < end]
            
            if active_anchors:
                highlighted_parts.append(f'<span class="anchor" title="Confidence: {active_anchors[0][0]["confidence"]:.2%}">{part_text}</span>')
            else:
                highlighted_parts.append(part_text)
                
            word_index += 1
        else:
            highlighted_parts.append(part_text)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Lyrics Analysis</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif;
                max-width: 1400px;
                margin: 40px auto;
                padding: 20px;
                line-height: 1.6;
            }}
            .metadata {{
                color: #666;
                font-size: 0.9em;
                margin-bottom: 20px;
            }}
            .container {{
                display: flex;
                gap: 20px;
            }}
            .column {{
                flex: 1;
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}
            pre {{
                white-space: pre-wrap;
                font-family: monospace;
                margin: 0;
                line-height: 1.5;
            }}
            .anchor {{
                background-color: #90EE90;
                border-radius: 3px;
                padding: 2px 5px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .source-selector select {{
                padding: 5px;
                font-size: 14px;
            }}
        </style>
        <script>
            function updateReferenceText() {{
                const source = document.getElementById('source-select').value;
                const texts = {json.dumps(reference_texts)};
                document.getElementById('reference-text').textContent = texts[source];
            }}
        </script>
    </head>
    <body>
        <h1>Lyrics Analysis</h1>
        <div class="metadata">
            <p>Total anchor sequences: {len(anchors)}</p>
            <p>Confidence: {data['confidence']:.2%}</p>
            <p>Corrections made: {data['corrections_made']}</p>
        </div>
        <div class="container">
            <div class="column">
                <h2>Transcribed Text</h2>
                <pre>{text}</pre>
            </div>
            <div class="column">
                <h2>Highlighted Anchor Sequences</h2>
                <pre>{''.join(highlighted_parts)}</pre>
            </div>
            <div class="column">
                <div class="header">
                    <h2>Reference Text</h2>
                    <div class="source-selector">
                        <select id="source-select" onchange="updateReferenceText()">
                            {''.join(f'<option value="{source}">{source.title()}</option>' for source in reference_texts.keys())}
                        </select>
                    </div>
                </div>
                <pre id="reference-text">{next(iter(reference_texts.values()))}</pre>
            </div>
        </div>
        <script>
            // Initialize reference text
            updateReferenceText();
        </script>
    </body>
    </html>
    """
    
    return html_content


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
