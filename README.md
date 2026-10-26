# PortGuard

항만 안전 관제를 위한 독립 Python 영상 분석·Flask 백엔드 서비스입니다.
QuayPilot 저장소와 합치지 않고 API·MQTT·영상 스트림으로 연동합니다.
MongoDB 접속 정보는 서버의 `.env`에서만 관리합니다.

## 문서

- [설치·실행·종료·문제 해결](docs/running.md)
- [현재 작업 상황과 남은 작업](docs/progress.md)
- [현재 폴더 구조와 파일 역할](docs/structure.md)
- [수동 검증 기록](docs/verification.md)
- [영상 출처와 시험 계획](docs/video_sources.md)
- [가상 경광등 실행·API·MQTT 계약](docs/beacon.md)
- [영상 사건 MQTT·outbox·저장 ACK](docs/vision_mqtt.md)

## 빠른 실행

저장소 루트에서 실행합니다. Python 3.12와 GUI를 사용할 수 있는 로컬 환경을 기준으로 합니다.
처음 설치·DB 설정·ROI 생성은 [실행 문서](docs/running.md)를 먼저 확인합니다.

터미널 1 — Flask:

```sh
source .venv/bin/activate
python -m flask --app app run --port 5001
```

터미널 2 — 영상 분석:

```sh
source .venv/bin/activate
python detect_people.py
```

영상: `data/videos/Browse2.mpg`, ROI: `ROI-CAM01-01`이 기본 설정입니다.
분석기는 시작할 때 Flask에서 ROI를 조회하므로 Flask가 먼저 실행되어야 합니다.
영상 창에서 영어 소문자 `q`로 종료합니다. Flask는 해당 터미널에서 `Ctrl+C`로 종료합니다.

## 현재 동작 범위

- 사건 저장 서비스, 목록·상세·상태 처리 API와 MongoDB 중복 방지
- ROI 생성·조회·좌표 검증
- 영상 파일의 YOLO 감지·추적, ROI 안팎, 체류·퇴장·누락 유예, 사건 신호 출력
- 별도 가상 경광등 에이전트·MQTT worker·명령 API 코드

영상 분석은 사건 JSON·증거 JPEG를 로컬에 생성합니다. `import_incident.py 사건ID`로 검증 후 DB에 수동 저장합니다.
증거 조회 API를 구현했습니다. CAM-01 사건 MQTT·outbox·저장 ACK를 구현했습니다(기존 사건 실제 브로커 전송·ACK 확인). MJPEG·Socket.IO·점검은 아직 구현되지 않았습니다.
가상 경광등 구현과 CAM-01 구현을 구분합니다. 세부 검증 상태는 진행 문서를 확인합니다.

## 증거 이미지 조회

Flask와 증거 파일이 같은 컴퓨터에 있어야 합니다. DB에 저장된 사건의 JPEG를 반환합니다.

```sh
curl -f http://127.0.0.1:5000/vision-api/incidents/사건ID/evidence -o evidence.jpg
```

성공: `200 image/jpeg`. UUID 형식 오류: `400`. 사건·증거 정보·파일 없음: `404` JSON.
이미지는 프로젝트의 `data/evidence/`에서 조회하며 서버로의 이미지 전송은 후속 작업입니다.
