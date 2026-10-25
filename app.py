from flask import Flask
from db import db

app = Flask(__name__)

@app.get("/vision-api/health")
def health():
    return {
        "status": "ok",
        "service": "portguard",
    }

@app.get("/vision-api/incidents")
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