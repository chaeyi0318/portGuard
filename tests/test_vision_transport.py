import json
from unittest.mock import Mock
from uuid import uuid4

import cv2
import mongomock
import numpy as np
import pytest

from mqtt import vision, vision_sender
from services import incidents


@pytest.fixture
def transport(monkeypatch, tmp_path):
    sender, server = tmp_path / 'sender', tmp_path / 'server'
    sender.mkdir()
    database = mongomock.MongoClient(tz_aware=True).test
    database.incidents.create_index('eventId', unique=True)
    monkeypatch.setattr(incidents, 'db', database)
    monkeypatch.setattr(vision, 'EVIDENCE_DIR', server)
    event_id = str(uuid4())
    stamp = '2026-10-26T00:00:00+00:00'
    event = dict(eventId=event_id, deviceId='CAM-01', roiId='ROI-CAM01-01',
                 roiVersion=1, trackId=1, sessionId=str(uuid4()), sessionStartedAt=stamp,
                 eventType='intrusion', source='recorded_video', occurredAt=stamp,
                 capturedAt=stamp, videoTimeSeconds=2, dwellSeconds=2,
                 evidence=dict(fileName=f'{event_id}.jpg', contentType='image/jpeg'))
    (sender / f'{event_id}.json').write_text(json.dumps(event))
    _, image = cv2.imencode('.jpg', np.zeros((10, 10, 3), dtype=np.uint8))
    (sender / f'{event_id}.jpg').write_bytes(image.tobytes())
    connection = Mock()
    connection.is_connected.return_value = True
    return sender, server, database, connection, event_id


def test_retry_duplicate_and_durable_ack(transport):
    sender, server, database, connection, event_id = transport
    vision_sender.send_pending(connection, sender)
    payload = connection.publish.call_args.args[1]
    assert vision.receive_event(payload, connection) is True
    # Lost application ACK: retry must not create a second incident.
    assert vision.receive_event(payload, connection) is False
    assert database.incidents.count_documents({}) == 1
    assert (server / f'{event_id}.jpg').read_bytes() == (sender / f'{event_id}.jpg').read_bytes()
    vision_sender.acknowledge(connection.publish.call_args.args[1], sender)
    connection.reset_mock()
    vision_sender.send_pending(connection, sender)
    connection.publish.assert_not_called()
    assert (sender / f'{event_id}.json').exists()


def test_database_failure_does_not_ack_and_can_retry(transport, monkeypatch):
    sender, _, _, connection, _ = transport
    vision_sender.send_pending(connection, sender)
    payload = connection.publish.call_args.args[1]
    original = vision.save_incident
    monkeypatch.setattr(vision, 'save_incident', Mock(side_effect=RuntimeError('offline')))
    connection.reset_mock()
    with pytest.raises(RuntimeError):
        vision.receive_event(payload, connection)
    connection.publish.assert_not_called()
    monkeypatch.setattr(vision, 'save_incident', original)
    assert vision.receive_event(payload, connection) is True


def test_bad_image_never_saves_or_acks(transport):
    sender, _, database, connection, _ = transport
    vision_sender.send_pending(connection, sender)
    packet = json.loads(connection.publish.call_args.args[1])
    packet['imageBase64'] = 'bm90LWEtanBlZw=='
    connection.reset_mock()
    with pytest.raises(ValueError):
        vision.receive_event(json.dumps(packet), connection)
    assert database.incidents.count_documents({}) == 0
    connection.publish.assert_not_called()


def test_disconnect_keeps_pending_record(transport):
    sender, _, _, connection, event_id = transport
    connection.is_connected.return_value = False
    vision_sender.send_pending(connection, sender)
    connection.publish.assert_not_called()
    assert not (sender / f'{event_id}.acked').exists()
