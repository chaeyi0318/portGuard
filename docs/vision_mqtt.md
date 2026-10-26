# 영상 사건 MQTT 전송

분석기는 `data/evidence/{eventId}.json`과 JPEG를 생성합니다.
별도 sender가 이 파일을 3초마다 확인해 QoS 1로 전송합니다.
분석 종료 후에도 sender를 실행해 두면 미전송 사건을 계속 재시도합니다.

## 실행

Docker Desktop 실행 후 브로커를 준비합니다.

```sh
docker compose -f compose.beacon.yaml up -d
```

각 명령을 별도 터미널에서 저장소 루트 기준으로 실행합니다.

```sh
source .venv/bin/activate
python -m flask --app app run --port 5001
```

```sh
source .venv/bin/activate
python -m mqtt.worker
```

```sh
source .venv/bin/activate
python -m mqtt.vision_sender
```

```sh
source .venv/bin/activate
VISION_API_URL=http://127.0.0.1:5001 python detect_people.py
```

worker는 배포당 하나만 실행합니다. 기존 BEACON-01도 같은 worker가 처리합니다.
브로커 접속 설정은 기존 MQTT_HOST/MQTT_PORT/MQTT_USERNAME/MQTT_PASSWORD/MQTT_TLS를 사용합니다.

## 계약

- `devices/CAM-01/events`: `{ "event": 사건JSON, "imageBase64": JPEG의base64 }`
- `devices/CAM-01/acks`: `{ "deviceId": "CAM-01", "eventId": "UUID", "status": "stored" }`
- 두 메시지 모두 QoS 1, retain=false.
- JPEG는 최대 2 MiB, 전체 메시지는 최대 3 MiB입니다. 실제 JPEG 디코딩도 검사합니다.
- 서버는 JPEG를 원자적으로 배치하고 MongoDB 저장 성공 후 ACK를 보냅니다.
- 동일 eventId 재전송은 기존 DB 사건을 재사용합니다. 기존 JPEG와 다른 내용은 거부합니다.
- ACK가 오기 전에는 반복 전송합니다. MQTT의 전송 성공 자체를 저장 성공으로 취급하지 않습니다.
- ACK 수신 후 로컬 `.acked` 파일을 만듭니다. 재시작해도 확인된 사건은 전송하지 않습니다.
- 원본 JSON·JPEG는 삭제하지 않습니다. 분석기와 sender는 같은 data/evidence 폴더를 사용합니다.
- 기존 로컬 JSON도 sender 실행 시 전송 대상입니다. 수동 저장한 사건은 중복 방지로 재사용됩니다.

## 확인과 제한

자동 테스트에서 이미지·DB 저장, ACK 유실 후 중복 재전송, DB 오류 시 ACK 금지,
연결 중단 시 보존, 잘못된 JPEG 거부를 검증했습니다.
2026-10-26 실제 Docker 브로커·Atlas에서 기존 사건 재전송, 저장 ACK, DB 1건 유지, 증거 조회를 확인했습니다.
신규 사건 최초 저장은 모의 DB 테스트로 검증했으며, 실제 영상 신규 사건과 네트워크 단절 시험은 남아 있습니다.

이 단계는 사건 전송 계약입니다. CAM-01 heartbeat·현재 구역 상태·세션/sequence 순서 판정,
프레임 스트림은 후속 작업입니다. 사건은 과거 기록이므로 늦게 재전송돼도 저장합니다.
ACK는 연결된 브로커를 신뢰하므로 외부 배포 시 토픽별 접근 권한을 구성해야 합니다.
