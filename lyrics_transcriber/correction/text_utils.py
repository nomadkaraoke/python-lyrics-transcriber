import re


def clean_text(text: str) -> str:
    """Clean text by removing punctuation and normalizing whitespace.

    Args:
        text: Text to clean

    Returns:
        Cleaned text with:
        - All text converted to lowercase
        - Hyphens and slashes converted to spaces
        - All other punctuation removed
        - Multiple spaces/whitespace collapsed to single space
        - Leading/trailing whitespace removed
    """
    # Convert to lowercase
    text = text.lower()

    # Replace hyphens and slashes with spaces first
    text = text.replace("-", " ").replace("/", " ")

    # Remove remaining punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Normalize whitespace (collapse multiple spaces, remove leading/trailing)
    text = " ".join(text.split())

    return text
