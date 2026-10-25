import json
import sys
from pathlib import Path

import cv2

from db import client
from services.incident_input import validate_incident_input
from services.incidents import save_incident


BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "data" / "evidence"


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "사용법: python import_incident.py 사건ID"
        )

    from uuid import UUID

    try:
        event_id = str(UUID(sys.argv[1]))
    except ValueError:
        raise SystemExit("사건 ID는 UUID 형식이어야 합니다.") from None

    record_path = EVIDENCE_DIR / f"{event_id}.json"

    if not record_path.is_file():
        raise SystemExit("사건 JSON 파일이 없습니다.")

    with record_path.open(encoding="utf-8") as file:
        event = validate_incident_input(json.load(file))

    if event["eventId"] != event_id:
        raise SystemExit("파일명과 JSON의 사건 ID가 다릅니다.")

    image_path = EVIDENCE_DIR / event["evidence"]["fileName"]

    if not image_path.is_file():
        raise SystemExit("증거 이미지 파일이 없습니다.")

    # JPEG 시그니처와 실제 디코딩 확인
    with image_path.open("rb") as file:
        if file.read(3) != b"\xff\xd8\xff":
            raise SystemExit("JPEG 형식의 파일이 아닙니다.")

    image = cv2.imread(str(image_path))

    if image is None:
        raise SystemExit("증거 이미지를 읽을 수 없습니다.")

    incident, created = save_incident(event)

    print("신규 저장:", created)
    print("사건 ID:", incident["eventId"])
    print("증거 파일:", incident["evidence"]["fileName"])


if __name__ == "__main__":
    try:
        main()
    finally:
        client.close()