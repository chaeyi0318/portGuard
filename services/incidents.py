from datetime import datetime, timezone

from pymongo import ReturnDocument

from db import db

NEXT_STATUS = {
    "unreviewed": "acknowledged",
    "acknowledged": "in_progress",
    "in_progress": "closed",
}

def transition_incident(event_id, status, note, expected_version):
    incidents = db["incidents"]

    incident = incidents.find_one(
        {
            "evnetId": event_id
        }
    )

    if incident is None:
        return None, 404, "사건을 찾을 수 없습니다"
    
    if incident["version"] != expected_version:
        return None, 409, "사건이 변경되었습니다. 새로 조회해 주세요."

    current_status = incident["status"]

    if NEXT_STATUS.get(current_status) != status:
        return None, 409, "허용되지 않는 상태 변경입니다."

    now = datetime.now(timezone.utc)

    updated = incidents.find_one_and_update(
        {
            "eventId": event_id,
            "version": expected_version,
            "status": current_status
        },
        {
            "$set": {
                "status": status,
                "updatedAt": now,
            },
            "$inc": {"version": 1},
            "$push": {
                "history": {
                    "fromStatus": current_status,
                    "toStatus": status,
                    "note": note,
                    "changedAt": now,
                }
            },
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )

    if updated is None:
        return None, 409, "사건이 변경되었습니다. 새로 조회해 주세요."

    return updated, 200, None