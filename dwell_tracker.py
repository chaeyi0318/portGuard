class DwellTracker:
    def __init__(self, grace_seconds=0.5, exit_seconds=1.0):
        self.grace_seconds = grace_seconds
        self.exit_seconds = exit_seconds
        self.states = {}
        self.previous_time = None

    def update(self, video_time, observations):
        delta = 0.0

        if self.previous_time is not None:
            delta = video_time - self.previous_time

            if delta < 0:
                raise ValueError("영상 시각이 역순입니다.")

        self.previous_time = video_time
        durations = {}

        for track_id, state in self.states.items():
            missing_time = video_time - state["last_seen"]

            if missing_time > self.grace_seconds:
                # 오래된 관측으로 체류·퇴장을 이어 계산하지 않음
                state["dwell"] = 0.0
                state["outside"] = 0.0
                state["seen_previous_frame"] = False

        for track_id, inside in observations.items():
            state = self.states.get(track_id)

            if state is None:
                state = {
                    "dwell": 0.0,
                    "outside": 0.0,
                    "last_seen": video_time,
                    "inside": None,
                    "seen_previous_frame": False,
                }
                self.states[track_id] = state

            consecutive = state["seen_previous_frame"]

            if inside:
                # 내부로 돌아오면 퇴장 확인 시간 초기화
                state["outside"] = 0.0

                if consecutive and state["inside"] is True:
                    state["dwell"] += delta

            else:
                # 밖에서 연속으로 관측된 구간만 누적
                if consecutive and state["inside"] is False:
                    state["outside"] += delta

                if state["outside"] >= self.exit_seconds:
                    state["dwell"] = 0.0

            state["inside"] = inside
            state["last_seen"] = video_time
            durations[track_id] = state["dwell"]

        for track_id, state in self.states.items():
            if track_id not in observations:
                # 누락은 퇴장 증거가 아님
                state["outside"] = 0.0

            state["seen_previous_frame"] = track_id in observations

        # 장기간 사라진 추적 기록 정리
        for track_id in list(self.states):
            state = self.states[track_id]

            if video_time - state["last_seen"] > 60:
                del self.states[track_id]

        return durations