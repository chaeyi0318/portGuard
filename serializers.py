from datetime import datetime

def serialize_incident(incident):
    result = dict(incident)
    result.pop("_id", None)

    for field in ("occurredAt", "capturedAt", "receivedAt", "updatedAt"):
        value = result.get(field)

        if isinstance(value, datetime):
            result[field] = value.isoformat()

    history = []

    for change in result.get("history", []):
        item = dict(change)
        value = item.get("changedAt")

        if isinstance(value, datetime):
            item["changedAt"] = value.isoformat()

        history.append(item)

    result["history"] = history

    return result

def serialize_roi(roi):
    result = dict(roi)
    result.pop("_id", None)

    for field in ("createdAt", "updatedAt"):
        value = result.get(field)

        if isinstance(value, datetime):
            result[field] = value.isoformat()

    return result