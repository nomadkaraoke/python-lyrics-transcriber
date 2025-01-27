import difflib
import json
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from lyrics_transcriber.types import LyricsData, PhraseType, TranscriptionResult, CorrectionResult, AnchorSequence, GapSequence, PhraseScore
from lyrics_transcriber.transcribers.base_transcriber import BaseTranscriber
from lyrics_transcriber.transcribers.audioshake import AudioShakeTranscriber, AudioShakeConfig
from lyrics_transcriber.transcribers.whisper import WhisperTranscriber, WhisperConfig
from lyrics_transcriber.lyrics.base_lyrics_provider import BaseLyricsProvider, LyricsProviderConfig
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.spotify import SpotifyProvider
from lyrics_transcriber.output.generator import OutputGenerator
from lyrics_transcriber.correction.corrector import LyricsCorrector
from lyrics_transcriber.core.config import TranscriberConfig, LyricsConfig, OutputConfig


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
    mp3_filepath: Optional[str] = None
    cdg_filepath: Optional[str] = None
    cdg_zip_filepath: Optional[str] = None
    original_txt: Optional[str] = None
    corrected_txt: Optional[str] = None
    corrections_json: Optional[str] = None


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

        # Check if styles JSON is available for CDG and video features
        if not self.output_config.output_styles_json or not os.path.exists(self.output_config.output_styles_json):
            if self.output_config.generate_cdg or self.output_config.render_video:
                self.logger.warning(
                    f"Output styles JSON file not found: {self.output_config.output_styles_json}. "
                    "CDG and video generation will be disabled."
                )
                self.output_config.generate_cdg = False
                self.output_config.render_video = False

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
        self.corrector = corrector or LyricsCorrector(cache_dir=self.output_config.cache_dir, logger=self.logger)
        self.output_generator = output_generator or self._initialize_output_generator()

        # Log enabled features
        self.logger.info("Enabled features:")
        self.logger.info(f"  Lyrics fetching: {'enabled' if self.output_config.fetch_lyrics else 'disabled'}")
        self.logger.info(f"  Transcription: {'enabled' if self.output_config.run_transcription else 'disabled'}")
        self.logger.info(f"  Lyrics correction: {'enabled' if self.output_config.run_correction else 'disabled'}")
        self.logger.info(f"  Plain text output: {'enabled' if self.output_config.generate_plain_text else 'disabled'}")
        self.logger.info(f"  LRC file generation: {'enabled' if self.output_config.generate_lrc else 'disabled'}")
        self.logger.info(f"  CDG file generation: {'enabled' if self.output_config.generate_cdg else 'disabled'}")
        self.logger.info(f"  Video rendering: {'enabled' if self.output_config.render_video else 'disabled'}")
        if self.output_config.render_video:
            self.logger.info(f"    Video resolution: {self.output_config.video_resolution}")

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
        return OutputGenerator(config=self.output_config, logger=self.logger)

    def process(self) -> LyricsControllerResult:
        """Main processing method that orchestrates the entire workflow."""

        # Step 1: Fetch lyrics if enabled and artist/title are provided
        if self.output_config.fetch_lyrics and self.artist and self.title:
            self.fetch_lyrics()

        # Step 2: Run transcription if enabled
        if self.output_config.run_transcription:
            self.transcribe()

        # Step 3: Process and correct lyrics if enabled
        if self.output_config.run_correction:
            self.correct_lyrics()

        # Step 4: Generate outputs based on what's enabled and available
        self.generate_outputs()

        self.logger.info("Processing completed successfully")
        return self.results

    def fetch_lyrics(self) -> None:
        """Fetch lyrics from available providers."""
        self.logger.info(f"Fetching lyrics for {self.artist} - {self.title}")

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

    def transcribe(self) -> None:
        """Run transcription using all available transcribers."""
        self.logger.info(f"Starting transcription with providers: {list(self.transcribers.keys())}")

        for name, transcriber_info in self.transcribers.items():
            self.logger.info(f"Running transcription with {name}")
            result = transcriber_info["instance"].transcribe(self.audio_filepath)
            if result:
                # Add the transcriber name and priority to the result
                self.results.transcription_results.append(
                    TranscriptionResult(name=name, priority=transcriber_info["priority"], result=result)
                )
                self.logger.debug(f"Transcription completed for {name}")

        if not self.results.transcription_results:
            self.logger.warning("No successful transcriptions from any provider")

    def correct_lyrics(self) -> None:
        """Run lyrics correction using transcription and internet lyrics."""
        self.logger.info("Starting lyrics correction process")

        # Check if we have reference lyrics to work with
        if not self.results.lyrics_results:
            self.logger.warning("No reference lyrics available for correction - using raw transcription")
            # Use the highest priority transcription result as the "corrected" version
            if self.results.transcription_results:
                sorted_results = sorted(self.results.transcription_results, key=lambda x: x.priority)
                best_transcription = sorted_results[0]

                # Create a CorrectionResult with no corrections
                self.results.transcription_corrected = CorrectionResult(
                    original_segments=best_transcription.result.segments,
                    corrected_segments=best_transcription.result.segments,
                    corrected_text="",  # Will be generated from segments
                    corrections=[],  # No corrections made
                    corrections_made=0,  # No corrections made
                    confidence=1.0,  # Full confidence since we're using original
                    transcribed_text="",  # Will be generated from segments
                    reference_texts={},
                    anchor_sequences=[],
                    gap_sequences=[],
                    resized_segments=[],  # Will be populated later
                    metadata={"correction_type": "none", "reason": "no_reference_lyrics"},
                )
            return

        # Run correction if we have reference lyrics
        corrected_data = self.corrector.run(
            transcription_results=self.results.transcription_results, lyrics_results=self.results.lyrics_results
        )

        # Store corrected results
        self.results.transcription_corrected = corrected_data
        self.logger.info("Lyrics correction completed")

        # Add human review step
        if self.output_config.enable_review:
            from ..review import start_review_server
            import json
            from copy import deepcopy

            self.logger.info("Starting human review process")

            def normalize_data(data_dict):
                """Normalize numeric values in the data structure before JSON conversion."""
                if isinstance(data_dict, dict):
                    return {k: normalize_data(v) for k, v in data_dict.items()}
                elif isinstance(data_dict, list):
                    return [normalize_data(item) for item in data_dict]
                elif isinstance(data_dict, float):
                    # Convert whole number floats to integers
                    if data_dict.is_integer():
                        return int(data_dict)
                    return data_dict
                return data_dict

            # Normalize and convert auto-corrected data
            auto_data = normalize_data(deepcopy(self.results.transcription_corrected.to_dict()))
            auto_corrected_json = json.dumps(auto_data, indent=4).splitlines()

            # Pass through review server
            reviewed_data = start_review_server(self.results.transcription_corrected)

            # Normalize and convert reviewed data
            human_data = normalize_data(deepcopy(reviewed_data.to_dict()))
            human_corrected_json = json.dumps(human_data, indent=4).splitlines()

            self.logger.info("Human review completed")

            # Compare the normalized JSON strings
            diff = list(
                difflib.unified_diff(auto_corrected_json, human_corrected_json, fromfile="auto-corrected", tofile="human-corrected")
            )

            if diff:
                self.logger.warning("Changes made by human review:")
                for line in diff:
                    self.logger.warning(line.rstrip())

            # exit(1)

    def generate_outputs(self) -> None:
        """Generate output files based on enabled features and available data."""
        self.logger.info("Generating output files")

        # Only proceed with outputs that make sense based on what we have
        has_correction = bool(self.results.transcription_corrected)

        output_files = self.output_generator.generate_outputs(
            transcription_corrected=self.results.transcription_corrected if has_correction else None,
            lyrics_results=self.results.lyrics_results,
            output_prefix=self.output_prefix,
            audio_filepath=self.audio_filepath,
            artist=self.artist,
            title=self.title,
        )

        # Store results
        self.results.lrc_filepath = output_files.lrc
        self.results.ass_filepath = output_files.ass
        self.results.video_filepath = output_files.video
        self.results.original_txt = output_files.original_txt
        self.results.corrected_txt = output_files.corrected_txt
        self.results.corrections_json = output_files.corrections_json
        self.results.cdg_filepath = output_files.cdg
        self.results.mp3_filepath = output_files.mp3
        self.results.cdg_zip_filepath = output_files.cdg_zip
