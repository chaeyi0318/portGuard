class DwellTracker:
    def __init__(
        self,
        grace_seconds=0.5,
        exit_seconds=1.0,
        dwell_seconds=2.0,
    ):
        self.grace_seconds = grace_seconds
        self.exit_seconds = exit_seconds
        self.dwell_seconds = dwell_seconds

        self.states = {}
        self.previous_time = None

        # 이번 프레임에 새로 발생한 사건
        self.new_events = []

    def update(self, video_time, observations):
        self.new_events = []
        delta = 0.0

        if self.previous_time is not None:
            delta = video_time - self.previous_time

            if delta < 0:
                raise ValueError("영상 시각이 역순입니다.")

        self.previous_time = video_time
        durations = {}

        for state in self.states.values():
            if video_time - state["last_seen"] > self.grace_seconds:
                state["dwell"] = 0.0
                state["outside"] = 0.0
                state["seen_previous_frame"] = False

                # 누락만으로 사건 발생 기록을 해제하지 않음

        for track_id, inside in observations.items():
            state = self.states.get(track_id)

            if state is None:
                state = {
                    "dwell": 0.0,
                    "outside": 0.0,
                    "last_seen": video_time,
                    "inside": None,
                    "seen_previous_frame": False,
                    "event_emitted": False,
                }
                self.states[track_id] = state

            consecutive = state["seen_previous_frame"]

            if inside:
                state["outside"] = 0.0

                if consecutive and state["inside"] is True:
                    state["dwell"] += delta

                if (
                    state["dwell"] >= self.dwell_seconds
                    and not state["event_emitted"]
                ):
                    state["event_emitted"] = True

                    self.new_events.append({
                        "trackId": track_id,
                        "videoTime": video_time,
                        "dwellSeconds": state["dwell"],
                    })

            else:
                if consecutive and state["inside"] is False:
                    state["outside"] += delta

                if state["outside"] >= self.exit_seconds:
                    state["dwell"] = 0.0
                    state["event_emitted"] = False

            state["inside"] = inside
            state["last_seen"] = video_time
            durations[track_id] = state["dwell"]

        for track_id, state in self.states.items():
            if track_id not in observations:
                state["outside"] = 0.0

            state["seen_previous_frame"] = track_id in observations

        return durations