import os
import sys
import re
import json
import logging
import shutil
import hashlib
import subprocess
import slugify
import whisper_timestamped as whisper
import lyricsgenius
import syrics.api
from datetime import timedelta
from .utils import subtitles
from typing import List, Optional
from openai import OpenAI
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_exception_type
import requests


class LyricsTranscriber:
    def __init__(
        self,
        audio_filepath,
        artist=None,
        title=None,
        openai_api_key=None,
        audioshake_api_token=None,
        genius_api_token=None,
        spotify_cookie=None,
        output_dir=None,
        cache_dir="/tmp/lyrics-transcriber-cache/",
        log_level=logging.DEBUG,
        log_formatter=None,
        transcription_model="medium",
        llm_model="gpt-4o",
        llm_prompt_matching=None,
        llm_prompt_correction=None,
        render_video=False,
        video_resolution="360p",
        video_background_image=None,
        video_background_color="black",
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        self.log_level = log_level
        self.log_formatter = log_formatter

        self.log_handler = logging.StreamHandler()

        if self.log_formatter is None:
            self.log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)s - %(message)s")

        self.log_handler.setFormatter(self.log_formatter)
        self.logger.addHandler(self.log_handler)

        self.logger.debug(f"LyricsTranscriber instantiating with input file: {audio_filepath}")

        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.audio_filepath = audio_filepath
        self.artist = artist
        self.title = title
        self.song_known = self.artist is not None and self.title is not None

        self.openai_api_key = os.getenv("OPENAI_API_KEY", default=openai_api_key)
        self.genius_api_token = os.getenv("GENIUS_API_TOKEN", default=genius_api_token)
        self.spotify_cookie = os.getenv("SPOTIFY_COOKIE_SP_DC", default=spotify_cookie)
        self.audioshake_api_token = os.getenv("AUDIOSHAKE_API_TOKEN", default=audioshake_api_token)

        self.transcription_model = transcription_model
        self.llm_model = llm_model

        # Use package-relative paths for prompt files
        if llm_prompt_matching is None:
            llm_prompt_matching = os.path.join(
                os.path.dirname(__file__), "llm_prompts", "llm_prompt_lyrics_matching_andrew_handwritten_20231118.txt"
            )
        if llm_prompt_correction is None:
            llm_prompt_correction = os.path.join(
                os.path.dirname(__file__), "llm_prompts", "llm_prompt_lyrics_correction_andrew_handwritten_20231118.txt"
            )

        self.llm_prompt_matching = llm_prompt_matching
        self.llm_prompt_correction = llm_prompt_correction

        if not os.path.exists(self.llm_prompt_matching):
            raise FileNotFoundError(f"LLM prompt file not found: {self.llm_prompt_matching}")
        if not os.path.exists(self.llm_prompt_correction):
            raise FileNotFoundError(f"LLM prompt file not found: {self.llm_prompt_correction}")

        self.openai_client = None

        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)

            # Uncomment for local models e.g. with ollama
            # self.openai_client = OpenAI(
            #     base_url="http://localhost:11434/v1",
            #     api_key="ollama",
            # )

            self.openai_client.log = self.log_level
        else:
            self.logger.warning("No OpenAI API key found, no correction will be applied to transcription")

        self.render_video = render_video
        self.video_resolution = video_resolution
        self.video_background_image = video_background_image
        self.video_background_color = video_background_color

        match video_resolution:
            case "4k":
                self.video_resolution_num = (3840, 2160)
                self.font_size = 250
                self.line_height = 250
            case "1080p":
                self.video_resolution_num = (1920, 1080)
                self.font_size = 120
                self.line_height = 120
            case "720p":
                self.video_resolution_num = (1280, 720)
                self.font_size = 100
                self.line_height = 100
            case "360p":
                self.video_resolution_num = (640, 360)
                self.font_size = 50
                self.line_height = 50
            case _:
                raise ValueError("Invalid video_resolution value. Must be one of: 4k, 1080p, 720p, 360p")

        # If a video background is provided, validate file exists
        if self.video_background_image is not None:
            if os.path.isfile(self.video_background_image):
                self.logger.debug(f"video_background is valid file path: {self.video_background_image}")
            else:
                raise FileNotFoundError(f"video_background is not a valid file path: {self.video_background_image}")

        self.outputs = {
            "transcription_data_dict_whisper": None,
            "transcription_data_whisper_filepath": None,
            "transcribed_lyrics_text_whisper": None,
            "transcribed_lyrics_text_whisper_filepath": None,
            "transcription_data_dict_audioshake": None,
            "transcription_data_audioshake_filepath": None,
            "transcribed_lyrics_text_audioshake": None,
            "transcribed_lyrics_text_audioshake_filepath": None,
            "transcription_data_dict_primary": None,
            "transcription_data_primary_filepath": None,
            "transcribed_lyrics_text_primary": None,
            "transcribed_lyrics_text_primary_filepath": None,
            "genius_lyrics_text": None,
            "genius_lyrics_filepath": None,
            "spotify_lyrics_data_dict": None,
            "spotify_lyrics_data_filepath": None,
            "spotify_lyrics_text_filepath": None,
            "llm_token_usage": {"input": 0, "output": 0},
            "llm_costs_usd": {"input": 0.0, "output": 0.0, "total": 0.0},
            "llm_transcript": None,
            "llm_transcript_filepath": None,
            "corrected_lyrics_text": None,
            "corrected_lyrics_text_filepath": None,
            "midico_lrc_filepath": None,
            "ass_subtitles_filepath": None,
            "karaoke_video_filepath": None,
            "singing_percentage": None,
            "total_singing_duration": None,
            "song_duration": None,
            "output_dir": None,
        }

        if self.audio_filepath is None:
            raise Exception("audio_filepath must be specified as the input source to transcribe")

        self.create_folders()

        self.output_prefix = f"{artist} - {title}"

    def generate(self):
        self.logger.debug(f"Starting generate() with cache_dir: {self.cache_dir} and output_dir: {self.output_dir}")

        self.logger.debug(f"audio_filepath is set: {self.audio_filepath}, beginning initial whisper transcription")

        self.transcribe()

        self.write_transcribed_lyrics_plain_text()

        self.write_genius_lyrics_file()
        self.write_spotify_lyrics_data_file()
        self.write_spotify_lyrics_plain_text()

        self.validate_lyrics_match_song()

        if self.openai_client:
            self.write_corrected_lyrics_data_file()
            self.write_corrected_lyrics_plain_text()
        else:
            self.logger.warning("Skipping LLM correction as no OpenAI client is available")
            self.outputs["corrected_lyrics_data_dict"] = self.outputs["transcription_data_dict_primary"]
            self.write_corrected_lyrics_plain_text()

        self.calculate_singing_percentage()

        self.write_midico_lrc_file()
        self.write_ass_file()

        if self.render_video:
            self.outputs["karaoke_video_filepath"] = self.get_cache_filepath(".mp4")
            self.create_video()

        self.copy_files_to_output_dir()
        self.calculate_llm_costs()

        if self.openai_client:
            self.openai_client.close()

        return self.outputs

    def copy_files_to_output_dir(self):
        if self.output_dir is None:
            self.output_dir = os.getcwd()

        self.logger.debug(f"copying temporary files to output dir: {self.output_dir}")
        self.logger.debug("Files to copy:")
        for key, value in self.outputs.items():
            if key.endswith("_filepath"):
                self.logger.debug(f"  {key}: {value}")
                if value and os.path.isfile(value):
                    self.logger.debug(f"    File exists, copying to {self.output_dir}")
                    shutil.copy(value, self.output_dir)
                else:
                    self.logger.debug(f"    File doesn't exist or is None")

        self.outputs["output_dir"] = self.output_dir

    def validate_lyrics_match_song(self):
        at_least_one_online_lyrics_validated = False

        with open(self.llm_prompt_matching, "r") as file:
            llm_matching_instructions = file.read()

        for online_lyrics_source in ["genius", "spotify"]:
            self.logger.debug(f"validating transcribed lyrics match lyrics from {online_lyrics_source}")

            online_lyrics_text_key = f"{online_lyrics_source}_lyrics_text"
            online_lyrics_filepath_key = f"{online_lyrics_source}_lyrics_filepath"

            if online_lyrics_text_key not in self.outputs or self.outputs[online_lyrics_text_key] is None:
                continue

            if self.openai_client:
                data_input_str = f'Data input 1:\n{self.outputs["transcribed_lyrics_text_primary"]}\nData input 2:\n{self.outputs[online_lyrics_text_key]}\n'

                self.logger.debug(f"making API call to LLM model {self.llm_model} to validate {online_lyrics_source} lyrics match")
                response = self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "system", "content": llm_matching_instructions}, {"role": "user", "content": data_input_str}],
                )

                message = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                self.outputs["llm_token_usage"]["input"] += response.usage.prompt_tokens
                self.outputs["llm_token_usage"]["output"] += response.usage.completion_tokens

                if finish_reason == "stop":
                    if message == "Yes":
                        self.logger.info(f"{online_lyrics_source} lyrics successfully validated to match transcription")
                        at_least_one_online_lyrics_validated = True
                    elif message == "No":
                        self.logger.warning(f"{online_lyrics_source} lyrics do not match transcription, deleting that source from outputs")
                        self.outputs[online_lyrics_text_key] = None
                        self.outputs[online_lyrics_filepath_key] = None
                    else:
                        self.logger.error(f"Unexpected response from LLM: {message}")
                else:
                    self.logger.warning(f"OpenAI API call did not finish successfully, finish_reason: {finish_reason}")
            else:
                # Fallback primitive word matching
                self.logger.debug(f"Using primitive word matching to validate {online_lyrics_source} lyrics match")
                transcribed_words = set(self.outputs["transcribed_lyrics_text_primary"].split())
                online_lyrics_words = set(self.outputs[online_lyrics_text_key].split())
                common_words = transcribed_words & online_lyrics_words
                match_percentage = len(common_words) / len(online_lyrics_words) * 100

                if match_percentage >= 50:
                    self.logger.info(
                        f"{online_lyrics_source} lyrics successfully validated to match transcription with {match_percentage:.2f}% word match"
                    )
                    at_least_one_online_lyrics_validated = True
                else:
                    self.logger.warning(f"{online_lyrics_source} lyrics do not match transcription, deleting that source from outputs")
                    self.outputs[online_lyrics_text_key] = None
                    self.outputs[online_lyrics_filepath_key] = None

        self.logger.info(
            f"Completed validation of transcription using online lyrics sources. Match found: {at_least_one_online_lyrics_validated}"
        )

        if not at_least_one_online_lyrics_validated:
            self.logger.error(
                f"Lyrics from Genius and Spotify did not match the transcription. Please check artist and title are set correctly."
            )

    def write_corrected_lyrics_data_file(self):
        if not self.openai_client:
            self.logger.warning("Skipping LLM correction as no OpenAI client is available")
            return

        self.logger.debug("write_corrected_lyrics_data_file initiating OpenAI client")

        corrected_lyrics_data_json_cache_filepath = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics Corrected).json"))

        if os.path.isfile(corrected_lyrics_data_json_cache_filepath):
            self.logger.debug(
                f"found existing file at corrected_lyrics_data_json_cache_filepath, reading: {corrected_lyrics_data_json_cache_filepath}"
            )

            with open(corrected_lyrics_data_json_cache_filepath, "r") as corrected_lyrics_data_json:
                self.outputs["corrected_lyrics_data_filepath"] = corrected_lyrics_data_json_cache_filepath

                corrected_lyrics_data_dict = json.load(corrected_lyrics_data_json)
                self.outputs["corrected_lyrics_data_dict"] = corrected_lyrics_data_dict
                return

        reference_lyrics = self.outputs.get("genius_lyrics_text") or self.outputs.get("spotify_lyrics_text")

        if not reference_lyrics:
            self.logger.warning("No reference lyrics found from Genius or Spotify. Skipping LLM correction.")
            self.outputs["corrected_lyrics_data_dict"] = self.outputs["transcription_data_dict_primary"]
            return

        self.logger.debug(
            f"no cached lyrics found at corrected_lyrics_data_json_cache_filepath: {corrected_lyrics_data_json_cache_filepath}, attempting to run correction using LLM"
        )

        corrected_lyrics_dict = {"segments": []}

        with open(self.llm_prompt_correction, "r") as file:
            system_prompt_template = file.read()

        system_prompt = system_prompt_template.replace("{{reference_lyrics}}", reference_lyrics)

        # TODO: Test if results are cleaner when using the vocal file from a background vocal audio separation model
        # TODO: Record more info about the correction process (e.g before/after diffs for each segment) to a file for debugging
        # TODO: Possibly add a step after segment-based correct to get the LLM to self-analyse the diff

        self.outputs["llm_transcript"] = ""
        self.outputs["llm_transcript_filepath"] = os.path.join(self.cache_dir, self.get_output_filename(" (LLM Transcript).txt"))

        total_segments = len(self.outputs["transcription_data_dict_primary"]["segments"])
        self.logger.info(f"Beginning correction using LLM, total segments: {total_segments}")

        with open(self.outputs["llm_transcript_filepath"], "a", buffering=1, encoding="utf-8") as llm_transcript_file:
            self.logger.debug(f"writing LLM chat instructions: {self.outputs['llm_transcript_filepath']}")

            llm_transcript_header = f"--- SYSTEM instructions passed in for all segments ---:\n\n{system_prompt}\n"
            self.outputs["llm_transcript"] += llm_transcript_header
            llm_transcript_file.write(llm_transcript_header)

            for segment in self.outputs["transcription_data_dict_primary"]["segments"]:
                # # Don't waste OpenAI dollars when testing!
                # if segment["id"] > 10:
                #     continue
                # if segment["id"] < 20 or segment["id"] > 24:
                #     continue

                llm_transcript_segment = ""
                segment_input = json.dumps(
                    {
                        "id": segment["id"],
                        "start": segment["start"],
                        "end": segment["end"],
                        "confidence": segment["confidence"],
                        "text": segment["text"],
                        "words": segment["words"],
                    }
                )

                previous_two_corrected_lines = ""
                upcoming_two_uncorrected_lines = ""

                for previous_segment in corrected_lyrics_dict["segments"]:
                    if previous_segment["id"] in (segment["id"] - 2, segment["id"] - 1):
                        previous_two_corrected_lines += previous_segment["text"].strip() + "\n"

                for next_segment in self.outputs["transcription_data_dict_primary"]["segments"]:
                    if next_segment["id"] in (segment["id"] + 1, segment["id"] + 2):
                        upcoming_two_uncorrected_lines += next_segment["text"].strip() + "\n"

                llm_transcript_segment += f"--- Segment {segment['id']} / {total_segments} ---\n"
                llm_transcript_segment += f"Previous two corrected lines:\n\n{previous_two_corrected_lines}\nUpcoming two uncorrected lines:\n\n{upcoming_two_uncorrected_lines}\nData input:\n\n{segment_input}\n"

                # fmt: off
                segment_prompt = system_prompt_template.replace(
                    "{{previous_two_corrected_lines}}", previous_two_corrected_lines
                ).replace(
                    "{{upcoming_two_uncorrected_lines}}", upcoming_two_uncorrected_lines
                ).replace(
                    "{{segment_input}}", segment_input
                )

                self.logger.info(
                    f'Calling completion model {self.llm_model} with instructions and data input for segment {segment["id"]} / {total_segments}:'
                )

                response = self.openai_client.chat.completions.create(
                    model=self.llm_model,
                    response_format={"type": "json_object"},
                    seed=10,
                    temperature=0.4,
                    messages=[
                        {
                            "role": "user", 
                            "content": segment_prompt
                        }
                    ],
                )
                # fmt: on

                message = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                llm_transcript_segment += f"\n--- RESPONSE for segment {segment['id']} ---:\n\n"
                llm_transcript_segment += message
                llm_transcript_segment += f"\n--- END segment {segment['id']} / {total_segments} ---:\n\n"

                self.logger.debug(f"writing LLM chat transcript for segment to: {self.outputs['llm_transcript_filepath']}")
                llm_transcript_file.write(llm_transcript_segment)
                self.outputs["llm_transcript"] += llm_transcript_segment

                self.outputs["llm_token_usage"]["input"] += response.usage.prompt_tokens
                self.outputs["llm_token_usage"]["output"] += response.usage.completion_tokens

                # self.logger.debug(f"response finish_reason: {finish_reason} message: \n{message}")

                if finish_reason == "stop":
                    try:
                        corrected_segment_dict = json.loads(message)
                        corrected_lyrics_dict["segments"].append(corrected_segment_dict)
                        self.logger.info("Successfully parsed response from GPT as JSON and appended to corrected_lyrics_dict.segments")
                    except json.JSONDecodeError as e:
                        raise Exception("Failed to parse response from GPT as JSON") from e
                else:
                    self.logger.warning(f"OpenAI API call did not finish successfully, finish_reason: {finish_reason}")

            self.logger.info(f'Successfully processed correction for all {len(corrected_lyrics_dict["segments"])} lyrics segments')

            self.logger.debug(f"writing corrected lyrics data JSON filepath: {corrected_lyrics_data_json_cache_filepath}")
            with open(corrected_lyrics_data_json_cache_filepath, "w", encoding="utf-8") as corrected_lyrics_data_json_cache_file:
                corrected_lyrics_data_json_cache_file.write(json.dumps(corrected_lyrics_dict, indent=4))

        self.outputs["corrected_lyrics_data_filepath"] = corrected_lyrics_data_json_cache_filepath
        self.outputs["corrected_lyrics_data_dict"] = corrected_lyrics_dict

    def calculate_llm_costs(self):
        price_dollars_per_1000_tokens = {
            "gpt-3.5-turbo-1106": {
                "input": 0.0010,
                "output": 0.0020,
            },
            "gpt-4-1106-preview": {
                "input": 0.01,
                "output": 0.03,
            },
        }

        input_price = price_dollars_per_1000_tokens.get(self.llm_model, {"input": 0, "output": 0})["input"]
        output_price = price_dollars_per_1000_tokens.get(self.llm_model, {"input": 0, "output": 0})["output"]

        input_cost = input_price * (self.outputs["llm_token_usage"]["input"] / 1000)
        output_cost = output_price * (self.outputs["llm_token_usage"]["output"] / 1000)

        self.outputs["llm_costs_usd"]["input"] = round(input_cost, 3)
        self.outputs["llm_costs_usd"]["output"] = round(output_cost, 3)
        self.outputs["llm_costs_usd"]["total"] = round(input_cost + output_cost, 3)

    def write_corrected_lyrics_plain_text(self):
        if self.outputs["corrected_lyrics_data_dict"]:
            self.logger.debug(f"corrected_lyrics_data_dict exists, writing plain text lyrics file")

            corrected_lyrics_text_filepath = os.path.join(
                self.cache_dir, self.get_output_filename(" (Lyrics Corrected).txt")  # Updated to use consistent naming
            )
            self.outputs["corrected_lyrics_text_filepath"] = corrected_lyrics_text_filepath

            self.outputs["corrected_lyrics_text"] = ""

            self.logger.debug(f"writing lyrics plain text to corrected_lyrics_text_filepath: {corrected_lyrics_text_filepath}")
            with open(corrected_lyrics_text_filepath, "w", encoding="utf-8") as f:
                for corrected_segment in self.outputs["corrected_lyrics_data_dict"]["segments"]:
                    self.outputs["corrected_lyrics_text"] += corrected_segment["text"].strip() + "\n"
                    f.write(corrected_segment["text"].strip() + "\n")

    def write_spotify_lyrics_data_file(self):
        if self.spotify_cookie and self.song_known:
            self.logger.debug(f"attempting spotify fetch as spotify_cookie and song name was set")
        else:
            self.logger.warning(f"skipping spotify fetch as not all spotify params were set")
            return

        spotify_lyrics_data_json_cache_filepath = os.path.join(
            self.cache_dir, self.get_output_filename(" (Lyrics Spotify).json")  # Updated to use consistent naming
        )

        if os.path.isfile(spotify_lyrics_data_json_cache_filepath):
            self.logger.debug(
                f"found existing file at spotify_lyrics_data_json_cache_filepath, reading: {spotify_lyrics_data_json_cache_filepath}"
            )

            with open(spotify_lyrics_data_json_cache_filepath, "r") as spotify_lyrics_data_json:
                spotify_lyrics_data_dict = json.load(spotify_lyrics_data_json)
                self.outputs["spotify_lyrics_data_filepath"] = spotify_lyrics_data_json_cache_filepath
                self.outputs["spotify_lyrics_data_dict"] = spotify_lyrics_data_dict
                return

        self.logger.debug(
            f"no cached lyrics found at spotify_lyrics_data_json_cache_filepath: {spotify_lyrics_data_json_cache_filepath}, attempting to fetch from spotify"
        )

        spotify_lyrics_json = None

        try:
            spotify_client = syrics.api.Spotify(self.spotify_cookie)
            spotify_search_query = f"{self.title} - {self.artist}"
            spotify_search_results = spotify_client.search(spotify_search_query, type="track", limit=5)

            spotify_top_result = spotify_search_results["tracks"]["items"][0]
            self.logger.debug(
                f"spotify_top_result: {spotify_top_result['artists'][0]['name']} - {spotify_top_result['name']} ({spotify_top_result['external_urls']['spotify']})"
            )

            spotify_lyrics_dict = spotify_client.get_lyrics(spotify_top_result["id"])
            spotify_lyrics_json = json.dumps(spotify_lyrics_dict, indent=4)

            self.logger.debug(
                f"writing lyrics data JSON to spotify_lyrics_data_json_cache_filepath: {spotify_lyrics_data_json_cache_filepath}"
            )
            with open(spotify_lyrics_data_json_cache_filepath, "w", encoding="utf-8") as f:
                f.write(spotify_lyrics_json)
        except Exception as e:
            self.logger.warn(f"caught exception while attempting to fetch from spotify: ", e)

        self.outputs["spotify_lyrics_data_filepath"] = spotify_lyrics_data_json_cache_filepath
        self.outputs["spotify_lyrics_data_dict"] = spotify_lyrics_dict

    def write_spotify_lyrics_plain_text(self):
        if self.outputs["spotify_lyrics_data_dict"]:
            self.logger.debug(f"spotify_lyrics data found, checking/writing plain text lyrics file")

            spotify_lyrics_text_filepath = os.path.join(
                self.cache_dir, self.get_output_filename(" (Lyrics Spotify).txt")  # Updated to use consistent naming
            )
            self.outputs["spotify_lyrics_text_filepath"] = spotify_lyrics_text_filepath

            lines = self.outputs["spotify_lyrics_data_dict"]["lyrics"]["lines"]

            self.outputs["spotify_lyrics_text"] = ""

            self.logger.debug(f"writing lyrics plain text to spotify_lyrics_text_filepath: {spotify_lyrics_text_filepath}")
            with open(spotify_lyrics_text_filepath, "w", encoding="utf-8") as f:
                for line in lines:
                    self.outputs["spotify_lyrics_text"] += line["words"].strip() + "\n"
                    f.write(line["words"].strip() + "\n")

    @retry(
        stop=stop_after_delay(120),  # Stop after 2 minutes
        wait=wait_exponential(multiplier=1, min=4, max=60),  # Exponential backoff starting at 4 seconds
        retry=retry_if_exception_type(requests.exceptions.RequestException),  # Retry on request exceptions
        reraise=True,  # Reraise the last exception if all retries fail
    )
    def fetch_genius_lyrics(self, genius, title, artist):
        self.logger.debug(f"fetch_genius_lyrics attempting to fetch lyrics from Genius for {title} by {artist}")
        return genius.search_song(title, artist)

    def write_genius_lyrics_file(self):
        if self.genius_api_token and self.song_known:
            self.logger.debug(f"attempting genius fetch as genius_api_token and song name was set")
        else:
            self.logger.warning(f"skipping genius fetch as not all genius params were set")
            return

        genius_lyrics_cache_filepath = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics Genius).txt"))

        # Check cache first
        if os.path.isfile(genius_lyrics_cache_filepath):
            self.logger.debug(f"found existing file at genius_lyrics_cache_filepath, reading: {genius_lyrics_cache_filepath}")

            with open(genius_lyrics_cache_filepath, "r") as cached_lyrics:
                self.outputs["genius_lyrics_filepath"] = genius_lyrics_cache_filepath
                self.outputs["genius_lyrics_text"] = cached_lyrics.read()
                return
        self.logger.debug(f"no cached lyrics found at genius_lyrics_cache_filepath: {genius_lyrics_cache_filepath}, fetching from Genius")

        # Initialize Genius with better defaults
        genius = lyricsgenius.Genius(
            self.genius_api_token,
            verbose=(self.log_level == logging.DEBUG),
            remove_section_headers=True,
        )

        try:
            song = self.fetch_genius_lyrics(genius, self.title, self.artist)
            if song is None:
                self.logger.warning(f'Could not find lyrics on Genius for "{self.title}" by {self.artist}')
                return None

            lyrics = self.clean_genius_lyrics(song.lyrics)

            self.logger.debug(f"writing clean lyrics to genius_lyrics_cache_filepath: {genius_lyrics_cache_filepath}")
            with open(genius_lyrics_cache_filepath, "w", encoding="utf-8") as f:
                f.write(lyrics)

            self.outputs["genius_lyrics_filepath"] = genius_lyrics_cache_filepath
            self.outputs["genius_lyrics_text"] = lyrics
            return lyrics.split("\n")  # Return lines like write_lyrics_from_genius

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch lyrics from Genius after multiple retries: {e}")
            raise

    def clean_genius_lyrics(self, lyrics):
        lyrics = lyrics.replace("\\n", "\n")
        lyrics = re.sub(r"You might also like", "", lyrics)
        lyrics = re.sub(
            r".*?Lyrics([A-Z])", r"\1", lyrics
        )  # Remove the song name and word "Lyrics" if this has a non-newline char at the start
        lyrics = re.sub(r"^[0-9]* Contributors.*Lyrics", "", lyrics)  # Remove this example: 27 ContributorsSex Bomb Lyrics
        lyrics = re.sub(
            r"See.*Live.*Get tickets as low as \$[0-9]+", "", lyrics
        )  # Remove this example: See Tom Jones LiveGet tickets as low as $71
        lyrics = re.sub(r"[0-9]+Embed$", "", lyrics)  # Remove the word "Embed" at end of line with preceding numbers if found
        lyrics = re.sub(r"(\S)Embed$", r"\1", lyrics)  # Remove the word "Embed" if it has been tacked onto a word at the end of a line
        lyrics = re.sub(r"^Embed$", r"", lyrics)  # Remove the word "Embed" if it has been tacked onto a word at the end of a line
        lyrics = re.sub(r".*?\[.*?\].*?", "", lyrics)  # Remove lines containing square brackets
        # add any additional cleaning rules here
        return lyrics

    def calculate_singing_percentage(self):
        # Calculate total seconds of singing using timings from whisper transcription results
        total_singing_duration = sum(
            segment["end"] - segment["start"] for segment in self.outputs["transcription_data_dict_primary"]["segments"]
        )

        self.logger.debug(f"calculated total_singing_duration: {int(total_singing_duration)} seconds, now running ffprobe")

        # Calculate total song duration using ffprobe
        duration_command = [
            "ffprobe",
            "-i",
            self.audio_filepath,
            "-show_entries",
            "format=duration",
            "-v",
            "quiet",
            "-of",
            "csv=%s" % ("p=0"),
        ]
        duration_output = subprocess.check_output(duration_command, universal_newlines=True)
        song_duration = float(duration_output)

        # Calculate singing percentage
        singing_percentage = int((total_singing_duration / song_duration) * 100)

        self.outputs["singing_percentage"] = singing_percentage
        self.outputs["total_singing_duration"] = total_singing_duration
        self.outputs["song_duration"] = song_duration

    # Loops through lyrics segments (typically sentences) from whisper_timestamps JSON output,
    # then loops over each word and writes all words with MidiCo segment start/end formatting
    # and word-level timestamps to a MidiCo-compatible LRC file
    def write_midico_lrc_file(self):
        self.outputs["midico_lrc_filepath"] = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics Corrected).lrc"))

        lrc_filename = self.outputs["midico_lrc_filepath"]
        self.logger.debug(f"writing midico formatted word timestamps to LRC file: {lrc_filename}")
        with open(lrc_filename, "w", encoding="utf-8") as f:
            f.write("[re:MidiCo]\n")
            for segment in self.outputs["corrected_lyrics_data_dict"]["segments"]:
                for i, word in enumerate(segment["words"]):
                    start_time = self.format_time_lrc(word["start"])
                    if i != len(segment["words"]) - 1:
                        if not word["text"].endswith(" "):
                            self.logger.debug(f"word '{word['text']}' does not end with a space, adding one")
                            word["text"] += " "
                    line = "[{}]1:{}{}\n".format(start_time, "/" if i == 0 else "", word["text"])
                    f.write(line)

    def create_screens(self):
        self.logger.debug("create_screens beginning generation of screens from transcription results")
        screens: List[subtitles.LyricsScreen] = []
        screen: Optional[subtitles.LyricsScreen] = None

        max_lines_per_screen = 4
        max_line_length = 36  # Maximum characters per line
        self.logger.debug(f"Max lines per screen: {max_lines_per_screen}, Max line length: {max_line_length}")

        for segment in self.outputs["corrected_lyrics_data_dict"]["segments"]:
            self.logger.debug(f"Processing segment: {segment['text']}")
            if screen is None or len(screen.lines) >= max_lines_per_screen:
                screen = subtitles.LyricsScreen(video_size=self.video_resolution_num, line_height=self.line_height, logger=self.logger)
                screens.append(screen)
                self.logger.debug(f"Created new screen. Total screens: {len(screens)}")

            words = segment["words"]
            current_line = subtitles.LyricsLine()
            current_line_text = ""
            self.logger.debug(f"Processing {len(words)} words in segment")

            for word in words:
                self.logger.debug(f"Processing word: '{word['text']}'")
                if len(current_line_text) + len(word["text"]) + 1 > max_line_length or (current_line_text and word["text"][0].isupper()):
                    self.logger.debug(f"Current line would exceed max length or new capitalized word. Line: '{current_line_text}'")
                    if current_line.segments:
                        screen.lines.append(current_line)
                        self.logger.debug(f"Added line to screen. Lines on current screen: {len(screen.lines)}")
                        if len(screen.lines) >= max_lines_per_screen:
                            screen = subtitles.LyricsScreen(
                                video_size=self.video_resolution_num,
                                line_height=self.line_height,
                                logger=self.logger,
                            )
                            screens.append(screen)
                            self.logger.debug(f"Screen full, created new screen. Total screens: {len(screens)}")
                    current_line = subtitles.LyricsLine()
                    current_line_text = ""
                    self.logger.debug("Reset current line")

                current_line_text += (" " if current_line_text else "") + word["text"]

                # fmt: off
                lyric_segment = subtitles.LyricSegment(
                    text=word["text"], 
                    ts=timedelta(seconds=word["start"]), 
                    end_ts=timedelta(seconds=word["end"])
                )
                # fmt: on

                current_line.segments.append(lyric_segment)
                self.logger.debug(f"Added word to current line. Current line: '{current_line_text}'")

            if current_line.segments:
                screen.lines.append(current_line)
                self.logger.debug(f"Added final line of segment to screen. Lines on current screen: {len(screen.lines)}")

        self.logger.debug(f"Finished creating screens. Total screens created: {len(screens)}")
        return screens

    def write_ass_file(self):
        self.outputs["ass_subtitles_filepath"] = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics Corrected).ass"))

        ass_filepath = self.outputs["ass_subtitles_filepath"]
        self.logger.debug(f"writing ASS formatted subtitle file: {ass_filepath}")

        initial_screens = self.create_screens()
        screens = subtitles.set_segment_end_times(initial_screens, int(self.outputs["song_duration"]))
        screens = subtitles.set_screen_start_times(screens)
        lyric_subtitles_ass = subtitles.create_styled_subtitles(screens, self.video_resolution_num, self.font_size)
        lyric_subtitles_ass.write(ass_filepath)

    def resize_background_image(self):
        self.logger.debug(
            f"resize_background_image attempting to resize background image: {self.video_background_image} to resolution: {self.video_resolution}"
        )
        background_image_resized = self.get_cache_filepath(f"-{self.video_resolution}.png")

        if os.path.isfile(background_image_resized):
            self.logger.debug(
                f"resize_background_image found existing resized background image, skipping resize: {background_image_resized}"
            )
            return background_image_resized

        resize_command = ["ffmpeg", "-i", self.video_background_image]
        resize_command += ["-vf", f"scale={self.video_resolution_num[0]}x{self.video_resolution_num[1]}"]

        resize_command += [background_image_resized]
        subprocess.check_output(resize_command, universal_newlines=True)

        if not os.path.isfile(background_image_resized):
            raise FileNotFoundError(
                f"background_image_resized was not a valid file after running ffmpeg to resize: {background_image_resized}"
            )

        return background_image_resized

    def create_video(self):
        self.logger.debug(f"create_video attempting to generate video file: {self.outputs['karaoke_video_filepath']}")

        audio_delay = 0
        audio_delay_ms = int(audio_delay * 1000)  # milliseconds

        video_metadata = []
        if self.artist:
            video_metadata.append("-metadata")
            video_metadata.append(f"artist={self.artist}")
        if self.title:
            video_metadata.append("-metadata")
            video_metadata.append(f"title={self.title}")

        # fmt: off
        ffmpeg_cmd = [
            "ffmpeg",
            "-r", "30", # Set frame rate to 30 fps
        ]

        if self.video_background_image:
            self.logger.debug(f"background image set: {self.video_background_image}, resizing to resolution: {self.video_resolution}")

            background_image_resized = self.resize_background_image()

            ffmpeg_cmd += [
                # Use provided image as background
                "-loop", "1",  # Loop the image
                "-i", background_image_resized,  # Input image file
            ]

        else:
            self.logger.debug(f"background not set, using solid {self.video_background_color} background with resolution: {self.video_resolution}")
            ffmpeg_cmd += ["-f", "lavfi"]
            ffmpeg_cmd += ["-i", f"color=c={self.video_background_color}:s={self.video_resolution_num[0]}x{self.video_resolution_num[1]}:r=30"]


        # Check for hardware acclerated h.264 encoding and use if available
        video_codec = "libx264"
        ffmpeg_codes = subprocess.getoutput("ffmpeg -codecs")

        if "h264_videotoolbox" in ffmpeg_codes:
            video_codec = "h264_videotoolbox"
            self.logger.info(f"video codec set to hardware accelerated h264_videotoolbox")

        ffmpeg_cmd += [
            # Use accompaniment track as audio
            "-i", self.audio_filepath,
            # Set audio delay if needed
            # https://ffmpeg.org/ffmpeg-filters.html#adelay
            # "-af",
            # f"adelay=delays={audio_delay_ms}:all=1",
            # Re-encode audio as mp3
            "-c:a", "aac",
            # Add subtitles
            "-vf", "ass=" + self.outputs["ass_subtitles_filepath"],
            # Encode as H264 using hardware acceleration if available
            "-c:v", video_codec,
            # Increase output video quality
            "-preset", "slow",  # Use a slower preset for better compression efficiency
            # "-crf", "1",  # Lower CRF for higher quality. Adjust as needed, lower is better quality
            "-b:v", "5000k",  # Set the video bitrate, for example, 5000 kbps
            "-minrate", "5000k",  # Minimum bitrate
            "-maxrate", "20000k",  # Maximum bitrate
            "-bufsize", "10000k",  # Set the buffer size, typically 2x maxrate
            # End encoding after the shortest stream
            "-shortest",
            # Overwrite files without asking
            "-y",
            # Only encode the first 30 seconds (for testing, fast iteration when editing this)
            # "-t", "30",
            *video_metadata,
            # Output path of video
            self.outputs["karaoke_video_filepath"],
        ]
        # fmt: on

        self.logger.debug(f"running ffmpeg command to generate video: {' '.join(ffmpeg_cmd)}")
        ffmpeg_output = subprocess.check_output(ffmpeg_cmd, universal_newlines=True)
        return ffmpeg_output

    def format_time_lrc(self, duration):
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        formatted_time = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        return formatted_time

    def write_transcribed_lyrics_plain_text(self):
        if self.outputs["transcription_data_dict_whisper"]:
            transcribed_lyrics_text_whisper_filepath = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics Whisper).txt"))
            self.logger.debug(f"Setting Whisper text filepath to: {transcribed_lyrics_text_whisper_filepath}")
            self.outputs["transcribed_lyrics_text_whisper_filepath"] = transcribed_lyrics_text_whisper_filepath
            self.outputs["transcribed_lyrics_text_whisper"] = ""

            self.logger.debug(f"Writing Whisper lyrics to: {transcribed_lyrics_text_whisper_filepath}")
            with open(transcribed_lyrics_text_whisper_filepath, "w", encoding="utf-8") as f:
                for segment in self.outputs["transcription_data_dict_whisper"]["segments"]:
                    self.outputs["transcribed_lyrics_text_whisper"] += segment["text"] + "\n"
                    f.write(segment["text"].strip() + "\n")
            self.logger.debug(f"Finished writing Whisper lyrics, file exists: {os.path.exists(transcribed_lyrics_text_whisper_filepath)}")

        if self.outputs["transcription_data_dict_audioshake"]:
            transcribed_lyrics_text_audioshake_filepath = os.path.join(self.cache_dir, self.get_output_filename(" (Lyrics AudioShake).txt"))
            self.outputs["transcribed_lyrics_text_audioshake_filepath"] = transcribed_lyrics_text_audioshake_filepath
            self.outputs["transcribed_lyrics_text_audioshake"] = ""

            self.logger.debug(f"Writing AudioShake lyrics to: {transcribed_lyrics_text_audioshake_filepath}")
            with open(transcribed_lyrics_text_audioshake_filepath, "w", encoding="utf-8") as f:
                for segment in self.outputs["transcription_data_dict_audioshake"]["segments"]:
                    self.outputs["transcribed_lyrics_text_audioshake"] += segment["text"] + "\n"
                    f.write(segment["text"].strip() + "\n")

    def find_best_split_point(self, text, max_length):
        self.logger.debug(f"Finding best split point for text: '{text}' (max_length: {max_length})")
        words = text.split()
        mid_word_index = len(words) // 2
        mid_point = len(" ".join(words[:mid_word_index]))
        self.logger.debug(f"Mid point is at character {mid_point}")

        # Check for a comma within one or two words of the middle word
        if "," in text:
            comma_indices = [i for i, char in enumerate(text) if char == ","]
            self.logger.debug(f"Found commas at indices: {comma_indices}")
            for index in comma_indices:
                if abs(mid_point - index) < 20 and len(text[: index + 1].strip()) <= max_length:
                    self.logger.debug(f"Choosing comma at index {index} as split point")
                    return index + 1  # Include the comma in the first part

        # Check for 'and'
        if " and " in text:
            and_indices = [m.start() for m in re.finditer(" and ", text)]
            self.logger.debug(f"Found 'and' at indices: {and_indices}")
            for index in sorted(and_indices, key=lambda x: abs(x - mid_point)):
                if len(text[: index + len(" and ")].strip()) <= max_length:
                    self.logger.debug(f"Choosing 'and' at index {index} as split point")
                    return index + len(" and ")

        # Check for words starting with a capital letter
        capital_word_indices = [m.start() for m in re.finditer(r"\s[A-Z]", text)]
        self.logger.debug(f"Found capital words at indices: {capital_word_indices}")
        for index in sorted(capital_word_indices, key=lambda x: abs(x - mid_point)):
            if index > 0 and len(text[:index].strip()) <= max_length:
                self.logger.debug(f"Choosing capital word at index {index} as split point")
                return index

        # If no better split point is found, try splitting at the middle word
        if len(words) > 2 and mid_word_index > 0:
            split_at_middle = len(" ".join(words[:mid_word_index]))
            if split_at_middle <= max_length:
                self.logger.debug(f"Choosing middle word split at index {split_at_middle}")
                return split_at_middle

        # If the text is still too long, forcibly split at the maximum length
        self.logger.debug(f"No suitable split point found, forcibly splitting at max_length {max_length}")
        return max_length

    def split_long_segments(self, segments, max_length):
        self.logger.debug(f"Splitting long segments (max_length: {max_length})")
        new_segments = []
        for segment in segments:
            text = segment["text"]
            self.logger.debug(f"Processing segment: '{text}' (length: {len(text)})")
            if len(text) <= max_length:
                self.logger.debug("Segment is within max_length, keeping as is")
                new_segments.append(segment)
            else:
                self.logger.debug("Segment exceeds max_length, splitting")
                meta_words = segment["words"]
                current_text = ""
                current_start = segment["start"]
                current_words = []

                for i, meta in enumerate(meta_words):
                    word = meta["text"]
                    if current_text:
                        current_text += " "
                    current_text += word
                    current_words.append(meta)

                    should_split = len(current_text) > max_length or (i > 0 and word[0].isupper())
                    if should_split:
                        self.logger.debug(f"Splitting at: '{current_text}'")
                        # If splitting due to capitalization, don't include the capitalized word
                        if word[0].isupper() and len(current_text.strip()) > len(word):
                            split_text = current_text[: -(len(word) + 1)].strip()
                            current_words = current_words[:-1]
                        else:
                            split_text = current_text.strip()

                        new_segment = {"text": split_text, "start": current_start, "end": current_words[-1]["end"], "words": current_words}
                        new_segments.append(new_segment)
                        self.logger.debug(f"Added new segment: {new_segment}")

                        # Reset for next segment
                        if word[0].isupper() and len(current_text.strip()) > len(word):
                            current_text = word
                            current_words = [meta]
                        else:
                            current_text = ""
                            current_words = []
                        current_start = meta["start"]

                # Add any remaining text as a final segment
                if current_text:
                    self.logger.debug(f"Adding final segment: '{current_text}'")
                    new_segments.append(
                        {"text": current_text.strip(), "start": current_start, "end": segment["end"], "words": current_words}
                    )

        self.logger.debug(f"Splitting complete. Original segments: {len(segments)}, New segments: {len(new_segments)}")
        return new_segments

    def transcribe(self):
        # Check cache first
        transcription_cache_filepath_whisper = self.get_cache_filepath(" (Lyrics Whisper).json")
        transcription_cache_filepath_audioshake = self.get_cache_filepath(" (Lyrics AudioShake).json")

        self.logger.debug(f"Cache directory: {self.cache_dir}")
        self.logger.debug(f"Output directory: {self.output_dir}")

        if os.path.isfile(transcription_cache_filepath_whisper):
            self.logger.debug(f"Found existing Whisper transcription, reading: {transcription_cache_filepath_whisper}")
            with open(transcription_cache_filepath_whisper, "r") as cache_file:
                self.outputs["transcription_data_dict_whisper"] = json.load(cache_file)
                self.outputs["transcription_data_whisper_filepath"] = transcription_cache_filepath_whisper
                self.logger.debug(f"Loaded Whisper data and set filepath to: {self.outputs['transcription_data_whisper_filepath']}")

        if os.path.isfile(transcription_cache_filepath_audioshake):
            self.logger.debug(f"Found existing AudioShake transcription, reading: {transcription_cache_filepath_audioshake}")
            with open(transcription_cache_filepath_audioshake, "r") as cache_file:
                self.outputs["transcription_data_dict_audioshake"] = json.load(cache_file)
                self.outputs["transcription_data_audioshake_filepath"] = transcription_cache_filepath_audioshake

        # If we have both cached transcriptions, set primary and return early
        if self.outputs["transcription_data_dict_whisper"] and self.outputs["transcription_data_dict_audioshake"]:
            self.set_primary_transcription()
            return
        # If we have Whisper cached and AudioShake isn't available, set primary and return early
        elif self.outputs["transcription_data_dict_whisper"] and not self.audioshake_api_token:
            self.set_primary_transcription()
            return

        # Continue with transcription for any missing data...
        audioshake_job_id = None
        if self.audioshake_api_token and not self.outputs["transcription_data_dict_audioshake"]:
            self.logger.debug(f"Starting AudioShake transcription")
            from .audioshake_transcriber import AudioShakeTranscriber

            audioshake = AudioShakeTranscriber(api_token=self.audioshake_api_token, logger=self.logger, output_prefix=self.output_prefix)
            audioshake_job_id = audioshake.start_transcription(self.audio_filepath)

        # Run Whisper transcription if needed while AudioShake processes
        if not self.outputs["transcription_data_dict_whisper"]:
            self.logger.debug(f"Using Whisper for transcription with model: {self.transcription_model}")
            audio = whisper.load_audio(self.audio_filepath)
            model = whisper.load_model(self.transcription_model, device="cpu")
            whisper_data = whisper.transcribe(model, audio, language="en", beam_size=5, temperature=0.2, best_of=5)

            # Remove segments with no words, only music
            whisper_data["segments"] = [segment for segment in whisper_data["segments"] if segment["text"].strip() != "Music"]
            self.logger.debug(f"Removed 'Music' segments. Remaining segments: {len(whisper_data['segments'])}")

            # Split long segments
            self.logger.debug("Starting to split long segments")
            whisper_data["segments"] = self.split_long_segments(whisper_data["segments"], max_length=36)
            self.logger.debug(f"Finished splitting segments. Total segments after splitting: {len(whisper_data['segments'])}")

            # Store Whisper results
            self.outputs["transcription_data_dict_whisper"] = whisper_data
            self.outputs["transcription_data_whisper_filepath"] = transcription_cache_filepath_whisper
            with open(transcription_cache_filepath_whisper, "w") as cache_file:
                json.dump(whisper_data, cache_file, indent=4)

        # Now that Whisper is done, get AudioShake results if available
        if audioshake_job_id:
            self.logger.debug("Getting AudioShake results")
            audioshake_data = audioshake.get_transcription_result(audioshake_job_id)
            self.outputs["transcription_data_dict_audioshake"] = audioshake_data
            self.outputs["transcription_data_audioshake_filepath"] = transcription_cache_filepath_audioshake
            with open(transcription_cache_filepath_audioshake, "w") as cache_file:
                json.dump(audioshake_data, cache_file, indent=4)

        # Set the primary transcription source
        self.set_primary_transcription()

        # Write the text files
        self.write_transcribed_lyrics_plain_text()

    def set_primary_transcription(self):
        """Set the primary transcription source (AudioShake if available, otherwise Whisper)"""
        if self.outputs["transcription_data_dict_audioshake"]:
            self.logger.info("Using AudioShake as primary transcription source")
            self.outputs["transcription_data_dict_primary"] = self.outputs["transcription_data_dict_audioshake"]
            self.outputs["transcription_data_primary_filepath"] = self.outputs["transcription_data_audioshake_filepath"]

            # Set the primary text content
            if "transcribed_lyrics_text_audioshake" not in self.outputs or not self.outputs["transcribed_lyrics_text_audioshake"]:
                self.outputs["transcribed_lyrics_text_audioshake"] = "\n".join(
                    segment["text"].strip() for segment in self.outputs["transcription_data_dict_audioshake"]["segments"]
                )
            self.outputs["transcribed_lyrics_text_primary"] = self.outputs["transcribed_lyrics_text_audioshake"]
            self.outputs["transcribed_lyrics_text_primary_filepath"] = self.outputs["transcribed_lyrics_text_audioshake_filepath"]
        else:
            self.logger.info("Using Whisper as primary transcription source")
            self.outputs["transcription_data_dict_primary"] = self.outputs["transcription_data_dict_whisper"]
            self.outputs["transcription_data_primary_filepath"] = self.outputs["transcription_data_whisper_filepath"]

            # Set the primary text content
            if "transcribed_lyrics_text_whisper" not in self.outputs or not self.outputs["transcribed_lyrics_text_whisper"]:
                self.outputs["transcribed_lyrics_text_whisper"] = "\n".join(
                    segment["text"].strip() for segment in self.outputs["transcription_data_dict_whisper"]["segments"]
                )
            self.outputs["transcribed_lyrics_text_primary"] = self.outputs["transcribed_lyrics_text_whisper"]
            self.outputs["transcribed_lyrics_text_primary_filepath"] = self.outputs["transcribed_lyrics_text_whisper_filepath"]

    def get_cache_filepath(self, extension):
        # Instead of using slugify and hash, use the consistent naming pattern
        cache_filepath = os.path.join(self.cache_dir, self.get_output_filename(extension))
        self.logger.debug(f"get_cache_filepath returning cache_filepath: {cache_filepath}")
        return cache_filepath

    def get_song_slug(self):
        if not self.artist and not self.title:
            return "unknown_song_" + self.get_file_hash(self.audio_filepath)

        artist_slug = slugify.slugify(self.artist or "unknown_artist", lowercase=False)
        title_slug = slugify.slugify(self.title or "unknown_title", lowercase=False)
        return artist_slug + "-" + title_slug

    def get_file_hash(self, filepath):
        return hashlib.md5(open(filepath, "rb").read()).hexdigest()

    def create_folders(self):
        if self.cache_dir is not None:
            os.makedirs(self.cache_dir, exist_ok=True)

        if self.output_dir is not None:
            os.makedirs(self.output_dir, exist_ok=True)

    def get_output_filename(self, suffix):
        """Generate consistent filename with (Purpose) suffix pattern"""
        return f"{self.output_prefix}{suffix}"
