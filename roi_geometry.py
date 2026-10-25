from shapely.geometry import Point, Polygon

def get_foot_point(box):
    x1, y1, x2, y2 = box

    return ((x1 + x2) / 2, y2)


def is_foot_inside_roi(box, points, frame_width, frame_height):
    foot_x, foot_y = get_foot_point(box)

    normalized_point = Point(
        foot_x / frame_width,
        foot_y / frame_height,
    )

    return Polygon(points).covers(normalized_point)