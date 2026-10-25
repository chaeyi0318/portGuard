from services.rois import validate_roi


cases = {
    "정상 사각형": [
        [0.1, 0.1], [0.8, 0.1], [0.8, 0.8], [0.1, 0.8]
    ],
    "범위 초과": [
        [0.1, 0.1], [1.2, 0.1], [0.8, 0.8]
    ],
    "중복 꼭짓점": [
        [0.1, 0.1], [0.8, 0.1], [0.1, 0.1]
    ],
    "일직선": [
        [0.1, 0.1], [0.5, 0.5], [0.9, 0.9]
    ],
    "변 교차": [
        [0.1, 0.1], [0.8, 0.7], [0.1, 0.8], [0.7, 0.1]
    ],
}

for name, points in cases.items():
    error = validate_roi({
        "deviceId": "CAM-01",
        "roiId": "ROI-CAM01-01",
        "points": points,
    })

    print(name, "→", error if error else "검증 통과")