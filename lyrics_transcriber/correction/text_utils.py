import re


def clean_text(text: str) -> str:
    """Clean text by removing punctuation and normalizing whitespace.

    Args:
        text: Text to clean

    Returns:
        Cleaned text with:
        - All text converted to lowercase
        - Multiple spaces/whitespace collapsed to single space
        - Leading/trailing whitespace removed
        - Punctuation removed (except for internal hyphens/slashes in words)
    """
    # Convert to lowercase
    text = text.lower()

    # Remove punctuation except hyphens and slashes that are between word characters
    text = re.sub(r"(?<!\w)[^\w\s]|[^\w\s](?!\w)", "", text)

    # Normalize whitespace (collapse multiple spaces, remove leading/trailing)
    text = " ".join(text.split())

    return text
