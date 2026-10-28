from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_categories():
    response = client.get("/api/suggestions/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4


def test_create_and_get_project():
    payload = {
        "title": "Top 2 Mind Benders",
        "movies": [
            {"title": "Inception", "year": "2010", "vote_average": 8.8},
            {"title": "Interstellar", "year": "2014", "vote_average": 8.7},
        ],
        "notes": "Testing",
    }
    create_res = client.post("/api/projects", json=payload)
    assert create_res.status_code == 200
    project = create_res.json()
    assert project["title"] == "Top 2 Mind Benders"
    p_id = project["id"]

    get_res = client.get(f"/api/projects/{p_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == p_id
    assert len(get_res.json()["movies_json"]) == 2

    # Clean up
    del_res = client.delete(f"/api/projects/{p_id}")
    assert del_res.status_code == 200


def test_create_single_movie_project():
    payload = {
        "movies": [
            {"title": "Shutter Island", "year": "2010", "vote_average": 8.2},
        ],
    }
    create_res = client.post("/api/projects", json=payload)
    assert create_res.status_code == 200
    project = create_res.json()
    assert "Shutter Island" in project["title"]
    assert project["movie_count"] == 1
    assert project["job_code"].startswith("SPOT-")
    p_id = project["id"]

    del_res = client.delete(f"/api/projects/{p_id}")
    assert del_res.status_code == 200
