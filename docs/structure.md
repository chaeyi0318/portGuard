# 폴더 구조와 역할

2026-10-25 실제 파일 기준입니다. 이번 문서 정리에서는 코드 파일을 이동하지 않았습니다.

```text
portGuard/
├── README.md                  # 프로젝트 시작 문서
├── app.py                     # Flask 앱·Blueprint·DB 오류 응답
├── db.py                      # 서버 MongoDB 연결
├── settings.py                # 카메라 JSON 읽기
├── serializers.py             # 사건·ROI 응답 날짜 변환
├── detect_people.py           # 영상 분석 실행, ROI 조회, 추적·표시·사건 신호
├── preview_video.py           # 영상 재생만 확인
├── roi_geometry.py            # 발밑 점·다각형 안팎 계산
├── dwell_tracker.py           # ID별 체류·누락 유예·퇴장·사건 신호
├── init_db.py                 # 사건·ROI 유일 인덱스 생성
├── check_db.py                # DB ping
├── check_roi.py               # ROI 검증 입력 예제
├── check_incident_save.py     # 실제 DB 사건 저장·중복 확인
├── seed_incident.py           # 초기 합성 시험 사건 입력
├── routes/
│   ├── __init__.py
│   ├── incidents.py           # 사건 조회·처리 HTTP API
│   ├── rois.py                # ROI 생성·조회 HTTP API
│   └── devices.py             # 가상 장비·명령·이력 HTTP API
├── services/
│   ├── __init__.py
│   ├── incidents.py           # 사건 저장·상태 전이·버전 검사
│   ├── rois.py                # ROI 검증·저장·조회
│   ├── devices.py             # 가상 장비 설정·메시지 검증·순서 판정
│   └── commands.py            # 가상 장비 명령 생성
├── mqtt/
│   ├── common.py              # MQTT 접속 공통 함수
│   └── worker.py              # 가상 경광등 수신·명령 전달·시간 초과
├── agents/
│   └── beacon.py              # 독립 가상 경광등 에이전트
├── config/
│   ├── camera.json            # CAM-01·영상 경로·임계값
│   ├── bytetrack.yaml         # 사람 추적 설정
│   ├── devices.json           # 가상 장비·시간 기준
│   └── mosquitto.conf         # 개발용 브로커 설정
├── tests/
│   └── test_beacon.py         # 가상 장비 자동 테스트
├── docs/                      # 실행·진행·구조·검증·출처·경광등 문서
├── compose.beacon.yaml        # 개발용 MQTT 브로커만 실행
├── requirements.txt           # 현재 패키지 버전 목록
├── requirements-dev.txt       # 테스트 설치용 목록
├── .env.example               # 공유 가능한 설정 예제
├── .gitignore
├── .env                       # 로컬 비밀 설정, Git 제외
├── .venv/                     # 로컬 Python 환경, Git 제외
└── data/                      # 영상·로컬 장비 SQLite 등, Git 제외
    └── videos/
        └── Browse2.mpg
```

YOLO `.pt` 모델과 캐시 등 로컬 생성 파일은 위 구조에서 생략했습니다.
실제 제외 여부는 `.gitignore`와 `git status`로 확인합니다.

## 책임 경계

- routes는 HTTP 입력·응답, services는 DB와 업무 규칙을 담당합니다.
- 영상 분석은 `detect_people.py`와 기하·체류 모듈에서 수행합니다.
- 현재 분석기의 사건 출력과 `services/incidents.py` 저장 함수는 아직 연결되지 않았습니다.
- MQTT worker와 beacon 에이전트는 현재 가상 경광등 범위입니다. CAM-01 통신은 별도 구현 예정입니다.
- 지도 시설·UI·프록시·최종 배포는 QuayPilot 측 담당입니다.
