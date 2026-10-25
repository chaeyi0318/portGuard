# 설치와 실행

모든 명령은 저장소 루트에서 실행합니다. 현재 예제는 macOS/zsh와 Python 3.12 기준입니다.

## 1. 설치

이미 `.venv`가 있으면 생성 명령은 생략합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

처음 설정할 때만 복사합니다. 기존 `.env`는 덮어쓰지 않습니다.

```sh
cp .env.example .env
```

`.env`에 아래 항목을 설정합니다. 실제 자격 증명은 Git에 올리지 않습니다.

```dotenv
FLASK_RUN_HOST=127.0.0.1
FLASK_RUN_PORT=5050
FLASK_DEBUG=0
MONGODB_URI="Atlas에서 받은 실제 접속 문자열"
MONGODB_DATABASE=portguard
```

로컬 자동 재시작이 필요하면 `FLASK_DEBUG=1`로 설정합니다.
Atlas에 DB 사용자를 만들고 현재 공인 IP를 접속 허용 목록에 등록해야 합니다.
Flask 개발 서버와 디버그 모드는 최종 운영 서버 구성이 아닙니다.

## 2. DB 연결과 인덱스

```sh
python check_db.py
python init_db.py
```

연결 성공 메시지와 incidents/rois 인덱스 준비 메시지를 확인합니다.
`init_db.py`는 실제 DB에 `eventId`, `roiId` 유일 인덱스를 생성합니다.
기존 데이터에 중복이 있으면 인덱스 생성이 실패할 수 있습니다.

## 3. Flask 서버

터미널 1에서 실행합니다.

```sh
source .venv/bin/activate
python -m flask --app app run
```

- 생존 확인: <http://127.0.0.1:5050/vision-api/health>
- 전체 사건: <http://127.0.0.1:5050/vision-api/incidents?status=all>
- ROI: <http://127.0.0.1:5050/vision-api/rois/ROI-CAM01-01>

health의 `ok`는 Flask 응답 여부이며 DB·분석기 상태를 보장하지 않습니다.

## 4. 영상과 ROI 준비

CAVIAR `Browse2.mpg`를 `data/videos/Browse2.mpg`에 복사합니다.
영상은 저장소에 포함되지 않습니다. 출처는 [영상 문서](video_sources.md)를 참고합니다.
`config/camera.json`에서 아래 값을 확인합니다.

```json
{
  "deviceId": "CAM-01",
  "roiId": "ROI-CAM01-01",
  "input": {"type": "file", "path": "data/videos/Browse2.mpg"}
}
```

위 JSON은 확인할 항목만 발췌한 것으로 기존 전체 설정을 교체하지 않습니다.
현재 분석기는 `roi.points` 대신 DB에서 조회한 ROI 좌표를 사용합니다.
ROI가 없는 새 DB에서만 아래 시험 ROI를 생성합니다.

```sh
curl -i http://127.0.0.1:5050/vision-api/rois \
  -H 'Content-Type: application/json' \
  -d '{"deviceId":"CAM-01","roiId":"ROI-CAM01-01","points":[[0.6,0.3],[0.9,0.3],[0.9,0.9],[0.6,0.9]]}'
```

처음은 201, 이미 존재하면 409입니다. 임의의 기존 ROI를 덮어쓰지 않습니다.
좌표는 원본 영상 기준 0~1이며 지도 좌표가 아닙니다.

## 5. 영상 분석

터미널 2에서 실행합니다. Flask는 계속 실행해 둡니다.

```sh
source .venv/bin/activate
python detect_people.py
```

첫 실행 시 `yolo11s.pt` 모델 다운로드가 필요합니다.
현재 분석기 API 주소는 `http://127.0.0.1:5050`으로 코드에 고정되어 있습니다.
Flask 포트를 바꾸면 분석기의 주소도 맞춰야 합니다.

| 표시 | 의미 |
|---|---|
| 노란 다각형 | DB에서 조회한 ROI |
| 초록 박스·점 | 발밑 점이 ROI 밖 |
| 빨간 박스·점 | 발밑 점이 ROI 내부 또는 경계 |
| ID | 현재 실행의 추적 ID. 영구적인 사람 식별자가 아님 |
| INSIDE / DWELL | 내부 관측 / 누적 체류 기준 도달 |
| OUTSIDE의 초 숫자 | 퇴장 확정 전 보존 중인 내부 체류 시간 |
| UNTRACKED | 추적 ID가 아직 없음 |
| VIDEO | 처리 프레임 번호/FPS 기준 영상 시각 |

기본 체류 2초, 퇴장 1초, 검출 누락 유예 0.5초입니다.
이 값은 `config/camera.json`에서 설정합니다.
사건 신호는 터미널에 출력되며 DB나 MQTT로 전송되지 않습니다.
처리 시간과 화면 대기 때문에 원본 재생 속도보다 느릴 수 있습니다.
설정·코드 변경 후 분석 프로그램을 직접 재시작해야 합니다.

영상 창을 선택하고 영어 소문자 `q`로 종료합니다.
영상 재생만 확인할 때는 `python preview_video.py`를 사용합니다(ROI API 불필요).

## 6. 시험 스크립트

```sh
python check_roi.py
python seed_incident.py
python check_incident_save.py
```

`check_roi.py`는 좌표 검증만 합니다.
나머지 두 명령은 실제 DB에 합성 시험 사건을 저장합니다.
동일 ID가 있으면 추가 저장하지 않으며, 상태를 초기화하는 명령은 아닙니다.
`check_incident_save.py`의 첫 저장은 True, 이후 동일 ID는 False가 예상 결과입니다.

## 7. 가상 경광등

영상 분석과 별도 작업입니다. Docker 브로커, MQTT worker, 에이전트 실행과 장애 재현은
[beacon.md](beacon.md)를 따릅니다. 현재 worker는 CAM-01 사건 수신용이 아닙니다.

## 문제 해결

- Flask 404: 파일 저장 후 `python -m flask --app app routes`로 등록 주소를 확인합니다.
- 분석 시작 시 ROI 404: DB의 ROI ID와 `camera.json`의 ID를 맞춥니다.
- 영상 열기 실패: 실제 파일명·확장자와 설정 경로를 확인합니다.
- Atlas 연결 실패: `python check_db.py`로 분리 확인하고 현재 공인 IP 허용 여부를 봅니다.
  TLS 오류 원인은 IP만으로 확정하지 않습니다. 계속 실패하면 네트워크·인증서도 확인합니다.
- 포트 사용 중: 기존 서버 터미널을 확인하고 중복 서버 실행을 피합니다.
- 감지 ID 변경·의자 오탐: 알려진 미해결 항목입니다. 추적 ID가 바뀌면 중복 방지가 이어지지 않습니다.
