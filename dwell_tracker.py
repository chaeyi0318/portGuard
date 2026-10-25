class DwellTracker:
    def __init__(self, grace_seconds=0.5):
        self.grace_seconds = grace_seconds
        self.states = {}
        self.previous_time = None

    def update(self, video_time, observations):
        """
        observations: 이번 프레임의 {추적 ID: ROI 안팎 여부}
        반환값: 이번 프레임에 관측된 ID별 체류 시간
        """
        delta = 0.0

        if self.previous_time is not None:
            delta = video_time - self.previous_time

            if delta < 0:
                raise ValueError("영상 시각이 역순입니다.")

        self.previous_time = video_time

        # 유예 시간을 넘긴 기록 제거
        for track_id in list(self.states):
            state = self.states[track_id]

            if video_time - state["last_seen"] > self.grace_seconds:
                del self.states[track_id]

        durations = {}

        for track_id, inside in observations.items():
            state = self.states.get(track_id)

            if state is None:
                state = {
                    "dwell": 0.0,
                    "last_seen": video_time,
                    "inside": False,
                    "seen_previous_frame": False,
                }
                self.states[track_id] = state

            if not inside:
                state["dwell"] = 0.0
            elif state["inside"] and state["seen_previous_frame"]:
                state["dwell"] += delta

            state["inside"] = inside
            state["last_seen"] = video_time
            durations[track_id] = state["dwell"]

        for track_id, state in self.states.items():
            state["seen_previous_frame"] = track_id in observations

        return durations