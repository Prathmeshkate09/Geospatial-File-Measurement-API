import pytest
from fastapi.testclient import TestClient

from unittest.mock import patch

from app.main import app


# We'll use the existing DATABASE_URL but in a transaction that rolls back, 
# or just a separate schema if we wanted. For simplicity in this demo,
# we will mock the database where necessary or rely on an empty test database.
# In a real environment, you'd configure a test-specific PostGIS database here.

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_db_session():
    with patch("app.main.get_db") as mock_get_db:
        yield mock_get_db

@pytest.fixture
def mock_celery_task():
    with patch("app.main.process_geospatial_file.delay") as mock_task:
        yield mock_task
