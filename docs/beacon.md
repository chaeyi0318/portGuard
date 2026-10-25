# 경광등 시뮬레이터 v0.1

BEACON-01 전용 초기 구현. 카메라와 기존 사건 상태 계약은 변경하지 않는다.
모든 장비·명령·회신은 simulated=true. 실제 경광등이나 UI 애니메이션은 없다.

## 실행

저장소 루트에서 기존 MongoDB 설정을 유지하고 `.env.example`의 MQTT 설정을
`.env`에 추가한다. 로컬 브로커는 인증 없이 localhost에만 포트를 공개한다.

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
docker compose -f compose.beacon.yaml up -d
```

각각 별도 터미널에서 가상환경을 활성화한 뒤 실행한다.

```sh
python -m flask --app app run
python -m mqtt.worker
python -m agents.beacon
```

세 명령은 각각 별도 프로세스이다. MQTT worker는 배포당 반드시 한 개만 실행한다.
worker 시작 시 devices.deviceId와 commands.commandId 유일 인덱스를 만든다.
에이전트와 worker는 자동으로 브로커에 재연결한다. DB 정보는 에이전트에서 사용하지 않는다.

## 시험

```sh
curl -s http://127.0.0.1:5050/vision-api/devices
curl -s -X POST http://127.0.0.1:5050/vision-api/devices/BEACON-01/commands \
  -H 'Content-Type: application/json' -d '{"action":"turn_on"}'
```

202 응답의 command.commandId를 아래 ID 자리에 넣는다.

```sh
curl -s http://127.0.0.1:5050/vision-api/commands/ID
curl -s http://127.0.0.1:5050/vision-api/devices/BEACON-01/history
```

끄기는 action=turn_off. 명령 응답 예시(시각·ID는 실행마다 달라짐):

```json
{"command":{"commandId":"UUID","deviceId":"BEACON-01","action":"turn_on","simulated":true,"status":"queued","requestedAt":"2026-10-25T09:00:00+00:00","deadlineAt":"2026-10-25T09:00:10+00:00","history":[{"status":"queued","at":"2026-10-25T09:00:00+00:00"}]}}
```

명령: queued → sent → accepted → succeeded 또는 failed.
전송/접수는 작동 성공이 아니다. 마감 10초까지 결과가 없으면 timed_out.
회신이 빠르면 sent가 이력에 없을 수 있다. 종결 결과와 시간 초과는 늦은 회신으로 덮어쓰지 않는다.
HTTP 재요청은 새 명령이므로 새 ID를 만든다. 같은 ID의 MQTT 재전송만 중복 방지한다.

장비: 시작 checking/unknown → 첫 유효 관측 online/on 또는 online/off.
3초 heartbeat, 마지막 유효 메시지 이후 10초 초과 시 disconnected.
연결 끊김은 전원 차단이나 종료 원인을 뜻하지 않는다. 마지막 작동 상태와 observedAt을 유지한다.
재연결 시 새 상태 보고를 받아야 online으로 복구한다.

에이전트를 Ctrl+C로 종료하고 다음 모드로 다시 실행한 후 새 명령을 보낸다.

```sh
python -m agents.beacon --mode fail
python -m agents.beacon --mode timeout
```

fail은 accepted 후 failed. timeout은 accepted만 전송하며 heartbeat는 계속 정상이다.
각 모드는 하나씩 실행한다. 정상 모드 재시작은 `python -m agents.beacon`.
에이전트 종료 후 10초 지나면 연결 끊김, 재실행 후 복구 이력을 확인한다.
로컬 data/beacon.sqlite3에 명령 결과와 모의 출력 상태를 보존한다.

## MQTT 계약

- devices/BEACON-01/commands: Flask worker → 에이전트, QoS 1, retain=false
- devices/BEACON-01/acks: 에이전트 → worker, 접수와 결과, QoS 1
- devices/BEACON-01/status: 접속 직후 현재 출력 상태, QoS 1
- devices/BEACON-01/heartbeat: 3초 주기 현재 출력 상태, QoS 1

에이전트 발행 공통 필드:

```json
{"deviceId":"BEACON-01","sessionId":"UUID","sessionStartedAt":"2026-10-25T09:00:00+00:00","sequence":1,"sentAt":"2026-10-25T09:00:03+00:00","simulated":true,"operationStatus":"off"}
```

ACK는 commandId와 status(accepted/succeeded/failed)를 추가한다.
sequence는 세 토픽을 통틀어 세션 안에서 증가한다.
worker는 중복·역순·이전 세션과 10초 넘은 메시지를 무시한다.
명령 메시지는 commandId/deviceId/action/simulated/requestedAt/deadlineAt을 갖는다.
에이전트는 마감된 명령과 retained 명령을 실행하지 않는다.
worker는 미완료 명령을 2초 간격으로 재전송한다. 에이전트는 SQLite 결과를 재회신한다.

## 저장 및 제한

MongoDB devices: 현재 연결/출력 상태, 세션·sequence, lastSeenAt, observedAt, 최근 1000개 연결 변경 이력.
MongoDB commands: 요청·기한·전송 시각, 상태, 변경 이력. 장비 이력 API는 최근 100개 반환.
현재 상태와 명령 처리는 worker 한 개에서 순차 수행한다.
장비 메시지와 MongoDB 쓰기는 트랜잭션으로 묶지 않으며, 장애 시 재전송으로 명령 결과를 재처리한다.
시계 동기화가 필요하다. 장비 시계가 서버보다 5초 이상 빠르면 수신을 거절한다.

초기 범위에는 LWT/retained 상태, Socket.IO, 점검 API, 부저·게이트, 자동 침입 연동,
전체 서비스 Docker 패키지가 포함되지 않는다. CAM-01 장비 목록 통합은 해당 서비스 구현 시 추가한다.
실제 QuayPilot과의 계약 검증은 아직 수행하지 않았다.

## 검증

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

mongomock과 MQTT publish 대역으로 API→에이전트→worker→DB 흐름,
중복 방지, 역순·이전 세션 무시, 실패·시간 초과, 장애·복구를 검증한다.
실제 MQTT 브로커·MongoDB를 사용하는 실행 검증과 구분한다.
