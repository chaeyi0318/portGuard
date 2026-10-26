"""CAM-01 event transport. Application ACK means JPEG and MongoDB are saved."""
import base64
import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

from evidence import EVIDENCE_DIR
from services.incident_input import validate_incident_input
from services.incidents import save_incident

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_PACKET_BYTES = 3 * 1024 * 1024


def receive_event(payload, connection):
    if len(payload) > MAX_PACKET_BYTES:
        raise ValueError("사건 메시지가 너무 큽니다.")
    packet = json.loads(payload)
    event = validate_incident_input(packet['event'])
    if event['deviceId'] != 'CAM-01':
        raise ValueError("지원하지 않는 카메라입니다.")
    image = base64.b64decode(packet['imageBase64'], validate=True)
    if not image.startswith(b'\xff\xd8\xff') or len(image) > MAX_IMAGE_BYTES:
        raise ValueError("JPEG 형식 또는 크기를 확인하세요.")
    if cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR) is None:
        raise ValueError("JPEG를 읽을 수 없습니다.")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    target = EVIDENCE_DIR / event['evidence']['fileName']
    # Publish a complete file atomically, without overwriting existing evidence.
    with tempfile.NamedTemporaryFile(dir=EVIDENCE_DIR, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(image)
            file.flush()
            os.fsync(file.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.is_symlink() or target.read_bytes() != image:
                    raise ValueError("기존 증거 이미지와 내용이 다릅니다.")
        finally:
            temporary.unlink()
    incident, created = save_incident(event)

    if created:
        connection.publish(
            "portguard/internal/incidents/created",
            json.dumps({
                "eventId": incident["eventId"],
            }),
            qos=1,
            retain=False,
        )
        
    # Only a successful DB operation (including a known duplicate) permits ACK.
    connection.publish('devices/CAM-01/acks', json.dumps({
        'deviceId': 'CAM-01', 'eventId': incident['eventId'],
        'status': 'stored',
    }), qos=1, retain=False)
    return created
