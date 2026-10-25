from db import client, db

try:
    incidents = db["incidents"]

    incidents.create_index(
        "eventId",
        unique=True,
        name="uq_incidents_event_id",
    )

    print("incidents 컬렉션과 eventId 유니크 인덱스 준비 완료")

    rois = db["rois"]

    rois.create_index(
        "roiId",
        unique=True,
        name="uq_rois_roi_id",
    )

    print("rois 컬렉션과 roiId 유일 인덱스 준비 완료!")
finally:
    client.close()