from uuid import uuid4

import mongomock
import pytest

from app import app
from routes import incidents


@pytest.fixture
def evidence_api(monkeypatch, tmp_path):
    database = mongomock.MongoClient().test
    monkeypatch.setattr(incidents, "db", database)
    monkeypatch.setattr(incidents, "EVIDENCE_DIR", tmp_path)
    event_id = str(uuid4())
    database.incidents.insert_one({
        "eventId": event_id,
        "evidence": {"fileName": f"{event_id}.jpg", "contentType": "image/jpeg"},
    })
    return app.test_client(), database, tmp_path, event_id


def test_returns_registered_image(evidence_api):
    api, _, folder, event_id = evidence_api
    content = b"\xff\xd8\xfftest"
    (folder / f"{event_id}.jpg").write_bytes(content)
    response = api.get(f"/vision-api/incidents/{event_id}/evidence")
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert response.data == content
    response.close()


def test_missing_incident_file_and_invalid_id(evidence_api):
    api, _, _, event_id = evidence_api
    for value, expected in [(str(uuid4()), 404), (event_id, 404), ("invalid", 400)]:
        response = api.get(f"/vision-api/incidents/{value}/evidence")
        assert response.status_code == expected
        assert "error" in response.json


def test_rejects_untrusted_filename_and_external_symlink(evidence_api, tmp_path):
    api, database, folder, event_id = evidence_api
    database.incidents.update_one({}, {"$set": {"evidence.fileName": "../outside.jpg"}})
    assert api.get(f"/vision-api/incidents/{event_id}/evidence").status_code == 404
    database.incidents.update_one({}, {"$set": {"evidence.fileName": f"{event_id}.jpg"}})
    outside = folder.parent / f"{uuid4()}.jpg"
    outside.write_bytes(b"private")
    try:
        (folder / f"{event_id}.jpg").symlink_to(outside)
        assert api.get(f"/vision-api/incidents/{event_id}/evidence").status_code == 404
    finally:
        outside.unlink()
