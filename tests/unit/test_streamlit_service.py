"""Tests for streamlit_service.py — config loading from secrets and local files."""

import json
import os
from unittest.mock import MagicMock, patch, mock_open

import pytest
import yaml

from streamlit_service import StreamlitCloudService


@pytest.fixture()
def service():
    return StreamlitCloudService()


# ---------------------------------------------------------------------------
# _convert_secrets_to_dict
# ---------------------------------------------------------------------------

class TestConvertSecretsToDict:
    def test_plain_dict(self, service):
        result = service._convert_secrets_to_dict({"key": "value"})
        assert result == {"key": "value"}

    def test_nested_dict(self, service):
        nested = {"a": {"b": {"c": 1}}}
        assert service._convert_secrets_to_dict(nested) == nested

    def test_list(self, service):
        assert service._convert_secrets_to_dict([1, 2, 3]) == [1, 2, 3]

    def test_primitives(self, service):
        assert service._convert_secrets_to_dict("hello") == "hello"
        assert service._convert_secrets_to_dict(42) == 42
        assert service._convert_secrets_to_dict(True) is True

    def test_none(self, service):
        assert service._convert_secrets_to_dict(None) is None

    def test_object_with_data_attr(self, service):
        obj = MagicMock()
        obj._data = {"key": "value"}
        result = service._convert_secrets_to_dict(obj)
        assert result == {"key": "value"}

    def test_object_with_to_dict(self, service):
        obj = MagicMock(spec=[])  # no _data
        obj.to_dict = MagicMock(return_value={"key": "value"})
        result = service._convert_secrets_to_dict(obj)
        assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# get_user_credentials
# ---------------------------------------------------------------------------

class TestGetUserCredentials:
    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_from_secrets(self, mock_st, mock_exists, service):
        secrets = MagicMock()
        secrets.__getitem__ = MagicMock(return_value={"credentials": {"usernames": {}}})
        secrets.user_credentials = {"credentials": {"usernames": {}}}
        mock_st.secrets = secrets
        result = service.get_user_credentials()
        assert result is not None

    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_from_local_file(self, mock_st, mock_exists, service):
        # No secrets attr
        del mock_st.secrets
        config = {"credentials": {"usernames": {"user1": {"password": "hash"}}}}
        with patch("builtins.open", mock_open(read_data=yaml.dump(config))):
            result = service.get_user_credentials()
        assert result == config

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_no_secrets_no_file(self, mock_st, mock_exists, service):
        del mock_st.secrets
        result = service.get_user_credentials()
        assert result is None

    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_corrupted_yaml(self, mock_st, mock_exists, service):
        del mock_st.secrets
        with patch("builtins.open", mock_open(read_data=": invalid: yaml: [")):
            result = service.get_user_credentials()
        assert result is None


# ---------------------------------------------------------------------------
# get_google_sheets_credentials
# ---------------------------------------------------------------------------

class TestGetGoogleSheetsCredentials:
    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_from_local_file(self, mock_st, mock_exists, service):
        del mock_st.secrets
        creds = {"type": "service_account", "project_id": "test"}
        with patch("builtins.open", mock_open(read_data=json.dumps(creds))):
            result = service.get_google_sheets_credentials()
        assert result == creds

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_no_file_no_secrets(self, mock_st, mock_exists, service):
        del mock_st.secrets
        result = service.get_google_sheets_credentials()
        assert result is None

    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_corrupted_json(self, mock_st, mock_exists, service):
        del mock_st.secrets
        with patch("builtins.open", mock_open(read_data="not json")):
            result = service.get_google_sheets_credentials()
        assert result is None


# ---------------------------------------------------------------------------
# get_sheet_url
# ---------------------------------------------------------------------------

class TestGetSheetUrl:
    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_from_local_config(self, mock_st, mock_exists, service):
        del mock_st.secrets
        config = {"sheet_url": "https://docs.google.com/spreadsheets/d/abc/edit"}
        with patch("builtins.open", mock_open(read_data=yaml.dump(config))):
            result = service.get_sheet_url()
        assert result == config["sheet_url"]

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_no_source(self, mock_st, mock_exists, service):
        del mock_st.secrets
        result = service.get_sheet_url()
        assert result is None

    @patch("streamlit_service.os.path.exists", return_value=True)
    @patch("streamlit_service.st")
    def test_config_without_sheet_url(self, mock_st, mock_exists, service):
        del mock_st.secrets
        config = {"other_key": "value"}
        with patch("builtins.open", mock_open(read_data=yaml.dump(config))):
            result = service.get_sheet_url()
        assert result is None


# ---------------------------------------------------------------------------
# validate_secrets
# ---------------------------------------------------------------------------

class TestValidateSecrets:
    @patch("streamlit_service.os.path.exists", return_value=True)
    def test_local_files_skip_validation(self, mock_exists, service):
        assert service.validate_secrets() is None

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_no_secrets_attr(self, mock_st, mock_exists, service):
        del mock_st.secrets
        result = service.validate_secrets()
        assert result is not None
        assert "secrets" in result.lower()

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_missing_required_secrets(self, mock_st, mock_exists, service):
        mock_st.secrets = MagicMock(spec=[])  # no attributes
        result = service.validate_secrets()
        assert result is not None
        assert "user_credentials" in result

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_all_secrets_present(self, mock_st, mock_exists, service):
        secrets = MagicMock()
        secrets.user_credentials = {}
        secrets.google_sheets_credentials = {}
        secrets.sheet_url = "url"
        mock_st.secrets = secrets
        result = service.validate_secrets()
        assert result is None

    @patch("streamlit_service.os.path.exists", return_value=False)
    @patch("streamlit_service.st")
    def test_partial_secrets_missing(self, mock_st, mock_exists, service):
        secrets = MagicMock(spec=[])
        secrets.user_credentials = {}
        # google_sheets_credentials and sheet_url missing
        mock_st.secrets = secrets
        result = service.validate_secrets()
        assert result is not None
