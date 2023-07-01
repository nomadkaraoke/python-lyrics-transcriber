import os
import re
import json
import shutil
import hashlib
import datetime
import subprocess
import whisper_timestamped as whisper
import lyricsgenius


class LyricsTranscriber:
    def __init__(
        self,
        audio_filepath,
        song_artist=None,
        song_title=None,
        genius_api_token=None,
        output_dir=None,
        cache_dir="/tmp/lyrics-transcriber-cache/",
    ):
        log(f"LyricsTranscriber instantiating with input file: {audio_filepath}")

        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.audio_filepath = audio_filepath
        self.song_artist = song_artist
        self.song_title = song_title
        self.genius_api_token = genius_api_token

        self.whisper_result_dict = None

        self.result_metadata = {
            "whisper_json_filepath": None,
            "genius_lyrics": None,
            "genius_lyrics_filepath": None,
            "midico_lrc_filepath": None,
            "singing_percentage": None,
            "total_singing_duration": None,
            "song_duration": None,
        }

        if self.audio_filepath is None:
            raise Exception("audio_filepath must be specified as the input source to transcribe")

        self.create_folders()

    def generate(self):
        log(f"audio_filepath is set: {self.audio_filepath}, beginning initial whisper transcription")

        self.result_metadata["whisper_json_filepath"] = self.get_cache_filepath(".json")
        self.whisper_result_dict = self.transcribe()

        self.result_metadata["midico_lrc_filepath"] = self.get_cache_filepath(".lrc")
        self.write_midico_lrc_file()

        self.calculate_singing_percentage()

        if self.genius_api_token and self.song_artist and self.song_title:
            log(f"fetching lyrics from Genius as genius_api_token, song_artist and song_title were set")
            self.result_metadata["genius_lyrics_filepath"] = self.get_cache_filepath("-genius.txt")
            self.write_genius_lyrics_file()
        else:
            log(f"not fetching lyrics from Genius as song_artist and song_title were not set")

        # TODO: attempt to match up segments from genius lyrics with whisper segments

        # TODO: output synced lyrics from self.whisper_result_dict in ASS format too, using code from the_tuul

        if self.output_dir is None:
            self.output_dir = os.getcwd()

        self.result_metadata["whisper_json_filepath"] = shutil.copy(self.result_metadata["whisper_json_filepath"], self.output_dir)
        self.result_metadata["midico_lrc_filepath"] = shutil.copy(self.result_metadata["midico_lrc_filepath"], self.output_dir)
        self.result_metadata["genius_lyrics_filepath"] = shutil.copy(self.result_metadata["genius_lyrics_filepath"], self.output_dir)

        return self.result_metadata

    def write_genius_lyrics_file(self):
        genius_lyrics_filepath = self.result_metadata["genius_lyrics_filepath"]
        if os.path.isfile(genius_lyrics_filepath):
            log(f"found existing file at genius_lyrics_filepath, reading: {genius_lyrics_filepath}")
            with open(genius_lyrics_filepath, "r") as cache_file:
                return cache_file

        genius = lyricsgenius.Genius(self.genius_api_token)

        song = genius.search_song(self.song_title, self.song_artist)
        if song is None:
            print(f'Could not find lyrics on Genius for "{self.song_title}" by {self.song_artist}')
            return
        lyrics = self.clean_genius_lyrics(song.lyrics)

        log(f"writing clean lyrics to genius_lyrics_filepath: {genius_lyrics_filepath}")
        with open(genius_lyrics_filepath, "w") as f:
            f.write(lyrics)

        self.result_metadata["genius_lyrics"] = lyrics
        return lyrics

    def clean_genius_lyrics(self, lyrics):
        lyrics = lyrics.replace("\\n", "\n")
        lyrics = re.sub(r"You might also like", "", lyrics)
        # Remove the song name and word "Lyrics" if this has a non-newline char at the start
        lyrics = re.sub(r".*?Lyrics([A-Z])", r"\1", lyrics)
        lyrics = re.sub(r"[0-9]+Embed$", "", lyrics)  # Remove the word "Embed" at end of line with preceding numbers if found
        lyrics = re.sub(r"(\S)Embed$", r"\1", lyrics)  # Remove the word "Embed" if it has been tacked onto a word at the end of a line
        lyrics = re.sub(r"^Embed$", r"", lyrics)  # Remove the word "Embed" if it has been tacked onto a word at the end of a line
        lyrics = re.sub(r".*?\[.*?\].*?", "", lyrics)  # Remove lines containing square brackets
        # add any additional cleaning rules here
        return lyrics

    def calculate_singing_percentage(self):
        # Calculate total seconds of singing using timings from whisper transcription results
        total_singing_duration = sum(segment["end"] - segment["start"] for segment in self.whisper_result_dict["segments"])

        log(f"calculated total_singing_duration: {int(total_singing_duration)} seconds, now running ffprobe")

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

        self.result_metadata["singing_percentage"] = singing_percentage
        self.result_metadata["total_singing_duration"] = total_singing_duration
        self.result_metadata["song_duration"] = song_duration

        return singing_percentage, total_singing_duration, song_duration

    # Loops through lyrics segments (typically sentences) from whisper_timestamps JSON output,
    # then loops over each word and writes all words with MidiCo segment start/end formatting
    # and word-level timestamps to a MidiCo-compatible LRC file
    def write_midico_lrc_file(self):
        lrc_filename = self.result_metadata["midico_lrc_filepath"]
        log(f"writing midico formatted word timestamps to LRC file: {lrc_filename}")
        with open(lrc_filename, "w") as f:
            f.write("[re:MidiCo]\n")
            for segment in self.whisper_result_dict["segments"]:
                for i, word in enumerate(segment["words"]):
                    start_time = self.format_time_lrc(word["start"])
                    if i != len(segment["words"]) - 1:
                        word["text"] += " "
                    line = "[{}]1:{}{}\n".format(start_time, "/" if i == 0 else "", word["text"])
                    f.write(line)

    def format_time_lrc(self, duration):
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        formatted_time = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        return formatted_time

    def transcribe(self):
        whisper_cache_filepath = self.result_metadata["whisper_json_filepath"]
        if os.path.isfile(whisper_cache_filepath):
            log(f"transcribe found existing file at whisper_cache_filepath, reading: {whisper_cache_filepath}")
            with open(whisper_cache_filepath, "r") as cache_file:
                return json.load(cache_file)

        log(f"no cached transcription file found, running whisper transcribe")
        audio = whisper.load_audio(self.audio_filepath)
        model = whisper.load_model("medium.en", device="cpu")
        result = whisper.transcribe(model, audio, language="en")

        log(f"whisper transcription complete, writing JSON to cache file: {whisper_cache_filepath}")
        with open(whisper_cache_filepath, "w") as cache_file:
            json.dump(result, cache_file, indent=2)

        return result

    def get_cache_filepath(self, extension):
        filename = os.path.split(self.audio_filepath)[1]
        hash_value = self.get_file_hash(self.audio_filepath)
        cache_filepath = os.path.join(self.cache_dir, filename + "_" + hash_value + extension)
        log(f"get_cache_filepath returning cache_filepath: {cache_filepath}")
        return cache_filepath

    def get_file_hash(self, filepath):
        return hashlib.md5(open(filepath, "rb").read()).hexdigest()

    def create_folders(self):
        if self.cache_dir is not None:
            os.makedirs(self.cache_dir, exist_ok=True)

        if self.output_dir is not None:
            os.makedirs(self.output_dir, exist_ok=True)


def log(message):
    timestamp = datetime.datetime.now().isoformat()
    print(f"{timestamp} - {message}")
