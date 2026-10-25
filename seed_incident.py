from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from db import client, db

now = datetime.now(timezone.utc)

incident = {
    "eventId": "TEST-INCIDENT-001",
    "deviceId": "CAM-01",
    "roiId": "ROI-CAM01-01",
    "trackId": "TEST-TRACK-001",
    "eventType": "intrusion",
    "source": "synthetic",
    "occurredAt": now,
    "capturedAt": now,
    "receivedAt": now,
    "status": "unreviewed",
    "version": 1,
    "evidence": None,
    "history": [],
}

try:
    db["incidents"].insert_one(incident)
    print("시험 사건 저장 완료")
except DuplicateKeyError:
    print("중복 사건, 저장X")
finally:
    client.close()