import os
import hashlib
import datetime


class LyricsTranscriber:
    def __init__(
        self,
        audio_file=None,
        output_dir=None,
        cache_dir="/tmp/lyrics-transcriber-cache/",
    ):
        log("LyricsTranscriber initializing")

        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.audio_file = audio_file

        if self.audio_file is None:
            raise Exception("audio_file must be specified as the input source to transcribe")

        self.create_folders()

    def get_file_hash(self, filepath):
        return hashlib.md5(open(filepath, "rb").read()).hexdigest()

    def transcribe(self):
        log(f"audio_file is set: {self.audio_file}, beginning initial whisper transcription")

        whisper_json_filepath = ""
        genius_lyrics_filepath = ""
        midico_lrc_filepath = ""

        return whisper_json_filepath, genius_lyrics_filepath, midico_lrc_filepath

    def create_folders(self):
        if self.cache_dir is not None:
            os.makedirs(self.cache_dir, exist_ok=True)

        if self.output_dir is not None:
            os.makedirs(self.output_dir, exist_ok=True)


def log(message):
    timestamp = datetime.datetime.now().isoformat()
    print(f"{timestamp} - {message}")
