import warnings

warnings.simplefilter("ignore")

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from .transcriber import LyricsTranscriber

