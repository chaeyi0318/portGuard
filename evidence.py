from pathlib import Path
from uuid import UUID

import cv2
import json


BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "data" / "evidence"


def save_evidence(event_id, frame):
    # UUID 형식만 허용해서 파일 경로로 안전하게 사용
    safe_id = str(UUID(event_id))

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    image_path = EVIDENCE_DIR / f"{safe_id}.jpg"

    success, encoded = cv2.imencode(
        ".jpg",
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, 90],
    )

    if not success:
        raise RuntimeError("증거 이미지 변환에 실패했습니다.")

    # 같은 사건의 이미지를 실수로 덮어쓰지 않음
    with image_path.open("xb") as file:
        file.write(encoded.tobytes())

    return {
        "fileName": image_path.name,
        "contentType": "image/jpeg",
    }

def save_event_record(event):
    safe_id = str(UUID(event["eventId"]))
    record_path = EVIDENCE_DIR / f"{safe_id}.json"

    with record_path.open("x", encoding="utf-8") as file:
        json.dump(event, file, ensure_ascii=False, indent=2)

    return record_path