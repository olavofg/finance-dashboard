"""Integration fixtures using Streamlit's AppTest framework."""

import pytest
from streamlit.testing.v1 import AppTest


MOCK_APP_PATH = "tests/integration/mock_app.py"


@pytest.fixture()
def app_authenticated():
    """Run the mock dashboard app with authentication pre-set (bypasses login)."""
    at = AppTest.from_file(MOCK_APP_PATH, default_timeout=30)
    at.session_state["authentication_status"] = True
    at.session_state["name"] = "Test User"
    at.session_state["username"] = "testuser"
    at.run()
    return at


@pytest.fixture()
def app_unauthenticated():
    """Run the mock dashboard app without authentication (shows login page)."""
    at = AppTest.from_file(MOCK_APP_PATH, default_timeout=30)
    at.run()
    return at
