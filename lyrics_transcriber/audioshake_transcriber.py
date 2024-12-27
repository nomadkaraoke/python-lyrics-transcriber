import requests
import time
import os
import json


class AudioShakeTranscriber:
    def __init__(self, api_token, logger, output_prefix):
        self.api_token = api_token
        self.base_url = "https://groovy.audioshake.ai"
        self.logger = logger
        self.output_prefix = output_prefix

    def start_transcription(self, audio_filepath):
        """Starts the transcription job and returns the job ID without waiting for completion"""
        self.logger.info(f"Starting transcription for {audio_filepath} using AudioShake API")

        # Step 1: Upload the audio file
        asset_id = self._upload_file(audio_filepath)
        self.logger.info(f"File uploaded successfully. Asset ID: {asset_id}")

        # Step 2: Create a job for transcription and alignment
        job_id = self._create_job(asset_id)
        self.logger.info(f"Job created successfully. Job ID: {job_id}")

        return job_id

    def get_transcription_result(self, job_id):
        """Gets the results for a previously started job"""
        self.logger.info(f"Getting results for job ID: {job_id}")

        # Step 3: Wait for the job to complete and get the results
        result = self._get_job_result(job_id)
        self.logger.info(f"Job completed. Processing results...")

        # Step 4: Process the result and return in the required format
        return self._process_result(result)

    def transcribe(self, audio_filepath):
        """Original method now just combines the two steps"""
        job_id = self.start_transcription(audio_filepath)
        return self.get_transcription_result(job_id)

    def _upload_file(self, filepath):
        self.logger.info(f"Uploading {filepath} to AudioShake")
        url = f"{self.base_url}/upload"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        with open(filepath, "rb") as file:
            files = {"file": (os.path.basename(filepath), file)}
            response = requests.post(url, headers=headers, files=files)

        self.logger.info(f"Upload response status code: {response.status_code}")
        self.logger.info(f"Upload response content: {response.text}")

        response.raise_for_status()
        return response.json()["id"]

    def _create_job(self, asset_id):
        self.logger.info(f"Creating job for asset {asset_id}")
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
        self.logger.info(f"Getting job result for job {job_id}")
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
        self.logger.debug(f"Processing result for job {job_data['id']}")
        self.logger.debug(f"Job data: {json.dumps(job_data, indent=2)}")

        output_assets = job_data.get("outputAssets", [])
        self.logger.debug(f"Output assets: {output_assets}")

        output_asset = next((asset for asset in output_assets if asset["name"] == "alignment.json"), None)

        if not output_asset:
            self.logger.error("'alignment.json' found in job results")
            self.logger.error(f"Available output assets: {[asset['name'] for asset in output_assets]}")
            raise Exception("Required output not found in job results")

        transcription_url = output_asset["link"]
        self.logger.debug(f"Output URL: {transcription_url}")

        response = requests.get(transcription_url)
        response.raise_for_status()
        transcription_data = response.json()
        self.logger.debug(f"Output data: {json.dumps(transcription_data, indent=2)}")

        transcription_data = {"segments": transcription_data.get("lines", []), "text": transcription_data.get("text", "")}

        # Ensure each segment has the required fields
        for segment in transcription_data["segments"]:
            if "words" not in segment:
                segment["words"] = []
            if "text" not in segment:
                segment["text"] = " ".join(word["text"] for word in segment["words"])

        transcription_data["output_filename"] = self.get_output_filename(" (AudioShake)")

        return transcription_data

    def get_output_filename(self, suffix):
        """Generate consistent filename with (Purpose) suffix pattern"""
        return f"{self.output_prefix}{suffix}"
