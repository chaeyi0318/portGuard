"""Run alongside the analyzer: python -m mqtt.vision_sender.

Local JSON + JPEG records are a durable outbox; .acked markers suppress retries.
"""
import base64
import json
import logging
import threading
from uuid import UUID

from evidence import EVIDENCE_DIR
from mqtt.common import client, connect
from services.incident_input import validate_incident_input

LOG = logging.getLogger(__name__)


def send_pending(connection, directory=EVIDENCE_DIR):
    if not connection.is_connected():
        return
    for record in sorted(directory.glob('*.json')):
        if record.with_suffix('.acked').exists():
            continue
        try:
            event = json.loads(record.read_text(encoding='utf-8'))
            validate_incident_input(event)
            if event['eventId'] != record.stem or event['deviceId'] != 'CAM-01':
                raise ValueError('사건 파일명 또는 카메라 불일치')
            image = record.with_suffix('.jpg').read_bytes()
            if len(image) > 2 * 1024 * 1024:
                raise ValueError('증거 이미지는 2 MiB 이하여야 합니다.')
            connection.publish('devices/CAM-01/events', json.dumps({
                'event': event, 'imageBase64': base64.b64encode(image).decode('ascii'),
            }), qos=1, retain=False)
        except Exception:
            LOG.exception('사건 전송 준비 실패: %s', record.name)


def acknowledge(payload, directory=EVIDENCE_DIR):
    data = json.loads(payload)
    event_id = data.get('eventId')
    if data.get('deviceId') != 'CAM-01' or data.get('status') != 'stored':
        return
    if not isinstance(event_id, str) or str(UUID(event_id)) != event_id:
        raise ValueError('잘못된 ACK 사건 ID')
    record = directory / f'{event_id}.json'
    if record.is_file():
        record.with_suffix('.acked').touch()


def main():
    logging.basicConfig(level=logging.INFO)
    connection = client('portguard-vision-outbox')

    def on_connect(c, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            c.subscribe('devices/CAM-01/acks', qos=1)

    def on_message(c, userdata, message):
        try:
            if message.topic == 'devices/CAM-01/acks' and not message.retain:
                acknowledge(message.payload)
        except Exception:
            LOG.exception('사건 ACK 처리 실패')

    connection.on_connect = on_connect
    connection.on_message = on_message
    connect(connection)
    try:
        while True:
            send_pending(connection)
            threading.Event().wait(3)
    except KeyboardInterrupt:
        pass
    finally:
        connection.disconnect()
        connection.loop_stop()


if __name__ == '__main__':
    main()
