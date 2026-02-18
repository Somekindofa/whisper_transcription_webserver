from fastapi.testclient import TestClient

from server.main import app
from server import db


client = TestClient(app)


def test_patch_queue_item_updates_language_and_speakers(tmp_path):
    # Ensure DB exists
    db.init_db()

    # Create a queue item with defaults
    file_id = db.create_queue_item(
        original_name="audio.wav",
        stored_path="/tmp/audio.wav",
        size_bytes=12345,
        language="fr",
        speakers=1,
    )

    # Update language and speakers via API
    resp = client.patch(f"/api/queue/{file_id}", json={"language": "en", "speakers": 2})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["language"] == "en"
    assert data["speakers"] == 2

    # Confirm DB was updated
    item = db.get_queue_item_by_id(file_id)
    assert item["language"] == "en"
    assert item["speakers"] == 2


def test_processing_seconds_exposed_in_list(tmp_path):
    db.init_db()

    file_id = db.create_queue_item(
        original_name="audio2.wav",
        stored_path="/tmp/audio2.wav",
        size_bytes=11111,
        language="en",
        speakers=1,
    )

    # Simulate processing time being recorded
    db.update_processing_time(file_id, 12.34)

    resp = client.get('/api/queue')
    assert resp.status_code == 200
    items = resp.json()
    found = [i for i in items if i['id'] == file_id]
    assert found
    assert 'processing_seconds' in found[0]
    assert abs(found[0]['processing_seconds'] - 12.34) < 0.001

