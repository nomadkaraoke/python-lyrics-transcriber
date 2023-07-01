import os
import json
import hashlib
import datetime
import subprocess
import whisper_timestamped as whisper


class LyricsTranscriber:
    def __init__(
        self,
        audio_filepath=None,
        output_dir=None,
        cache_dir="/tmp/lyrics-transcriber-cache/",
    ):
        log(f"LyricsTranscriber instantiating with input file: {audio_filepath}")

        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.audio_filepath = audio_filepath

        self.whisper_result_dict = None

        if self.audio_filepath is None:
            raise Exception("audio_filepath must be specified as the input source to transcribe")

        self.create_folders()

    def generate(self):
        log(f"audio_filepath is set: {self.audio_filepath}, beginning initial whisper transcription")

        whisper_json_filepath = self.get_cache_filepath(".json")
        self.whisper_result_dict = self.transcribe(whisper_json_filepath)

        midico_lrc_filepath = self.get_cache_filepath(".lrc")
        self.write_midico_lrc_file(midico_lrc_filepath)

        singing_percentage, total_singing_duration, song_duration = self.calculate_singing_percentage()

        genius_lyrics_filepath = ""

        result_metadata = {
            "whisper_json_filepath": whisper_json_filepath,
            "genius_lyrics_filepath": genius_lyrics_filepath,
            "midico_lrc_filepath": midico_lrc_filepath,
            "singing_percentage": singing_percentage,
            "total_singing_duration": total_singing_duration,
            "song_duration": song_duration,
        }

        return result_metadata

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
        singing_percentage = (total_singing_duration / song_duration) * 100

        return singing_percentage, total_singing_duration, song_duration

    # Loops through lyrics segments (typically sentences) from whisper_timestamps JSON output,
    # then loops over each word and writes all words with MidiCo segment start/end formatting
    # and word-level timestamps to a MidiCo-compatible LRC file
    def write_midico_lrc_file(self, lrc_filename):
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

    def transcribe(self, whisper_cache_filepath):
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
