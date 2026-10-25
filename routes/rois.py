from flask import Blueprint, request

from services.rois import create_roi
from services.rois import create_roi, get_roi
from serializers import serialize_roi

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

    return {"roi": serialize_roi(roi)}, status_code

@rois_bp.get("/<roi_id>")
def get_roi_detail(roi_id):
    roi = get_roi(roi_id)

    if roi is None:
        return {"error": "위험구역을 찾을 수 없습니다."}, 404

    return {"roi": serialize_roi(roi)}