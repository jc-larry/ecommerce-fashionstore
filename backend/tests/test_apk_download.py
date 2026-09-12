from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_download_apk_endpoint():
    response = client.get("/download-apk")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.android.package-archive"
    assert 'attachment; filename="fashionstore.apk"' in response.headers.get("content-disposition", "")
    assert len(response.content) > 1000000  # APK is tens of MBs

def test_download_apk_api_v1():
    response = client.get("/api/v1/download-apk")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.android.package-archive"
