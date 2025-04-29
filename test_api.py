import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_get_lab_tests_invalid_file():
    files = {"file": ("test.txt", "test content", "text/plain")}
    response = client.post("/get-lab-tests", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be an image"

def test_get_lab_tests_valid_image():
    with open("test_image.jpg", "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = client.post("/get-lab-tests", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "is_success" in data
    assert "data" in data 