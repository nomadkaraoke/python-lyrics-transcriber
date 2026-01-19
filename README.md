# python-lyrics-transcriber (DEPRECATED)

> **This project has been deprecated and archived.**

The lyrics transcription functionality has been consolidated into [karaoke-gen](https://github.com/nomadkaraoke/karaoke-gen).

## Migration

For karaoke video generation with synchronized lyrics:
- Use [karaoke-gen](https://github.com/nomadkaraoke/karaoke-gen) - the complete karaoke generation solution
- Web app: https://gen.nomadkaraoke.com

## Historical Context

This library was originally developed as a standalone tool for creating synchronized lyrics files with word-level timestamps. It combined audio transcription (via AudioShake or Whisper), lyrics fetching from multiple sources (Genius, Spotify, Musixmatch, LRCLib), and intelligent correction algorithms to produce professional karaoke assets.

The functionality has now been integrated into the karaoke-gen platform, which provides a complete end-to-end solution for karaoke video generation including:
- Audio separation (vocals/instrumentals)
- Lyrics transcription and correction
- Human review interface
- Video rendering with title screens
- Distribution to YouTube, Dropbox, Google Drive

## Final Version

The last standalone version was **0.81.0** (December 2025). No further releases will be made to PyPI.

## License

MIT License - see [LICENSE](LICENSE) for details.
