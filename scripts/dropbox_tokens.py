#! /usr/bin/env python3
"""
This script handles the OAuth 2.0 authorization flow for Dropbox integration.
It starts a local server to receive the OAuth callback, opens a browser for user authorization,
and exchanges the authorization code for access and refresh tokens.

These access and refresh tokens are needed to integrate with Dropbox's API for long-term access
to a user's account. In Lyrics-Transcriber, it's used to temporarily upload audio to be fetched
by transcription services.

Usage:
    python dropbox_tokens.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET
"""

import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
from dotenv import load_dotenv
import base64
from threading import Thread
import argparse

# Load environment variables from .env file
load_dotenv()

# Local server endpoint that will receive the OAuth callback
REDIRECT_URL = "http://localhost:53682/"

# Global variable to store the authorization code received from Dropbox
auth_code = None


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler that processes the OAuth callback from Dropbox.
    Captures the authorization code and displays a success message to the user.
    """

    def do_GET(self):
        global auth_code
        # Extract query parameters from the callback URL
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            # Store the authorization code and show success message
            auth_code = params["code"][0]
            # Send success response
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")

            # Shutdown the server
            Thread(target=self.server.shutdown).start()
        else:
            # Handle error or other cases
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization failed!")


def get_tokens(app_key, app_secret):
    """
    Manages the OAuth flow to obtain Dropbox access and refresh tokens.

    Args:
        app_key (str): Dropbox application key
        app_secret (str): Dropbox application secret
    """
    # Build the Dropbox authorization URL with required parameters
    auth_url = (
        "https://www.dropbox.com/oauth2/authorize"
        f"?client_id={app_key}"
        f"&redirect_uri={REDIRECT_URL}"
        "&response_type=code"
        "&token_access_type=offline"  # Request refresh token for long-term access
    )

    # Start local server to receive the OAuth callback
    port = int(REDIRECT_URL.split(":")[-1].strip("/"))
    httpd = socketserver.TCPServer(("", port), OAuthHandler)

    print(f"Opening browser for Dropbox authorization...")
    webbrowser.open(auth_url)

    print(f"Waiting for authorization...")
    httpd.serve_forever()

    if auth_code:
        print("Authorization code received, exchanging for tokens...")

        # Exchange authorization code for tokens
        auth = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
        response = requests.post(
            "https://api.dropbox.com/oauth2/token",
            data={"code": auth_code, "grant_type": "authorization_code", "redirect_uri": REDIRECT_URL},
            headers={"Authorization": f"Basic {auth}"},
        )

        if response.status_code == 200:
            tokens = response.json()
            print("\nTokens received successfully!")
            print("\nAdd these lines to your .env file:")
            print(f"WHISPER_DROPBOX_APP_KEY={app_key}")
            print(f"WHISPER_DROPBOX_APP_SECRET={app_secret}")
            print(f"WHISPER_DROPBOX_ACCESS_TOKEN={tokens['access_token']}")
            print(f"WHISPER_DROPBOX_REFRESH_TOKEN={tokens['refresh_token']}")

            # Prompt user to automatically update the .env file with new tokens
            update = input("\nWould you like to update your .env file automatically? (y/n): ")
            if update.lower() == "y":
                # Read existing .env content
                with open(".env", "r") as f:
                    lines = f.readlines()

                # Write updated tokens while preserving other environment variables
                with open(".env", "w") as f:
                    for line in lines:
                        if line.startswith("WHISPER_DROPBOX_APP_KEY="):
                            f.write(f"WHISPER_DROPBOX_APP_KEY={app_key}\n")
                        elif line.startswith("WHISPER_DROPBOX_APP_SECRET="):
                            f.write(f"WHISPER_DROPBOX_APP_SECRET={app_secret}\n")
                        elif line.startswith("WHISPER_DROPBOX_ACCESS_TOKEN="):
                            f.write(f"WHISPER_DROPBOX_ACCESS_TOKEN={tokens['access_token']}\n")
                        elif line.startswith("WHISPER_DROPBOX_REFRESH_TOKEN="):
                            f.write(f"WHISPER_DROPBOX_REFRESH_TOKEN={tokens['refresh_token']}\n")
                        else:
                            f.write(line)
                print("Updated .env file successfully!")
        else:
            print("Error exchanging authorization code for tokens:")
            print(response.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get Dropbox OAuth tokens.")
    parser.add_argument("--app-key", required=True, help="Dropbox App Key")
    parser.add_argument("--app-secret", required=True, help="Dropbox App Secret")

    args = parser.parse_args()
    get_tokens(args.app_key, args.app_secret)
