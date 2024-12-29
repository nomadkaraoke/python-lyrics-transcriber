import os
import logging
from dataclasses import dataclass
from typing import Dict, Optional
from ..transcribers.base import BaseTranscriber
from ..transcribers.audioshake import AudioShakeTranscriber, AudioShakeConfig
from ..transcribers.whisper import WhisperTranscriber, WhisperConfig
from .fetcher import LyricsFetcher, LyricsFetcherConfig
from ..output.generator import OutputGenerator, OutputGeneratorConfig
from .corrector import LyricsCorrector, TranscriptionData, CorrectionResult


@dataclass
class TranscriberConfig:
    """Configuration for transcription services."""

    audioshake_api_token: Optional[str] = None
    runpod_api_key: Optional[str] = None
    whisper_runpod_id: Optional[str] = None


@dataclass
class LyricsConfig:
    """Configuration for lyrics services."""

    genius_api_token: Optional[str] = None
    spotify_cookie: Optional[str] = None


@dataclass
class OutputConfig:
    """Configuration for output generation."""

    output_dir: Optional[str] = None
    cache_dir: str = "/tmp/lyrics-transcriber-cache/"
    render_video: bool = False
    video_resolution: str = "360p"
    video_background_image: Optional[str] = None
    video_background_color: str = "black"


@dataclass
class TranscriptionResult:
    """Holds the results of the transcription and correction process."""

    # Lyrics from internet sources
    lyrics_text: Optional[str] = None
    lyrics_source: Optional[str] = None
    lyrics_genius: Optional[str] = None
    lyrics_spotify: Optional[str] = None
    spotify_lyrics_data: Optional[Dict] = None

    # Transcription results
    transcription_whisper: Optional[TranscriptionData] = None
    transcription_audioshake: Optional[TranscriptionData] = None
    transcription_primary: Optional[TranscriptionData] = None
    transcription_corrected: Optional[CorrectionResult] = None

    # Output files
    lrc_filepath: Optional[str] = None
    ass_filepath: Optional[str] = None
    video_filepath: Optional[str] = None


class LyricsTranscriber:
    """
    Controller class that orchestrates the lyrics transcription workflow:
    1. Fetch lyrics from internet sources
    2. Run multiple transcription methods
    3. Correct transcribed lyrics using fetched lyrics
    4. Generate output formats (LRC, ASS, video)
    """

    def __init__(
        self,
        audio_filepath: str,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        transcriber_config: Optional[TranscriberConfig] = None,
        lyrics_config: Optional[LyricsConfig] = None,
        output_config: Optional[OutputConfig] = None,
        lyrics_fetcher: Optional[LyricsFetcher] = None,
        corrector: Optional[LyricsCorrector] = None,
        output_generator: Optional[OutputGenerator] = None,
        logger: Optional[logging.Logger] = None,
        log_level: int = logging.DEBUG,
        log_formatter: Optional[logging.Formatter] = None,
    ):
        # Set up logging
        self.logger = logger or logging.getLogger(__name__)
        if not logger:
            self.logger.setLevel(log_level)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = log_formatter or logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

        self.logger.debug(f"LyricsTranscriber instantiating with input file: {audio_filepath}")

        # Store configs (with defaults if not provided)
        self.transcriber_config = transcriber_config or TranscriberConfig()
        self.lyrics_config = lyrics_config or LyricsConfig()
        self.output_config = output_config or OutputConfig()

        # Basic settings
        self.audio_filepath = audio_filepath
        self.artist = artist
        self.title = title
        self.output_prefix = f"{artist} - {title}" if artist and title else os.path.splitext(os.path.basename(audio_filepath))[0]

        # Create necessary folders
        os.makedirs(self.output_config.cache_dir, exist_ok=True)
        if self.output_config.output_dir:
            os.makedirs(self.output_config.output_dir, exist_ok=True)

        # Initialize results
        self.results = TranscriptionResult()

        # Initialize components (with dependency injection)
        self.transcribers = self._initialize_transcribers()
        self.lyrics_fetcher = lyrics_fetcher or self._initialize_lyrics_fetcher()
        self.corrector = corrector or LyricsCorrector(logger=self.logger)
        self.output_generator = output_generator or self._initialize_output_generator()

    def _initialize_transcribers(self) -> Dict[str, BaseTranscriber]:
        """Initialize available transcription services."""
        transcribers = {}

        # Add debug logging for config values
        self.logger.debug(f"Initializing transcribers with config: {self.transcriber_config}")

        if self.transcriber_config.audioshake_api_token:
            self.logger.debug("Initializing AudioShake transcriber")
            transcribers["audioshake"] = AudioShakeTranscriber(
                config=AudioShakeConfig(api_token=self.transcriber_config.audioshake_api_token), logger=self.logger
            )
        else:
            self.logger.debug("Skipping AudioShake transcriber - no API token provided")

        if self.transcriber_config.runpod_api_key and self.transcriber_config.whisper_runpod_id:
            self.logger.debug("Initializing Whisper transcriber")
            transcribers["whisper"] = WhisperTranscriber(
                config=WhisperConfig(
                    runpod_api_key=self.transcriber_config.runpod_api_key, endpoint_id=self.transcriber_config.whisper_runpod_id
                ),
                logger=self.logger,
            )
        else:
            self.logger.debug("Skipping Whisper transcriber - missing runpod_api_key or whisper_runpod_id")

        self.logger.debug(f"Initialized transcribers: {list(transcribers.keys())}")
        return transcribers

    def _initialize_lyrics_fetcher(self) -> LyricsFetcher:
        """Initialize lyrics fetching service."""
        return LyricsFetcher(
            config=LyricsFetcherConfig(
                genius_api_token=self.lyrics_config.genius_api_token, spotify_cookie=self.lyrics_config.spotify_cookie
            ),
            logger=self.logger,
        )

    def _initialize_output_generator(self) -> OutputGenerator:
        """Initialize output generation service."""

        # Convert OutputConfig to OutputGeneratorConfig
        generator_config = OutputGeneratorConfig(
            output_dir=self.output_config.output_dir if self.output_config else None,
            cache_dir=self.output_config.cache_dir if self.output_config else "/tmp/lyrics-transcriber-cache/",
            video_resolution=self.output_config.video_resolution if self.output_config else "360p",
            video_background_image=self.output_config.video_background_image if self.output_config else None,
            video_background_color=self.output_config.video_background_color if self.output_config else "black",
        )

        # Initialize output generator
        return OutputGenerator(config=generator_config, logger=self.logger)

    def process(self) -> TranscriptionResult:
        """
        Main processing method that orchestrates the entire workflow.

        Returns:
            TranscriptionResult containing all outputs and generated files.

        Raises:
            Exception: If a critical error occurs during processing.
        """
        try:
            # Step 1: Fetch lyrics if artist and title are provided
            if self.artist and self.title:
                self.fetch_lyrics()

            # Step 2: Run transcription
            self.transcribe()

            # Step 3: Process and correct lyrics
            if self.results.transcription_primary:
                self.correct_lyrics()

            # Step 4: Generate outputs
            if self.results.transcription_corrected:
                self.generate_outputs()

            self.logger.info("Processing completed successfully")
            return self.results

        except Exception as e:
            self.logger.error(f"Error during processing: {str(e)}")
            raise

    def fetch_lyrics(self) -> None:
        """Fetch lyrics from online sources."""
        self.logger.info(f"Fetching lyrics for {self.artist} - {self.title}")

        try:
            lyrics_result = self.lyrics_fetcher.fetch_lyrics(self.artist, self.title)

            # Update results
            self.results.lyrics_text = lyrics_result["lyrics"]
            self.results.lyrics_source = lyrics_result["source"]
            self.results.lyrics_genius = lyrics_result["genius_lyrics"]
            self.results.lyrics_spotify = lyrics_result["spotify_lyrics"]
            self.results.spotify_lyrics_data = lyrics_result.get("spotify_lyrics_data")

            if lyrics_result["lyrics"]:
                self.logger.info(f"Successfully fetched lyrics from {lyrics_result['source']}")
            else:
                self.logger.warning("No lyrics found from any source")

        except Exception as e:
            self.logger.error(f"Failed to fetch lyrics: {str(e)}")
            # Don't raise - we can continue without lyrics

    def transcribe(self) -> None:
        """Run transcription using all available transcribers."""
        self.logger.info(f"Starting transcription with providers: {list(self.transcribers.keys())}")

        for name, transcriber in self.transcribers.items():
            self.logger.info(f"Running transcription with {name}")
            try:
                result = transcriber.transcribe(self.audio_filepath)
                self.logger.debug(f"Transcription completed for {name}")

                # Store result based on transcriber type
                if name == "whisper":
                    self.results.transcription_whisper = result
                elif name == "audioshake":
                    self.results.transcription_audioshake = result

                # Use first successful transcription as primary
                if not self.results.transcription_primary:
                    self.results.transcription_primary = result
                    self.logger.debug(f"Set {name} transcription as primary")

            except Exception as e:
                self.logger.error(f"Transcription failed for {name}: {str(e)}", exc_info=True)
                continue

    def correct_lyrics(self) -> None:
        """Run lyrics correction using transcription and internet lyrics."""
        self.logger.info("Starting lyrics correction process")

        try:
            # Set input data for correction
            self.corrector.set_input_data(
                transcription_data_whisper=self.results.transcription_whisper,
                transcription_data_audioshake=self.results.transcription_audioshake,
                spotify_lyrics_data_dict=self.results.spotify_lyrics_data,
                spotify_lyrics_text=self.results.lyrics_spotify,
                genius_lyrics_text=self.results.lyrics_genius,
            )

            # Run correction
            corrected_data = self.corrector.run_corrector()
            # self.logger.debug(f"Correction result: {corrected_data}")

            # Store corrected results
            self.results.transcription_corrected = corrected_data
            self.logger.info("Lyrics correction completed")

        except Exception as e:
            self.logger.error(f"Failed to correct lyrics: {str(e)}", exc_info=True)  # Added exc_info for stack trace
            # Use uncorrected transcription as fallback
            self.results.transcription_corrected = self.results.transcription_primary
            self.logger.warning("Using uncorrected transcription as fallback")

    def generate_outputs(self) -> None:
        """Generate output files."""
        self.logger.info("Generating output files")

        try:
            output_files = self.output_generator.generate_outputs(
                transcription_data=self.results.transcription_corrected,
                output_prefix=self.output_prefix,
                audio_filepath=self.audio_filepath,
                render_video=self.output_config.render_video,
            )

            # Store output paths - access attributes directly instead of using .get()
            self.results.lrc_filepath = output_files.lrc
            self.results.ass_filepath = output_files.ass
            self.results.video_filepath = output_files.video

        except Exception as e:
            self.logger.error(f"Failed to generate outputs: {str(e)}")
            raise
