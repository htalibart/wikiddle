from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_articles_search():
    res = client.get("/api/articles?query=Python")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert all("id" in a and "title" in a for a in data)

def test_common_neighbors():
    res = client.get("/api/common-neighbors?id=1234")
    assert res.status_code == 200
    data = res.json()
    assert "common" in data
    assert "is_target" in data
