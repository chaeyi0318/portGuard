from datetime import datetime, timezone

from pymongo import ReturnDocument

from db import db

# 현재 상태를 키로 사용해서 다음 상태를 찾는 딕셔너리
NEXT_STATUS = {
    "unreviewed": "acknowledged",
    "acknowledged": "in_progress",
    "in_progress": "closed",
}

def transition_incident(event_id, status, note, expected_version):
    incidents = db["incidents"]

    incident = incidents.find_one({"eventId": event_id})

    if incident is None:
        return None, 404, "사건을 찾을 수 없습니다"

    # 앞에서 조회한 직후 다른 사람이 수정할 수도 있으니 최신버전 확인
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
            },      # 새 상태와 마지막 변경 시각 저장
            "$inc": {"version": 1},     # 버전을 1 증가
            "$push": {      # history 배열에 변경 기록 추가
                "history": {
                    "fromStatus": current_status,
                    "toStatus": status,
                    "note": note,
                    "changedAt": now,
                }
            },
        },
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,       # 변경 후 문서 받기
    )

    if updated is None:
        return None, 409, "사건이 변경되었습니다. 새로 조회해 주세요."

    return updated, 200, None