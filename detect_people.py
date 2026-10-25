from pathlib import Path

import cv2
import numpy as np
import requests
from ultralytics import YOLO

from roi_geometry import get_foot_point, is_foot_inside_roi
from settings import load_camera_config


BASE_DIR = Path(__file__).resolve().parent


def main():
    config = load_camera_config()
    video_path = BASE_DIR / config["input"]["path"]

    # Flask에서 저장된 ROI 조회
    roi_id = config["roiId"]

    response = requests.get(
        f"http://127.0.0.1:5050/vision-api/rois/{roi_id}",
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

    try:
        while True:
            success, frame = capture.read()

            if not success:
                print("영상 분석을 종료합니다.")
                break

            height, width = frame.shape[:2]

            # 정규화 좌표를 영상 픽셀 좌표로 변환
            polygon = np.array(
                [
                    [round(x * width), round(y * height)]
                    for x, y in points
                ],
                dtype=np.int32,
            )

            # 원본 프레임에서 사람 감지 및 추적
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

                # 박스 발밑 중앙점
                cv2.circle(
                    frame,
                    (round(foot_x), round(foot_y)),
                    4,
                    color,
                    -1,
                )

                # 추적 ID와 안팎 상태
                label = (
                    f"ID:{track_id} "
                    f"{'INSIDE' if inside else 'OUTSIDE'}"
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

            cv2.imshow("PortGuard ROI - Q to quit", frame)

            if cv2.waitKey(40) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()