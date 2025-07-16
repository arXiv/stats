import pytest
from stats_api.factory import create_app

@pytest.fixture
def app():
    """Fixture to create a test Flask app."""
    app = create_app("testing")
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    """Fixture to create a test client for making requests."""
    return app.test_client()