import requests
import time
import os
import json


class AudioShakeTranscriber:
    def __init__(self, api_token, logger):
        self.api_token = api_token
        self.base_url = "https://groovy.audioshake.ai"
        self.logger = logger

    def transcribe(self, audio_filepath):
        self.logger.info(f"Transcribing {audio_filepath} using AudioShake API")

        # Step 1: Upload the audio file
        asset_id = self._upload_file(audio_filepath)
        self.logger.debug(f"File uploaded successfully. Asset ID: {asset_id}")

        # Step 2: Create a job for transcription and alignment
        job_id = self._create_job(asset_id)
        self.logger.debug(f"Job created successfully. Job ID: {job_id}")

        # Step 3: Wait for the job to complete and get the results
        result = self._get_job_result(job_id)
        self.logger.debug(f"Job completed. Processing results...")

        # Step 4: Process the result and return in the required format
        return self._process_result(result)

    def _upload_file(self, filepath):
        self.logger.debug(f"Uploading {filepath} to AudioShake")
        url = f"{self.base_url}/upload"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        with open(filepath, "rb") as file:
            files = {"file": (os.path.basename(filepath), file)}
            response = requests.post(url, headers=headers, files=files)

        self.logger.debug(f"Upload response status code: {response.status_code}")
        self.logger.debug(f"Upload response content: {response.text}")

        response.raise_for_status()
        return response.json()["id"]

    def _create_job(self, asset_id):
        self.logger.debug(f"Creating job for asset {asset_id}")
        url = f"{self.base_url}/job/"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        data = {
            "metadata": {"format": "json", "name": "alignment", "language": "en"},
            "callbackUrl": "https://example.com/webhook/alignment",
            "assetId": asset_id,
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["job"]["id"]

    def _get_job_result(self, job_id):
        self.logger.debug(f"Getting job result for job {job_id}")
        url = f"{self.base_url}/job/{job_id}"
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        while True:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            job_data = response.json()["job"]
            if job_data["status"] == "completed":
                return job_data
            elif job_data["status"] == "failed":
                raise Exception("Job failed")
            time.sleep(5)  # Wait 5 seconds before checking again

    def _process_result(self, job_data):
        self.logger.debug(f"Processing result for job {job_data}")
        output_asset = next((asset for asset in job_data["outputAssets"] if asset["name"] == "transcription.json"), None)

        if not output_asset:
            raise Exception("Transcription output not found in job results")

        transcription_url = output_asset["link"]
        response = requests.get(transcription_url)
        response.raise_for_status()
        transcription_data = response.json()

        transcription_data = {"segments": transcription_data.get("lines", []), "text": transcription_data.get("text", "")}

        # Ensure each segment has the required fields
        for segment in transcription_data["segments"]:
            if "words" not in segment:
                segment["words"] = []
            if "text" not in segment:
                segment["text"] = " ".join(word["text"] for word in segment["words"])

        return transcription_data
