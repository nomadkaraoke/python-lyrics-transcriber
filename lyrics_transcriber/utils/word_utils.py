import shortuuid


class WordUtils:
    """Utility class for word-related operations."""

    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID for words/segments."""
        return shortuuid.uuid()
