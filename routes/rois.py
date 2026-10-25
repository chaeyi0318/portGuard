from flask import Blueprint, request

from services.rois import create_roi


rois_bp = Blueprint(
    "rois",
    __name__,
    url_prefix="/vision-api/rois",
)


@rois_bp.post("")
def post_roi():
    if not request.is_json:
        return {"error": "JSON 형식으로 요청해 주세요."}, 400

    data = request.get_json(silent=True)

    roi, status_code, error = create_roi(data)

    if error is not None:
        return {"error": error}, status_code

    result = dict(roi)
    result["createdAt"] = result["createdAt"].isoformat()
    result["updatedAt"] = result["updatedAt"].isoformat()

    return {"roi": result}, status_code