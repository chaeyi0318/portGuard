from pathlib import Path
import os

import cv2
import numpy as np
import requests
from ultralytics import YOLO
from uuid import uuid4
from datetime import datetime, timezone

from evidence import save_evidence, save_event_record
from dwell_tracker import DwellTracker
from roi_geometry import get_foot_point, is_foot_inside_roi
from settings import load_camera_config


BASE_DIR = Path(__file__).resolve().parent


def main():
    config = load_camera_config()

    session_id = str(uuid4())
    session_started_at = datetime.now(timezone.utc).isoformat()

    video_path = BASE_DIR / config["input"]["path"]

    # Flask에서 저장된 ROI 조회
    roi_id = config["roiId"]

    response = requests.get(
        f"{os.getenv('VISION_API_URL', 'http://127.0.0.1:5001').rstrip('/')}/vision-api/rois/{roi_id}",
        timeout=5,
    )
    response.raise_for_status()
    roi = response.json()["roi"]

    if roi["deviceId"] != config["deviceId"]:
        raise SystemExit("ROI의 카메라와 영상 설정의 카메라가 다릅니다.")

    points = roi["points"]

    model = YOLO("yolo11s.pt")
    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        capture.release()
        raise SystemExit(f"영상을 열 수 없습니다: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)

    if not np.isfinite(fps) or fps <= 0:
        capture.release()
        raise SystemExit("영상 FPS를 확인할 수 없습니다.")

    frame_index = 0

    dwell_tracker = DwellTracker(
        grace_seconds=config["thresholds"]["detectionGraceSeconds"],
        exit_seconds=config["thresholds"]["exitSeconds"],
        dwell_seconds=config["thresholds"]["dwellSeconds"],
    )

    try:
        while True:
            success, frame = capture.read()

            if not success:
                print("영상 분석을 종료합니다.")
                break

            captured_at = datetime.now(timezone.utc).isoformat()
            # 처리 속도와 별개로 원본 영상의 시각 사용
            video_time = frame_index / fps
            frame_index += 1

            height, width = frame.shape[:2]

            # ROI를 픽셀 좌표로 변환
            polygon = np.array(
                [
                    [round(x * width), round(y * height)]
                    for x, y in points
                ],
                dtype=np.int32,
            )

            # 사람 감지 및 추적
            result = model.track(
                frame,
                persist=True,
                tracker=str(BASE_DIR / "config" / "bytetrack.yaml"),
                classes=[0],
                conf=0.1,
                verbose=False,
            )[0]

            boxes = result.boxes.xyxy.cpu().tolist()

            if result.boxes.id is not None:
                track_ids = result.boxes.id.int().cpu().tolist()
            else:
                track_ids = [None] * len(boxes)

            # ID가 있는 사람의 안팎 관측 결과
            observations = {
                track_id: is_foot_inside_roi(
                    box,
                    points,
                    width,
                    height,
                )
                for box, track_id in zip(boxes, track_ids)
                if track_id is not None
            }

            # 누락 유예를 적용한 체류 시간 계산
            durations = dwell_tracker.update(
                video_time,
                observations,
            )

            # 위험구역 표시
            cv2.polylines(
                frame,
                [polygon],
                True,
                (0, 255, 255),
                2,
            )

            for box, track_id in zip(boxes, track_ids):
                inside = is_foot_inside_roi(
                    box,
                    points,
                    width,
                    height,
                )

                dwell = durations.get(track_id, 0.0)
                color = (0, 0, 255) if inside else (0, 255, 0)

                x1, y1, x2, y2 = map(round, box)
                foot_x, foot_y = get_foot_point(box)

                # 사람 박스
                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2,
                )

                # 발밑 중앙점
                cv2.circle(
                    frame,
                    (round(foot_x), round(foot_y)),
                    4,
                    color,
                    -1,
                )

                dwell_limit = config["thresholds"]["dwellSeconds"]

                if track_id is None:
                    state_label = "UNTRACKED"
                elif not inside:
                    state_label = "OUTSIDE"
                elif dwell >= dwell_limit:
                    state_label = "DWELL"
                else:
                    state_label = "INSIDE"

                label = (
                    f"ID:{track_id} "
                    f"{state_label} "
                    f"{dwell:.1f}s"
                )

                cv2.putText(
                    frame,
                    label,
                    (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1,
                )

            # 원본 영상 시각 표시
            cv2.putText(
                frame,
                f"VIDEO {video_time:.2f}s",
                (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

            for event in dwell_tracker.new_events:
                event_id = str(uuid4())
                evidence = save_evidence(event_id, frame)

                record = {
                    "eventId": event_id,
                    "deviceId": config["deviceId"],
                    "roiId": roi["roiId"],
                    "roiVersion": roi["version"],
                    "trackId": event["trackId"],
                    "sessionId": session_id,
                    "sessionStartedAt": session_started_at,
                    "eventType": "intrusion",
                    "source": "recorded_video",
                    "inputFileName": video_path.name,
                    "occurredAt": datetime.now(timezone.utc).isoformat(),
                    "capturedAt": captured_at,
                    "videoTimeSeconds": event["videoTime"],
                    "dwellSeconds": event["dwellSeconds"],
                    "evidence": evidence,
                }

                record_path = save_event_record(record)

                print(
                    f"[침입 시험] 사건:{event_id} "
                    f"영상:{event['videoTime']:.2f}s "
                    f"기록:{record_path.name}"
                )

            cv2.imshow("PortGuard ROI - Q to quit", frame)

            if cv2.waitKey(40) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
