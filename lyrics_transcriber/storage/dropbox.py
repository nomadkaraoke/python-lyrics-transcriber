import dropbox
from dropbox import Dropbox
from dropbox.files import WriteMode
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)


class DropboxHandler:
    def __init__(self, app_key=None, app_secret=None, refresh_token=None, access_token=None):
        self.app_key = app_key or os.environ.get("WHISPER_DROPBOX_APP_KEY")
        self.app_secret = app_secret or os.environ.get("WHISPER_DROPBOX_APP_SECRET")
        self.refresh_token = refresh_token or os.environ.get("WHISPER_DROPBOX_REFRESH_TOKEN")
        self.access_token = access_token or os.environ.get("WHISPER_DROPBOX_ACCESS_TOKEN")
        self.dbx = Dropbox(self.access_token)

    def _refresh_access_token(self):
        """Refresh the access token using the refresh token."""
        try:
            logger.debug("Attempting to refresh access token")
            # Prepare the token refresh request
            data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
            auth = (self.app_key, self.app_secret)

            logger.debug(f"Making refresh token request to Dropbox API")
            response = requests.post("https://api.dropbox.com/oauth2/token", data=data, auth=auth)

            logger.debug(f"Received response from Dropbox API. Status code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                self.access_token = result["access_token"]
                self.dbx = Dropbox(self.access_token)
                logger.info("Successfully refreshed access token")
            else:
                logger.error(f"Failed to refresh token. Status code: {response.status_code}, Response: {response.text}")

        except Exception as e:
            logger.error(f"Error refreshing access token: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _handle_auth_error(func):
        """Decorator to handle authentication errors and retry with refreshed token."""

        def wrapper(self, *args, **kwargs):
            try:
                logger.debug(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")
                return func(self, *args, **kwargs)
            except (dropbox.exceptions.AuthError, dropbox.exceptions.ApiError) as e:
                logger.debug(f"Caught error in {func.__name__}: {str(e)}")
                if "expired_access_token" in str(e):
                    logger.info(f"Access token expired in {func.__name__}, attempting refresh")
                    self._refresh_access_token()
                    logger.debug(f"Retrying {func.__name__} after token refresh")
                    return func(self, *args, **kwargs)
                logger.error(f"Unhandled Dropbox error in {func.__name__}: {str(e)}")
                raise

        return wrapper

    @_handle_auth_error
    def upload_with_retry(self, file, path, max_retries=3):
        """Upload a file to Dropbox with retries."""
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting file upload to {path} (attempt {attempt + 1}/{max_retries})")
                file.seek(0)
                self.dbx.files_upload(file.read(), path, mode=WriteMode.overwrite)
                logger.debug(f"Successfully uploaded file to {path}")
                return
            except dropbox.exceptions.ApiError as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All upload attempts failed for {path}: {str(e)}")
                    raise
                sleep_time = 1 * (attempt + 1)
                logger.debug(f"Waiting {sleep_time} seconds before retry")
                time.sleep(sleep_time)

    @_handle_auth_error
    def upload_string_with_retry(self, content, path, max_retries=3):
        """Upload a string content to Dropbox with retries."""
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting string upload to {path} (attempt {attempt + 1}/{max_retries})")
                self.dbx.files_upload(content.encode(), path, mode=WriteMode.overwrite)
                logger.debug(f"Successfully uploaded string content to {path}")
                return
            except dropbox.exceptions.ApiError as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All upload attempts failed for {path}: {str(e)}")
                    raise
                sleep_time = 1 * (attempt + 1)
                logger.debug(f"Waiting {sleep_time} seconds before retry")
                time.sleep(sleep_time)

    @_handle_auth_error
    def list_folder_recursive(self, path=""):
        """List all files in a folder recursively."""
        try:
            logger.debug(f"Listing files recursively from {path}")
            entries = []
            result = self.dbx.files_list_folder(path, recursive=True)

            while True:
                entries.extend(result.entries)
                if not result.has_more:
                    break
                logger.debug("Fetching more results from Dropbox")
                result = self.dbx.files_list_folder_continue(result.cursor)

            return entries

        except (dropbox.exceptions.AuthError, dropbox.exceptions.ApiError):
            # Let the decorator handle these
            raise
        except Exception as e:
            logger.error(f"Error listing files from Dropbox: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def download_file_content(self, path):
        """Download and return the content of a file."""
        try:
            logger.debug(f"Downloading file content from {path}")
            return self.dbx.files_download(path)[1].content
        except Exception as e:
            logger.error(f"Error downloading file from {path}: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def download_folder(self, dropbox_path, local_path):
        """Download all files from a Dropbox folder to a local path."""
        try:
            logger.debug(f"Downloading folder {dropbox_path} to {local_path}")

            # List all files in the folder
            result = self.dbx.files_list_folder(dropbox_path, recursive=True)
            entries = result.entries

            # Continue fetching if there are more files
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                entries.extend(result.entries)

            # Download each file
            for entry in entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    # Calculate relative path from the root folder
                    rel_path = entry.path_display[len(dropbox_path) :].lstrip("/")
                    local_file_path = os.path.join(local_path, rel_path)

                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                    # Download the file
                    logger.debug(f"Downloading {entry.path_display} to {local_file_path}")
                    self.dbx.files_download_to_file(local_file_path, entry.path_display)

            logger.debug(f"Successfully downloaded folder {dropbox_path} to {local_path}")

        except Exception as e:
            logger.error(f"Error downloading folder {dropbox_path}: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def upload_folder(self, local_path, dropbox_path):
        """Upload all files from a local folder to a Dropbox path."""
        try:
            logger.debug(f"Uploading folder {local_path} to {dropbox_path}")

            # Walk through all files in the local folder
            for root, dirs, files in os.walk(local_path):
                for filename in files:
                    local_file_path = os.path.join(root, filename)
                    # Calculate relative path from local_path
                    rel_path = os.path.relpath(local_file_path, local_path)
                    target_path = f"{dropbox_path}/{rel_path}"

                    logger.debug(f"Uploading {rel_path} to {target_path}")
                    with open(local_file_path, "rb") as f:
                        self.dbx.files_upload(f.read(), target_path, mode=WriteMode.overwrite)

            logger.debug(f"Successfully uploaded folder {local_path} to {dropbox_path}")

        except Exception as e:
            logger.error(f"Error uploading folder {local_path}: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def create_shared_link(self, path):
        """Create a shared link for a file that's accessible without login."""
        try:
            logger.debug(f"Creating shared link for {path}")
            shared_link = self.dbx.sharing_create_shared_link_with_settings(
                path, settings=dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
            )
            # Convert dropbox shared link to direct download link
            return shared_link.url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        except Exception as e:
            logger.error(f"Error creating shared link: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def get_existing_shared_link(self, path):
        """Get existing shared link for a file if it exists."""
        try:
            logger.debug(f"Getting existing shared link for {path}")
            shared_links = self.dbx.sharing_list_shared_links(path=path).links
            if shared_links:
                # Convert to direct download link
                return shared_links[0].url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
            return None
        except Exception as e:
            logger.error(f"Error getting existing shared link: {str(e)}", exc_info=True)
            return None

    @_handle_auth_error
    def create_or_get_shared_link(self, path):
        """Create a shared link or get existing one."""
        try:
            # First try to get existing link
            existing_link = self.get_existing_shared_link(path)
            if existing_link:
                logger.debug(f"Found existing shared link for {path}")
                return existing_link

            # If no existing link, create new one
            logger.debug(f"Creating new shared link for {path}")
            shared_link = self.dbx.sharing_create_shared_link_with_settings(
                path, settings=dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
            )
            return shared_link.url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        except Exception as e:
            logger.error(f"Error creating or getting shared link: {str(e)}", exc_info=True)
            raise

    @_handle_auth_error
    def file_exists(self, path):
        """Check if a file exists in Dropbox."""
        try:
            self.dbx.files_get_metadata(path)
            return True
        except:
            return False
