# PortGuard

항만 안전 관제를 위한 독립 Python·Flask 서비스.
QuayPilot과 API·MQTT·영상 스트림으로 연동한다.

## 개발 환경

- Python 3.12
- Flask
- MongoDB·MQTT·영상 분석은 추후 구현

## 처음 설치

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

기존 `.env`가 있으면 복사하지 않고 필요한 설정만 수정한다.
`.env`에는 서버 설정과 접속 정보를 저장하며 Git에 올리지 않는다.

## 로컬 실행

```sh
source .venv/bin/activate
python -m flask --app app run
```

상태 확인: http://127.0.0.1:5050/vision-api/health

정상 응답:

```json
{"service": "portguard", "status": "ok"}
```

종료: 실행 중인 터미널에서 Ctrl+C

자동 재시작이 필요하면 로컬 `.env`의 `FLASK_DEBUG`를 `1`로 설정한다.
디버그 모드는 로컬 개발에서만 사용한다.

## 현재 구현

- 서버 생존 확인: GET /vision-api/health

이 응답은 Flask 서버의 응답 여부만 나타낸다.
DB 연결이나 영상 분석의 정상 동작을 뜻하지 않는다.
## 가상 경광등

BEACON-01 독립 에이전트, MQTT worker, 장비 조회·명령·이력 API가 추가되었다.
[실행 방법과 API·MQTT 계약](beacon.md)을 참고한다.
