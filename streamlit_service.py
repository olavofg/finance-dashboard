import copy
import json
import logging
import os

import streamlit as st
import yaml


logger = logging.getLogger(__name__)


class StreamlitCloudService:
    """Abstraction layer for loading config from Streamlit secrets (prod) or local files (dev)."""

    def _convert_secrets_to_dict(self, secrets_obj):
        """Recursively convert Streamlit's immutable secrets objects into plain dicts."""

        if secrets_obj is None:
            return None

        # Streamlit secrets expose data via the private `_data` attribute.
        if hasattr(secrets_obj, '_data'):
            try:
                data = dict(secrets_obj._data)
                return {k: self._convert_secrets_to_dict(v) for k, v in data.items()}
            except Exception:
                try:
                    return dict(secrets_obj)
                except Exception:
                    pass

        elif hasattr(secrets_obj, 'to_dict'):
            try:
                return self._convert_secrets_to_dict(secrets_obj.to_dict())
            except Exception:
                pass

        elif isinstance(secrets_obj, dict):
            return {k: self._convert_secrets_to_dict(v) for k, v in secrets_obj.items()}

        elif isinstance(secrets_obj, (list, tuple)):
            return [self._convert_secrets_to_dict(item) for item in secrets_obj]

        elif isinstance(secrets_obj, (str, int, float, bool)):
            return secrets_obj

        else:
            try:
                if hasattr(secrets_obj, '__dict__'):
                    return copy.deepcopy(secrets_obj.__dict__)
                return copy.deepcopy(secrets_obj)
            except Exception:
                return secrets_obj

    def get_user_credentials(self):
        """Load user credentials from Streamlit secrets or local config.yaml."""
        try:
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'user_credentials'):
                return self._convert_secrets_to_dict(st.secrets['user_credentials'])
        except Exception as e:
            logger.exception("Failed to load credentials from secrets: %s", e)

        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
        except Exception as e:
            logger.exception("Failed to load config.yaml: %s", e)

        return None

    def get_google_sheets_credentials(self):
        """Load Google Sheets service-account credentials from secrets or local file."""
        try:
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'google_sheets_credentials'):
                return self._convert_secrets_to_dict(st.secrets['google_sheets_credentials'])
        except Exception as e:
            logger.exception("Failed to load credentials from secrets: %s", e)

        try:
            if os.path.exists('credentials.json'):
                with open('credentials.json', 'r', encoding='utf-8') as file:
                    return json.load(file)
        except Exception as e:
            logger.exception("Failed to load credentials.json: %s", e)

        return None

    def get_sheet_url(self):
        """Get the Google Sheets URL from secrets or local config.yaml."""
        try:
            if hasattr(st, 'secrets') and hasattr(st.secrets, 'sheet_url'):
                return st.secrets['sheet_url']
        except Exception as e:
            logger.exception("Failed to load sheet_url from secrets: %s", e)

        try:
            if os.path.exists('config.yaml'):
                with open('config.yaml', 'r', encoding='utf-8') as file:
                    config = yaml.safe_load(file)
                    if config and 'sheet_url' in config:
                        return config['sheet_url']
        except Exception as e:
            logger.exception("Failed to load sheet_url from config.yaml: %s", e)

        return None

    def validate_secrets(self):
        """Validate that all required secrets are present (skipped when local config files exist).

        Returns None if valid, or an error message string describing what is missing.
        """
        # Local dev: config files present, no need to check secrets.
        if os.path.exists('config.yaml') or os.path.exists('credentials.json'):
            return None

        if not hasattr(st, 'secrets'):
            return "Ambiente Streamlit Cloud detectado, mas secrets não estão disponíveis."

        required_secrets = [
            'user_credentials',
            'google_sheets_credentials',
            'sheet_url'
        ]

        missing_secrets = []

        for secret in required_secrets:
            try:
                if not hasattr(st.secrets, secret):
                    missing_secrets.append(secret)
            except Exception:
                missing_secrets.append(secret)

        if missing_secrets:
            return f"Secrets obrigatórios não configurados: {', '.join(missing_secrets)}"

        return None
