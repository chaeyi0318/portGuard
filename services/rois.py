import math
from shapely.geometry import Polygon

def validate_roi(data):
    if not isinstance(data, dict):
        return "JSON 객체를 보내 주세요"

    for field in ("deviceId", "roiId"):
        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            return f"{field}는 비어 있지 않은 문자열이어야 합니다"

    points = data.get("points")

    if not isinstance(points, list) or not 3 <= len(points) <= 32:
        return "points는 꼭짓점 3~32개로 구성해야 합니다"

    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            return "각 꼭짓점은 [x, y] 형식이어야 합니다"

        for value in point:
            if type(value) not in (int, float):
                return "좌표는 숫자여야 합니다."

            if not math.isfinite(value) or not 0 <= value <= 1:
                return "좌표는 0~1 범위의 유한한 숫자여야 합니다"

        unique_points = {tuple(point) for point in points}

    if len(unique_points) != len(points):
        return "중복된 꼭짓점은 사용할 수 없습니다."

    polygon = Polygon(points)

    if polygon.area <= 0:
        return "위험구역은 면적이 있어야 합니다."

    if not polygon.is_valid:
        return "다각형이 유효하지 않습니다. 변이 서로 교차하는지 확인해 주세요."

    return None