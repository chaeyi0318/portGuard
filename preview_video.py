from pathlib import Path
import time

import cv2

from settings import load_camera_config


BASE_DIR = Path(__file__).resolve().parent


def main():
    config = load_camera_config()
    video_path = BASE_DIR / config["input"]["path"]

    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        capture.release()
        raise SystemExit(f"영상을 열 수 없습니다: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        capture.release()
        raise SystemExit("영상 FPS를 확인할 수 없습니다.")

    frame_interval = 1 / fps

    try:
        while True:
            started_at = time.monotonic()
            success, frame = capture.read()

            if not success:
                print("영상 재생을 종료합니다.")
                break

            cv2.imshow("PortGuard Preview - Q to quit", frame)

            elapsed = time.monotonic() - started_at
            wait_ms = max(1, round((frame_interval - elapsed) * 1000))

            if cv2.waitKey(wait_ms) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()