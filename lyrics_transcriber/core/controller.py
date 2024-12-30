import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from ..transcribers.base_transcriber import BaseTranscriber, TranscriptionResult
from ..transcribers.audioshake import AudioShakeTranscriber, AudioShakeConfig
from ..transcribers.whisper import WhisperTranscriber, WhisperConfig
from ..lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig, LyricsData
from ..lyrics.genius import GeniusProvider
from ..lyrics.spotify import SpotifyProvider
from ..output.generator import OutputGenerator, OutputGeneratorConfig
from ..correction.corrector import LyricsCorrector, CorrectionResult


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

    output_dir: Optional[str] = os.getcwd()
    cache_dir: str = os.getenv("LYRICS_TRANSCRIBER_CACHE_DIR", "/tmp/lyrics-transcriber-cache/")
    render_video: bool = False
    video_resolution: str = "360p"
    video_background_image: Optional[str] = None
    video_background_color: str = "black"


@dataclass
class LyricsControllerResult:
    """Holds the results of the transcription and correction process."""

    # Results from different sources
    lyrics_results: List[LyricsData] = field(default_factory=list)
    transcription_results: List[TranscriptionResult] = field(default_factory=list)

    # Corrected results
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
        transcribers: Optional[Dict[str, BaseTranscriber]] = None,
        lyrics_providers: Optional[Dict[str, BaseLyricsProvider]] = None,
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

        # Add after creating necessary folders
        self.logger.debug(f"Using cache directory: {self.output_config.cache_dir}")
        self.logger.debug(f"Using output directory: {self.output_config.output_dir}")

        # Create necessary folders
        os.makedirs(self.output_config.cache_dir, exist_ok=True)
        os.makedirs(self.output_config.output_dir, exist_ok=True)

        # Initialize results
        self.results = LyricsControllerResult()

        # Initialize components (with dependency injection)
        self.transcribers = transcribers or self._initialize_transcribers()
        self.lyrics_providers = lyrics_providers or self._initialize_lyrics_providers()
        self.corrector = corrector or LyricsCorrector(logger=self.logger)
        self.output_generator = output_generator or self._initialize_output_generator()

    def _initialize_transcribers(self) -> Dict[str, BaseTranscriber]:
        """Initialize available transcription services."""
        transcribers = {}

        # Add debug logging for config values
        self.logger.debug(f"Initializing transcribers with config: {self.transcriber_config}")
        self.logger.debug(f"Using cache directory for transcribers: {self.output_config.cache_dir}")

        if self.transcriber_config.audioshake_api_token:
            self.logger.debug("Initializing AudioShake transcriber")
            transcribers["audioshake"] = {
                "instance": AudioShakeTranscriber(
                    cache_dir=self.output_config.cache_dir,
                    config=AudioShakeConfig(api_token=self.transcriber_config.audioshake_api_token),
                    logger=self.logger,
                ),
                "priority": 1,  # AudioShake has highest priority
            }
        else:
            self.logger.debug("Skipping AudioShake transcriber - no API token provided")

        if self.transcriber_config.runpod_api_key and self.transcriber_config.whisper_runpod_id:
            self.logger.debug("Initializing Whisper transcriber")
            transcribers["whisper"] = {
                "instance": WhisperTranscriber(
                    cache_dir=self.output_config.cache_dir,
                    config=WhisperConfig(
                        runpod_api_key=self.transcriber_config.runpod_api_key, endpoint_id=self.transcriber_config.whisper_runpod_id
                    ),
                    logger=self.logger,
                ),
                "priority": 2,  # Whisper has lower priority
            }
        else:
            self.logger.debug("Skipping Whisper transcriber - missing runpod_api_key or whisper_runpod_id")

        return transcribers

    def _initialize_lyrics_providers(self) -> Dict[str, BaseLyricsProvider]:
        """Initialize available lyrics providers."""
        providers = {}

        # Create provider config with all necessary parameters
        provider_config = LyricsProviderConfig(
            genius_api_token=self.lyrics_config.genius_api_token,
            spotify_cookie=self.lyrics_config.spotify_cookie,
            cache_dir=self.output_config.cache_dir,
            audio_filepath=self.audio_filepath,
        )

        if provider_config.genius_api_token:
            self.logger.debug("Initializing Genius lyrics provider")
            providers["genius"] = GeniusProvider(config=provider_config, logger=self.logger)
        else:
            self.logger.debug("Skipping Genius provider - no API token provided")

        if provider_config.spotify_cookie:
            self.logger.debug("Initializing Spotify lyrics provider")
            providers["spotify"] = SpotifyProvider(config=provider_config, logger=self.logger)
        else:
            self.logger.debug("Skipping Spotify provider - no cookie provided")

        return providers

    def _initialize_output_generator(self) -> OutputGenerator:
        """Initialize output generation service."""

        # Convert OutputConfig to OutputGeneratorConfig
        generator_config = OutputGeneratorConfig(
            output_dir=self.output_config.output_dir,
            cache_dir=self.output_config.cache_dir,
            video_resolution=self.output_config.video_resolution,
            video_background_image=self.output_config.video_background_image,
            video_background_color=self.output_config.video_background_color,
        )

        # Initialize output generator
        return OutputGenerator(config=generator_config, logger=self.logger)

    def process(self) -> LyricsControllerResult:
        """
        Main processing method that orchestrates the entire workflow.

        Returns:
            LyricsControllerResult containing all outputs and generated files.

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
            self.correct_lyrics()

            # Step 4: Generate outputs
            self.generate_outputs()

            self.logger.info("Processing completed successfully")
            return self.results

        except Exception as e:
            self.logger.error(f"Error during processing: {str(e)}")
            raise

    def fetch_lyrics(self) -> None:
        """Fetch lyrics from available providers."""
        self.logger.info(f"Fetching lyrics for {self.artist} - {self.title}")

        try:
            for name, provider in self.lyrics_providers.items():
                try:
                    result = provider.fetch_lyrics(self.artist, self.title)
                    if result:
                        self.results.lyrics_results.append(result)
                        self.logger.info(f"Successfully fetched lyrics from {name}")

                except Exception as e:
                    self.logger.error(f"Failed to fetch lyrics from {name}: {str(e)}")
                    continue

            if not self.results.lyrics_results:
                self.logger.warning("No lyrics found from any source")

        except Exception as e:
            self.logger.error(f"Failed to fetch lyrics: {str(e)}")
            # Don't raise - we can continue without lyrics

    def transcribe(self) -> None:
        """Run transcription using all available transcribers."""
        self.logger.info(f"Starting transcription with providers: {list(self.transcribers.keys())}")

        for name, transcriber_info in self.transcribers.items():
            self.logger.info(f"Running transcription with {name}")
            try:
                result = transcriber_info["instance"].transcribe(self.audio_filepath)
                if result:
                    # Add the transcriber name and priority to the result
                    self.results.transcription_results.append(
                        TranscriptionResult(name=name, priority=transcriber_info["priority"], result=result)
                    )
                    self.logger.debug(f"Transcription completed for {name}")

            except Exception as e:
                self.logger.error(f"Transcription failed for {name}: {str(e)}", exc_info=True)
                continue

        if not self.results.transcription_results:
            self.logger.warning("No successful transcriptions from any provider")

    def correct_lyrics(self) -> None:
        """Run lyrics correction using transcription and internet lyrics."""
        self.logger.info("Starting lyrics correction process")

        try:
            # Run correction
            corrected_data = self.corrector.run(
                transcription_results=self.results.transcription_results, lyrics_results=self.results.lyrics_results
            )

            # Store corrected results
            self.results.transcription_corrected = corrected_data
            self.logger.info("Lyrics correction completed")

        except Exception as e:
            self.logger.error(f"Failed to correct lyrics: {str(e)}", exc_info=True)

    def generate_outputs(self) -> None:
        """Generate output files."""
        self.logger.info("Generating output files")

        try:
            output_files = self.output_generator.generate_outputs(
                transcription_corrected=self.results.transcription_corrected,
                lyrics_results=self.results.lyrics_results,
                output_prefix=self.output_prefix,
                audio_filepath=self.audio_filepath,
            )

            # Store output paths - access attributes directly instead of using .get()
            self.results.lrc_filepath = output_files.lrc
            self.results.ass_filepath = output_files.ass
            self.results.video_filepath = output_files.video

        except Exception as e:
            self.logger.error(f"Failed to generate outputs: {str(e)}")
            raise
