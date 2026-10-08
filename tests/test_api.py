
import io
from unittest.mock import MagicMock

def test_upload_invalid_file_extension(client):
    file_data = b"dummy content"
    files = {"file": ("test.txt", io.BytesIO(file_data), "text/plain")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 400
    assert "Only .zip (Shapefile) or .kml files are supported" in response.text

def test_upload_valid_kml(client, mock_celery_task, monkeypatch):
    # We mock the database dependency to avoid hitting real PostGIS during unit tests
    from app.main import get_db
    mock_session = MagicMock()
    
    # Fake database save behavior
    def fake_add(obj):
        obj.id = "fake-uuid-123"
        return obj
    mock_session.add.side_effect = fake_add
    
    app_dependency_overrides = {get_db: lambda: mock_session}
    client.app.dependency_overrides.update(app_dependency_overrides)

    file_data = b"<kml>dummy</kml>"
    files = {"file": ("test.kml", io.BytesIO(file_data), "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)
    
    assert response.status_code == 202
    data = response.json()
    assert data["filename"] == "test.kml"
    assert data["status"] == "PENDING"
    
    # Assert celery task was called
    mock_celery_task.assert_called_once()
    
    # Clean up overrides
    client.app.dependency_overrides.clear()

def test_get_file_info_not_found(client):
    # Mocking DB to return None
    from app.main import get_db
    mock_session = MagicMock()
    mock_session.query().filter().first.return_value = None
    client.app.dependency_overrides[get_db] = lambda: mock_session
    
    response = client.get("/api/files/fake-id/")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    
    client.app.dependency_overrides.clear()
