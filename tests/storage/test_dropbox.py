import pytest
from unittest.mock import Mock, patch, call
import os
from io import BytesIO
from dropbox.files import WriteMode, FileMetadata
from dropbox.sharing import SharedLinkSettings, RequestedVisibility
from dropbox.exceptions import AuthError, ApiError
from lyrics_transcriber.storage.dropbox import (
    DropboxConfig,
    DropboxHandler,
    DefaultTokenRefresher,
    TokenRefresher,
)
from tempfile import TemporaryDirectory


class TestDropboxConfig:
    def test_from_env(self):
        """Test creating config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "WHISPER_DROPBOX_APP_KEY": "test_key",
                "WHISPER_DROPBOX_APP_SECRET": "test_secret",
                "WHISPER_DROPBOX_REFRESH_TOKEN": "test_refresh",
                "WHISPER_DROPBOX_ACCESS_TOKEN": "test_access",
            },
        ):
            config = DropboxConfig.from_env()
            assert config.app_key == "test_key"
            assert config.app_secret == "test_secret"
            assert config.refresh_token == "test_refresh"
            assert config.access_token == "test_access"


class TestDefaultTokenRefresher:
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        refresher = DefaultTokenRefresher()
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"access_token": "new_token"}
            new_token = refresher.refresh_token("refresh", "key", "secret")
            assert new_token == "new_token"
            mock_post.assert_called_once_with(
                "https://api.dropbox.com/oauth2/token",
                data={"grant_type": "refresh_token", "refresh_token": "refresh"},
                auth=("key", "secret"),
            )

    def test_refresh_token_failure(self):
        """Test token refresh failure."""
        refresher = DefaultTokenRefresher()
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("API Error")
            with pytest.raises(Exception, match="API Error"):
                refresher.refresh_token("refresh", "key", "secret")


class TestDropboxHandler:
    @pytest.fixture
    def mock_client(self):
        return Mock()

    @pytest.fixture
    def mock_refresher(self):
        return Mock()

    @pytest.fixture
    def config(self):
        return DropboxConfig(
            app_key="test_key",
            app_secret="test_secret",
            refresh_token="test_refresh",
            access_token="test_access",
        )

    @pytest.fixture
    def handler(self, config, mock_client, mock_refresher):
        return DropboxHandler(
            config=config,
            token_refresher=mock_refresher,
            client=mock_client,
        )

    def test_init_with_env_vars(self):
        """Test initialization with environment variables."""
        with patch.dict(
            os.environ,
            {
                "WHISPER_DROPBOX_APP_KEY": "test_key",
                "WHISPER_DROPBOX_APP_SECRET": "test_secret",
                "WHISPER_DROPBOX_REFRESH_TOKEN": "test_refresh",
                "WHISPER_DROPBOX_ACCESS_TOKEN": "test_access",
            },
        ):
            handler = DropboxHandler()
            assert handler.config.app_key == "test_key"

    def test_init_missing_config(self):
        """Test initialization with missing configuration."""
        with pytest.raises(ValueError, match="Missing required Dropbox configuration"):
            DropboxHandler(config=DropboxConfig())

    def test_upload_with_retry_success(self, handler):
        """Test successful file upload."""
        file_content = b"test content"
        file = BytesIO(file_content)
        handler.upload_with_retry(file, "/test/path")

        handler.client.files_upload.assert_called_once_with(file_content, "/test/path", mode=WriteMode.overwrite)

    def test_upload_with_retry_failure_then_success(self, handler):
        """Test file upload with initial failure then success."""
        file_content = b"test content"
        file = BytesIO(file_content)

        mock_error = ApiError(
            error={"error": "test_error"}, user_message_text="Test error", user_message_locale="en", request_id="test_request_id"
        )

        # Set up the sequence of responses
        handler.client.files_upload.side_effect = [
            mock_error,  # First attempt fails
            None,  # Second attempt succeeds
        ]

        handler.upload_with_retry(file, "/test/path")
        assert handler.client.files_upload.call_count == 2

        # Verify the upload was called with correct arguments
        handler.client.files_upload.assert_has_calls(
            [
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
            ]
        )

    def test_upload_with_retry_all_attempts_fail(self, handler):
        """Test file upload with all attempts failing."""
        file = BytesIO(b"test content")
        mock_error = ApiError(
            error={"error": "test_error"}, user_message_text="Test error", user_message_locale="en", request_id="test_request_id"
        )

        # Make all attempts fail
        handler.client.files_upload.side_effect = mock_error

        with pytest.raises(ApiError):
            handler.upload_with_retry(file, "/test/path", max_retries=3)

        assert handler.client.files_upload.call_count == 3

        # Verify all calls were made with correct arguments
        handler.client.files_upload.assert_has_calls(
            [
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
            ]
        )

    def test_list_folder_recursive(self, handler):
        """Test recursive folder listing."""
        mock_entry = Mock(spec=FileMetadata)
        handler.client.files_list_folder.return_value = Mock(entries=[mock_entry], has_more=False)

        result = handler.list_folder_recursive("/test/path")

        assert result == [mock_entry]
        handler.client.files_list_folder.assert_called_once_with("/test/path", recursive=True)

    def test_create_shared_link(self, handler):
        """Test creating a shared link."""
        mock_link = Mock(url="https://www.dropbox.com/test")
        handler.client.sharing_create_shared_link_with_settings.return_value = mock_link

        result = handler.create_shared_link("/test/path")

        assert result == "https://dl.dropboxusercontent.com/test"
        handler.client.sharing_create_shared_link_with_settings.assert_called_once_with(
            "/test/path",
            settings=SharedLinkSettings(requested_visibility=RequestedVisibility.public),
        )

    def test_get_existing_shared_link(self, handler):
        """Test getting an existing shared link."""
        mock_link = Mock(url="https://www.dropbox.com/test")
        handler.client.sharing_list_shared_links.return_value = Mock(links=[mock_link])

        result = handler.get_existing_shared_link("/test/path")

        assert result == "https://dl.dropboxusercontent.com/test"
        handler.client.sharing_list_shared_links.assert_called_once_with(path="/test/path")

    def test_file_exists(self, handler):
        """Test checking if a file exists."""
        handler.client.files_get_metadata.return_value = Mock()
        assert handler.file_exists("/test/path") is True

        handler.client.files_get_metadata.side_effect = Exception()
        assert handler.file_exists("/test/path") is False

    def test_refresh_access_token(self, handler):
        """Test access token refresh."""
        # Setup
        handler.token_refresher.refresh_token.return_value = "new_token"

        # Execute
        handler._refresh_access_token()

        # Verify
        handler.token_refresher.refresh_token.assert_called_once_with(
            handler.config.refresh_token, handler.config.app_key, handler.config.app_secret
        )
        assert handler.config.access_token == "new_token"

    def test_refresh_access_token_failure(self, handler):
        """Test access token refresh failure."""
        # Setup
        handler.token_refresher.refresh_token.side_effect = Exception("Refresh failed")

        # Execute and verify
        with pytest.raises(Exception, match="Refresh failed"):
            handler._refresh_access_token()

    def test_upload_string_with_retry_success(self, handler):
        """Test successful string upload."""
        # Execute
        handler.upload_string_with_retry("test content", "/test/path")

        # Verify
        handler.client.files_upload.assert_called_once_with(b"test content", "/test/path", mode=WriteMode.overwrite)

    def test_upload_string_with_retry_failure_then_success(self, handler):
        """Test string upload with retry."""
        # Setup
        mock_error = ApiError(
            error={"error": "test_error"}, user_message_text="Test error", user_message_locale="en", request_id="test_request_id"
        )
        handler.client.files_upload.side_effect = [
            mock_error,  # First attempt fails
            None,  # Second attempt succeeds
        ]

        # Execute
        handler.upload_string_with_retry("test content", "/test/path", max_retries=2)

        # Verify
        assert handler.client.files_upload.call_count == 2

        # Verify the upload was called with correct arguments
        handler.client.files_upload.assert_has_calls(
            [
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
            ]
        )

    def test_upload_string_with_retry_all_failures(self, handler):
        """Test string upload with all retries failing."""
        # Setup
        mock_error = ApiError(
            error={"error": "test_error"}, user_message_text="Test error", user_message_locale="en", request_id="test_request_id"
        )

        # Make all attempts fail
        handler.client.files_upload.side_effect = mock_error

        # Execute and verify
        with pytest.raises(ApiError):
            handler.upload_string_with_retry("test content", "/test/path", max_retries=3)

        assert handler.client.files_upload.call_count == 3

        # Verify all calls were made with correct arguments
        handler.client.files_upload.assert_has_calls(
            [
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
                call(b"test content", "/test/path", mode=WriteMode.overwrite),
            ]
        )

    def test_download_file_content_success(self, handler):
        """Test successful file download."""
        # Setup
        mock_response = Mock()
        mock_response.content = b"test content"
        handler.client.files_download.return_value = (None, mock_response)

        # Execute
        result = handler.download_file_content("/test/path")

        # Verify
        assert result == b"test content"
        handler.client.files_download.assert_called_once_with("/test/path")

    def test_download_file_content_failure(self, handler):
        """Test file download failure."""
        # Setup
        handler.client.files_download.side_effect = Exception("Download failed")

        # Execute and verify
        with pytest.raises(Exception, match="Download failed"):
            handler.download_file_content("/test/path")

    def test_list_folder_recursive_with_continuation(self, handler):
        """Test recursive folder listing with continuation token."""
        # Setup
        mock_entry1 = Mock(spec=FileMetadata)
        mock_entry2 = Mock(spec=FileMetadata)

        # First response has more results
        first_response = Mock(entries=[mock_entry1], has_more=True, cursor="test_cursor")

        # Second response completes the listing
        second_response = Mock(entries=[mock_entry2], has_more=False)

        handler.client.files_list_folder.return_value = first_response
        handler.client.files_list_folder_continue.return_value = second_response

        # Execute
        result = handler.list_folder_recursive("/test/path")

        # Verify
        assert result == [mock_entry1, mock_entry2]
        handler.client.files_list_folder.assert_called_once_with("/test/path", recursive=True)
        handler.client.files_list_folder_continue.assert_called_once_with("test_cursor")

    def test_download_folder_success(self, handler):
        """Test successful folder download."""
        # Setup mock entries
        mock_file1 = Mock(spec=FileMetadata)
        mock_file1.path_display = "/test/path/file1.txt"
        mock_file2 = Mock(spec=FileMetadata)
        mock_file2.path_display = "/test/path/subdir/file2.txt"

        # Mock list_folder_recursive to return our test files
        handler.list_folder_recursive = Mock(return_value=[mock_file1, mock_file2])

        # Use a temporary directory for the test
        with TemporaryDirectory() as temp_dir:
            # Execute
            handler.download_folder("/test/path", temp_dir)

            # Verify
            handler.client.files_download_to_file.assert_has_calls(
                [
                    call(os.path.join(temp_dir, "file1.txt"), "/test/path/file1.txt"),
                    call(os.path.join(temp_dir, "subdir/file2.txt"), "/test/path/subdir/file2.txt"),
                ]
            )

    def test_create_shared_link_success(self, handler):
        """Test successful shared link creation."""
        # Setup
        mock_link = Mock()
        mock_link.url = "https://www.dropbox.com/test/path"
        handler.client.sharing_create_shared_link_with_settings.return_value = mock_link

        # Execute
        result = handler.create_shared_link("/test/path")

        # Verify
        assert result == "https://dl.dropboxusercontent.com/test/path"
        handler.client.sharing_create_shared_link_with_settings.assert_called_once()

    def test_get_existing_shared_link_success(self, handler):
        """Test getting existing shared link."""
        # Setup
        mock_link = Mock()
        mock_link.url = "https://www.dropbox.com/test/path"
        mock_response = Mock()
        mock_response.links = [mock_link]
        handler.client.sharing_list_shared_links.return_value = mock_response

        # Execute
        result = handler.get_existing_shared_link("/test/path")

        # Verify
        assert result == "https://dl.dropboxusercontent.com/test/path"
        handler.client.sharing_list_shared_links.assert_called_once_with(path="/test/path")

    def test_get_existing_shared_link_no_links(self, handler):
        """Test getting existing shared link when none exist."""
        # Setup
        mock_response = Mock()
        mock_response.links = []
        handler.client.sharing_list_shared_links.return_value = mock_response

        # Execute
        result = handler.get_existing_shared_link("/test/path")

        # Verify
        assert result is None
        handler.client.sharing_list_shared_links.assert_called_once_with(path="/test/path")

    def test_create_or_get_shared_link_existing(self, handler):
        """Test create_or_get_shared_link when link exists."""
        # Setup
        existing_url = "https://dl.dropboxusercontent.com/test/path"
        handler.get_existing_shared_link = Mock(return_value=existing_url)
        handler.create_shared_link = Mock()  # Properly mock the method

        # Execute
        result = handler.create_or_get_shared_link("/test/path")

        # Verify
        assert result == existing_url
        handler.get_existing_shared_link.assert_called_once_with("/test/path")
        handler.create_shared_link.assert_not_called()

    def test_create_or_get_shared_link_new(self, handler):
        """Test create_or_get_shared_link when creating new link."""
        # Setup
        handler.get_existing_shared_link = Mock(return_value=None)
        new_url = "https://dl.dropboxusercontent.com/test/path"
        handler.create_shared_link = Mock(return_value=new_url)

        # Execute
        result = handler.create_or_get_shared_link("/test/path")

        # Verify
        assert result == new_url
        handler.get_existing_shared_link.assert_called_once_with("/test/path")
        handler.create_shared_link.assert_called_once_with("/test/path")

    def test_file_exists_true(self, handler):
        """Test file_exists when file exists."""
        # Setup
        handler.client.files_get_metadata.return_value = Mock()

        # Execute
        result = handler.file_exists("/test/path")

        # Verify
        assert result is True
        handler.client.files_get_metadata.assert_called_once_with("/test/path")

    def test_file_exists_false(self, handler):
        """Test file_exists when file doesn't exist."""
        # Setup
        handler.client.files_get_metadata.side_effect = Exception("Not found")

        # Execute
        result = handler.file_exists("/test/path")

        # Verify
        assert result is False
        handler.client.files_get_metadata.assert_called_once_with("/test/path")

    def test_list_folder_recursive_error(self, handler):
        """Test error handling in list_folder_recursive."""
        # Setup
        handler.client.files_list_folder.side_effect = Exception("Listing failed")

        # Execute and verify
        with pytest.raises(Exception, match="Listing failed"):
            handler.list_folder_recursive("/test/path")

    def test_download_folder_error(self, handler):
        """Test error handling in download_folder."""
        # Setup mock entries
        mock_file = Mock(spec=FileMetadata)
        mock_file.path_display = "/test/path/file1.txt"
        handler.list_folder_recursive = Mock(return_value=[mock_file])
        handler.client.files_download_to_file.side_effect = Exception("Download failed")

        # Execute and verify
        with TemporaryDirectory() as temp_dir:
            with pytest.raises(Exception, match="Download failed"):
                handler.download_folder("/test/path", temp_dir)

    def test_upload_folder_error(self, handler):
        """Test error handling in upload_folder."""
        # Setup
        with TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file_path = os.path.join(temp_dir, "test.txt")
            with open(test_file_path, "w") as f:
                f.write("test content")

            # Mock upload to fail
            handler.client.files_upload.side_effect = Exception("Upload failed")

            # Execute and verify
            with pytest.raises(Exception, match="Upload failed"):
                handler.upload_folder(temp_dir, "/test/dropbox/path")

    def test_create_shared_link_error(self, handler):
        """Test error handling in create_shared_link."""
        # Setup
        handler.client.sharing_create_shared_link_with_settings.side_effect = Exception("Link creation failed")

        # Execute and verify
        with pytest.raises(Exception, match="Link creation failed"):
            handler.create_shared_link("/test/path")

    def test_get_existing_shared_link_error(self, handler):
        """Test error handling in get_existing_shared_link."""
        # Setup
        handler.client.sharing_list_shared_links.side_effect = Exception("Link listing failed")

        # Execute
        result = handler.get_existing_shared_link("/test/path")

        # Verify
        assert result is None

    def test_create_or_get_shared_link_error(self, handler):
        """Test error handling in create_or_get_shared_link."""
        # Setup
        handler.get_existing_shared_link = Mock(side_effect=Exception("Link operation failed"))

        # Execute and verify
        with pytest.raises(Exception, match="Link operation failed"):
            handler.create_or_get_shared_link("/test/path")

    def test_upload_folder_success(self, handler):
        """Test successful folder upload."""
        # Setup
        with TemporaryDirectory() as temp_dir:
            # Create a test file structure
            test_file1 = os.path.join(temp_dir, "test1.txt")
            test_subdir = os.path.join(temp_dir, "subdir")
            os.makedirs(test_subdir)
            test_file2 = os.path.join(test_subdir, "test2.txt")

            # Create test files
            with open(test_file1, "w") as f:
                f.write("test content 1")
            with open(test_file2, "w") as f:
                f.write("test content 2")

            # Execute
            handler.upload_folder(temp_dir, "/test/dropbox/path")

            # Verify
            handler.client.files_upload.assert_has_calls(
                [
                    call(b"test content 1", "/test/dropbox/path/test1.txt", mode=WriteMode.overwrite),
                    call(b"test content 2", "/test/dropbox/path/subdir/test2.txt", mode=WriteMode.overwrite),
                ],
                any_order=True,
            )

    def test_handle_auth_error_decorator(self, handler):
        """Test the auth error handling decorator."""
        # Setup
        mock_error = AuthError(request_id="test_request_id", error={".tag": "expired_access_token"})

        # Create a mock method that will fail once then succeed
        mock_method = Mock(side_effect=[mock_error, "success"])
        mock_method.__name__ = "test_method"  # Add name for logging

        # Add the decorator to the mock method
        decorated_method = handler._handle_auth_error(mock_method)

        # Execute
        result = decorated_method(handler)

        # Verify
        assert result == "success"
        assert mock_method.call_count == 2
        handler.token_refresher.refresh_token.assert_called_once_with(
            handler.config.refresh_token, handler.config.app_key, handler.config.app_secret
        )

    def test_handle_auth_error_decorator_other_auth_error(self, handler):
        """Test the decorator with a non-expired token AuthError."""
        # Setup
        mock_error = AuthError(request_id="test_request_id", error={"error": {".tag": "invalid_token"}})  # Different error type

        mock_method = Mock(side_effect=mock_error)
        mock_method.__name__ = "test_method"

        decorated_method = handler._handle_auth_error(mock_method)

        # Execute and verify
        with pytest.raises(AuthError) as exc_info:
            decorated_method(handler)

        assert exc_info.value == mock_error
        handler.token_refresher.refresh_token.assert_not_called()

    def test_handle_auth_error_decorator_api_error(self, handler):
        """Test the decorator with an ApiError."""
        # Setup
        mock_error = ApiError(
            request_id="test_request_id", error="test_error", user_message_text="Test user message", user_message_locale="en"
        )

        mock_method = Mock(side_effect=mock_error)
        mock_method.__name__ = "test_method"

        decorated_method = handler._handle_auth_error(mock_method)

        # Execute and verify
        with pytest.raises(ApiError) as exc_info:
            decorated_method(handler)

        assert exc_info.value == mock_error
        handler.token_refresher.refresh_token.assert_not_called()
