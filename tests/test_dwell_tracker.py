from dwell_tracker import DwellTracker

def observe(tracker, start, end, inside):
    events = []

    # 0.25초 간격으로 같은 사람(ID 1)을 관측 
    for step in range(start, end + 1):
        tracker.update(step * 0.25, {1: inside})
        events.extend(tracker.new_events)

    return events

def test_short_entry_has_no_event():
    tracker = DwellTracker()

    # 0~1.75초 진입 후 퇴장
    events = observe(tracker, 0, 7, True)
    events += observe(tracker, 8, 12, False)

    assert events == []


def test_continuous_dwell_emits_once():
    tracker = DwellTracker()

    # 0~5초 동안 계속 체류
    events = observe(tracker, 0, 20, True)

    assert len(events) == 1
    assert events[0]["videoTime"] == 2.0
    assert events[0]["dwellSeconds"] == 2.0


def test_reentry_emits_new_event():
    tracker = DwellTracker()

    # 0~2.75초: 첫 체류 사건
    first = observe(tracker, 0, 11, True)

    # 3~4초: 밖에서 1초 관측하여 퇴장 확정
    outside = observe(tracker, 12, 16, False)

    # 4.25~6.25초: 재진입 후 다시 2초 체류
    second = observe(tracker, 17, 25, True)

    assert len(first) == 1
    assert outside == []
    assert len(second) == 1
    assert second[0]["videoTime"] == 6.25
    assert second[0]["dwellSeconds"] == 2.0

def test_short_missing_preserves_dwell_without_adding_time():
    tracker = DwellTracker()

    observe(tracker, 0, 4, True)  # 체류 1초

    tracker.update(1.25, {})  # 검출 누락
    durations = tracker.update(1.5, {1: True})

    # 기존 체류는 보존하고, 누락 구간은 더하지 않음
    assert durations[1] == 1.0
    assert tracker.new_events == []

    events = observe(tracker, 7, 10, True)  # 1.75~2.5초

    assert len(events) == 1
    assert events[0]["videoTime"] == 2.5


def test_long_missing_resets_dwell():
    tracker = DwellTracker()

    observe(tracker, 0, 4, True)  # 체류 1초

    tracker.update(1.25, {})
    tracker.update(1.5, {})
    tracker.update(1.75, {})  # 유예 0.5초 초과

    durations = tracker.update(2.0, {1: True})

    assert durations[1] == 0.0
    assert tracker.new_events == []

    events = observe(tracker, 9, 16, True)  # 2.25~4초

    assert len(events) == 1
    assert events[0]["videoTime"] == 4.0


def test_missing_does_not_rearm_existing_event():
    tracker = DwellTracker()

    first = observe(tracker, 0, 8, True)
    assert len(first) == 1

    tracker.update(2.25, {})
    tracker.update(2.5, {})
    tracker.update(2.75, {})

    # 누락은 확인된 퇴장이 아니므로 새 사건을 만들지 않음
    events = observe(tracker, 12, 24, True)
    assert events == []


def test_paused_video_time_does_not_add_dwell():
    tracker = DwellTracker()
    observe(tracker, 0, 4, True)  # 체류 1초

    # 영상 시각이 멈춰 있으면 호출을 반복해도 누적하지 않음
    for _ in range(10):
        durations = tracker.update(1.0, {1: True})
        assert durations[1] == 1.0
        assert tracker.new_events == []

    events = observe(tracker, 5, 8, True)

    assert len(events) == 1
    assert events[0]["videoTime"] == 2.0


def test_large_observation_gap_resets_dwell():
    tracker = DwellTracker()
    observe(tracker, 0, 4, True)  # 체류 1초

    # 관측 없이 시각이 크게 뛰어도 그 시간을 체류로 더하지 않음
    durations = tracker.update(10.0, {1: True})

    assert durations[1] == 0.0
    assert tracker.new_events == []

    events = observe(tracker, 41, 48, True)  # 10.25~12초

    assert len(events) == 1
    assert events[0]["videoTime"] == 12.0