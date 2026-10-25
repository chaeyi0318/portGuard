import json
from pathlib import Path

from services.incident_input import validate_incident_input


BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "data" / "evidence"


def main():
    records = list(EVIDENCE_DIR.glob("*.json"))

    if not records:
        raise SystemExit("사건 JSON이 없습니다. 영상 분석을 먼저 실행해 주세요.")

    record_path = max(records, key=lambda path: path.stat().st_mtime)

    with record_path.open(encoding="utf-8") as file:
        data = json.load(file)

    try:
        event = validate_incident_input(data)
    except ValueError as error:
        raise SystemExit(f"검증 실패: {error}") from None

    print("검증 성공!")
    print("파일:", record_path.name)
    print("사건 ID:", event["eventId"])
    print("발생 시각 타입:", type(event["occurredAt"]).__name__)
    print("증거 파일:", event["evidence"]["fileName"])


if __name__ == "__main__":
    main()