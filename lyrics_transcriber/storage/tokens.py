#! /usr/bin/env python3
import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
from dotenv import load_dotenv
import base64
from threading import Thread
import argparse

# Load environment variables
load_dotenv()

REDIRECT_URL = "http://localhost:53682/"

# Store the authorization code when received
auth_code = None


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        # Parse the query parameters
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
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
    # Construct the authorization URL
    auth_url = (
        "https://www.dropbox.com/oauth2/authorize"
        f"?client_id={app_key}"
        f"&redirect_uri={REDIRECT_URL}"
        "&response_type=code"
        "&token_access_type=offline"
    )

    # Start local server
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

            # Optionally update .env file directly
            update = input("\nWould you like to update your .env file automatically? (y/n): ")
            if update.lower() == "y":
                with open(".env", "r") as f:
                    lines = f.readlines()

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
