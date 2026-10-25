from datetime import datetime, timezone
import math
from uuid import UUID

def parse_event_datetime(value, field_name):
    if not isinstance(value, str):
        raise ValueError(f"{field_name}은 날짜 문자열이어야 합니다.")

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        raise ValueError(
            f"{field_name}의 날짜 형식이 올바르지 않습니다."
        ) from None

    if parsed.tzinfo is None:
        raise ValueError(
            f"{field_name}에는 시간대 정보가 필요합니다."
        )

    return parsed.astimezone(timezone.utc)

def validate_incident_input(data):
    if not isinstance(data, dict):
        raise ValueError("사건 데이터는 JSON 객체여야 합니다.")

    result = dict(data)

    for field in ("deviceId", "roiId", "sessionId"):
        value = result.get(field)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field}가 필요합니다.")

    event_id = result.get("eventId")

    if not isinstance(event_id, str):
        raise ValueError("eventId는 문자열이어야 합니다.")

    try:
        normalized_id = str(UUID(event_id))
    except ValueError:
        raise ValueError("eventId는 UUID 형식이어야 합니다.") from None

    if event_id != normalized_id:
        raise ValueError("eventId는 소문자 표준 UUID 형식이어야 합니다.")

    if result.get("eventType") != "intrusion":
        raise ValueError("지원하지 않는 사건 종류입니다.")

    if result.get("source") != "recorded_video":
        raise ValueError("현재는 영상 파일 사건만 지원합니다.")

    track_id = result.get("trackId")

    if type(track_id) is not int or track_id < 0:
        raise ValueError("trackId는 0 이상의 정수여야 합니다.")

    roi_version = result.get("roiVersion")

    if type(roi_version) is not int or roi_version < 1:
        raise ValueError("roiVersion은 1 이상의 정수여야 합니다.")

    for field in ("videoTimeSeconds", "dwellSeconds"):
        value = result.get(field)

        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{field}는 0 이상의 유한한 숫자여야 합니다.")

    for field in ("sessionStartedAt", "occurredAt", "capturedAt"):
        result[field] = parse_event_datetime(
            result.get(field),
            field,
        )

    if result["capturedAt"] > result["occurredAt"]:
        raise ValueError("캡처 시각이 사건 판정 시각보다 늦습니다.")

    evidence = result.get("evidence")

    if not isinstance(evidence, dict):
        raise ValueError("증거 이미지 정보가 필요합니다.")

    if evidence.get("fileName") != f"{event_id}.jpg":
        raise ValueError("증거 파일명이 사건 ID와 일치하지 않습니다.")

    if evidence.get("contentType") != "image/jpeg":
        raise ValueError("증거 이미지는 JPEG 형식이어야 합니다.")

    return result