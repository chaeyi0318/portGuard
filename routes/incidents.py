from flask import Blueprint

from db import db

incidents_bp = Blueprint(
    "incidents",
    __name__,
    url_prefix="/vision-api/incidents",
)

@incidents_bp.get("")
def get_incidents():
    incidents = list(
        db["incidents"]
        .find({}, {"_id": 0})   # MongoDB 내부 ID를 응답에서 제외
        .sort("occurredAt", -1)     # 최신순 정렬
        .limit(100)
    )

    for incident in incidents:
        for field in ("occurredAt", "capturedAt", "receivedAt"):
            value = incident.get(field)
            if value is not None:
                incident[field] = value.isoformat()

    return {"incidents": incidents}