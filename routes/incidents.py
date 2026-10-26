from pathlib import Path
from uuid import UUID

from flask import Blueprint, request, send_from_directory

from db import db

from services.incidents import transition_incident
from serializers import serialize_incident
from socket_server import socketio

incidents_bp = Blueprint(
    "incidents",
    __name__,
    url_prefix="/vision-api/incidents",
)

EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "evidence"


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

    return {
        "incidents": [
            serialize_incident(incident)
            for incident in incidents
        ]
    }


@incidents_bp.get("/<event_id>")
def get_incident(event_id):
    incident = db["incidents"].find_one(
        {"eventId": event_id},
        {"_id": 0},
    )

    if incident is None:
        return {"error": "사건을 찾을 수 없습니다"}, 404

    return {"incident": serialize_incident(incident)}


@incidents_bp.get("/<event_id>/evidence")
def get_incident_evidence(event_id):
    try:
        safe_id = str(UUID(event_id))
    except ValueError:
        return {"error": "사건 ID는 UUID 형식이어야 합니다."}, 400

    incident = db["incidents"].find_one({"eventId": safe_id}, {"_id": 0})
    if incident is None:
        return {"error": "사건을 찾을 수 없습니다"}, 404

    evidence = incident.get("evidence")
    file_name = f"{safe_id}.jpg"
    if (
        not isinstance(evidence, dict)
        or evidence.get("fileName") != file_name
        or evidence.get("contentType") != "image/jpeg"
    ):
        return {"error": "증거 이미지 정보가 없습니다."}, 404

    image_path = (EVIDENCE_DIR / file_name).resolve()
    if image_path.parent != EVIDENCE_DIR.resolve() or not image_path.is_file():
        return {"error": "증거 이미지 파일이 없습니다."}, 404

    return send_from_directory(EVIDENCE_DIR, file_name, mimetype="image/jpeg")


@incidents_bp.post("/<event_id>/transition")
def post_incident_transition(event_id):
    if not request.is_json:
        return {"error": "JSON 형식으로 요청해주세요"}, 400

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {"error": "JSON 객체를 보내 주세요."}, 400

    status = data.get("status")
    note = data.get("note")
    expected_version = data.get("expectedVersion")

    if status not in ("acknowledged", "in_progress", "closed"):
        return {"error": "지원하지 않는 처리 상태입니다."}, 400

    if not isinstance(note, str):
        return {"error": "note는 문자열이어야 합니다."}, 400

    if type(expected_version) is not int or expected_version < 1:
        return {"error": "expectedVersion은 1 이상의 정수여야 합니다."}, 400

    incident, status_code, error = transition_incident(
        event_id,
        status,
        note,
        expected_version,
    )

    if error is not None:
        return {"error": error}, status_code

    serialized = serialize_incident(incident)

    socketio.emit(
        "incident.updated",
        {"incident": serialized},
    )

    return {"incident": serialized}, status_code
