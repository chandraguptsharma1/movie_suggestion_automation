from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_scene_routes_flow():
    # 1. Create a test project
    payload = {
        "title": "Action Thrillers Scene Test",
        "movies": [
            {"title": "Mad Max: Fury Road", "year": "2015"},
            {"title": "John Wick", "year": "2014"},
        ],
    }
    create_res = client.post("/api/projects", json=payload)
    assert create_res.status_code == 200
    p_id = create_res.json()["id"]

    try:
        # 2. Get scenes initially (empty)
        get_res = client.get(f"/api/projects/{p_id}/scenes")
        assert get_res.status_code == 200
        assert get_res.json() == {"scenes": []}

        # 3. Update scenes directly
        mock_scenes = [
            {
                "slot": 1,
                "movie_title": "Mad Max: Fury Road",
                "start": "00:00:20.000",
                "end": "00:00:24.500",
                "start_seconds": 20.0,
                "end_seconds": 24.5,
                "duration_seconds": 4.5,
                "scene_type": "hook",
                "visual_energy": "high",
                "reason": "Explosive truck chase through the desert",
            }
        ]
        put_res = client.put(f"/api/projects/{p_id}/scenes", json={"scenes": mock_scenes})
        assert put_res.status_code == 200
        data = put_res.json()
        assert data["success"] is True
        assert len(data["scenes"]) == 1
        assert data["scenes"][0]["scene_type"] == "hook"

        # 4. Verify get returns the updated scenes
        get_after = client.get(f"/api/projects/{p_id}/scenes")
        assert get_after.status_code == 200
        assert len(get_after.json()["scenes"]) == 1

        # 5. Test select_scenes when no trailers downloaded (should return 400)
        select_res = client.post(f"/api/projects/{p_id}/select-scenes")
        assert select_res.status_code == 400
        assert "download trailers" in select_res.json()["detail"].lower()

    finally:
        client.delete(f"/api/projects/{p_id}")
