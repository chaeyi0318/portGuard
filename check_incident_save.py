from datetime import datetime, timezone

from db import client
from services.incidents import save_incident


now = datetime.now(timezone.utc)

event = {
    "eventId": "TEST-SAVE-001",
    "deviceId": "CAM-01",
    "roiId": "ROI-CAM01-01",
    "trackId": 40,
    "sessionId": "TEST-SESSION-001",
    "source": "synthetic",
    "occurredAt": now,
    "capturedAt": now,
    "videoTimeSeconds": 22.52,
    "dwellSeconds": 2.0,
    "evidence": None,
}

try:
    incident, created = save_incident(event)

    print("신규 저장:", created)
    print("사건 ID:", incident["eventId"])
    print("처리 상태:", incident["status"])
    print("버전:", incident["version"])
finally:
    client.close()