import logging
from enum import IntEnum
from typing import List

logging.getLogger().setLevel(logging.DEBUG)


class LyricMarker(IntEnum):
    SEGMENT_START = 1
    SEGMENT_END = 2


class LyricSegmentIterator:
    def __init__(self, lyrics_segments: List[str]):
        self._segments = lyrics_segments
        self._current_segment = None

    def __iter__(self):
        self._current_segment = 0
        return self

    def __next__(self):
        if self._current_segment >= len(self._segments):
            raise StopIteration
        val = self._segments[self._current_segment]
        self._current_segment += 1
        return val

    def __len__(self):
        return len(self._segments)
