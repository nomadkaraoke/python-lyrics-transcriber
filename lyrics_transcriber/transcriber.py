import os
import json
import hashlib
import datetime
import whisper_timestamped as whisper


class LyricsTranscriber:
    def __init__(
        self,
        audio_filepath=None,
        output_dir=None,
        cache_dir="/tmp/lyrics-transcriber-cache/",
    ):
        log("LyricsTranscriber initializing")

        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.audio_filepath = audio_filepath

        if self.audio_filepath is None:
            raise Exception("audio_filepath must be specified as the input source to transcribe")

        self.create_folders()

    def get_file_hash(self, filepath):
        return hashlib.md5(open(filepath, "rb").read()).hexdigest()

    def generate(self):
        log(f"audio_filepath is set: {self.audio_filepath}, beginning initial whisper transcription")

        whisper_json_filepath, whisper_result_json = self.transcribe()

        genius_lyrics_filepath = ""
        midico_lrc_filepath = ""

        return whisper_json_filepath, genius_lyrics_filepath, midico_lrc_filepath

    def transcribe(self):
        whisper_cache_filename = self.get_whisper_cache_filename()

        if os.path.isfile(whisper_cache_filename):
            with open(whisper_cache_filename, "r") as cache_file:
                return whisper_cache_filename, json.load(cache_file)

        audio = whisper.load_audio(self.audio_filepath)
        model = whisper.load_model("medium.en", device="cpu")
        result = whisper.transcribe(model, audio, language="en")

        with open(whisper_cache_filename, "w") as cache_file:
            json.dump(result, cache_file, indent=2)

        return whisper_cache_filename, result

    def get_whisper_cache_filename(self):
        filename = os.path.split(self.audio_filepath)[1]
        hash_value = self.get_file_hash(self.audio_filepath)
        cache_filename = os.path.join(self.cache_dir, filename + "_" + hash_value + ".json")
        return cache_filename

    def create_folders(self):
        if self.cache_dir is not None:
            os.makedirs(self.cache_dir, exist_ok=True)

        if self.output_dir is not None:
            os.makedirs(self.output_dir, exist_ok=True)


def log(message):
    timestamp = datetime.datetime.now().isoformat()
    print(f"{timestamp} - {message}")
