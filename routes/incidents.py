from flask import Blueprint, request

from db import db

incidents_bp = Blueprint(
    "incidents",
    __name__,
    url_prefix="/vision-api/incidents",
)

@incidents_bp.get("")
def get_incidents():
    status = request.args.get("status", "open")

    valid_statuses = {
        "unreviewed",
        "acknowledged",
        "in_progress",
        "closed",
    }

    if status == "all":
        query = {}
    elif status == "open":
        query = {"status": {"$in": sorted(valid_statuses - {"closed"})}}
    elif status in valid_statuses:
        query = {"status": status}
    else:
        return {"error": "지원하지 않는 status입니다."}, 400
    
    incidents = list(
        db["incidents"]
        .find(query, {"_id": 0})   # MongoDB 내부 ID를 응답에서 제외
        .sort("occurredAt", -1)     # 최신순 정렬
        .limit(100)
    )

    for incident in incidents:
        for field in ("occurredAt", "capturedAt", "receivedAt"):
            value = incident.get(field)
            if value is not None:
                incident[field] = value.isoformat()

    return {"incidents": incidents}