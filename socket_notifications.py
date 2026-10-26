import json
import logging
from collections import OrderedDict

from db import db
from mqtt.common import client, connect
from serializers import serialize_incident
from socket_server import socketio


LOG = logging.getLogger(__name__)
TOPIC = "portguard/internal/incidents/created"


def start_notifications(app):
    connection = client("portguard-flask-notifications")
    delivered = OrderedDict()

    def on_connect(c, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            c.subscribe(TOPIC, qos=1)

    def on_message(c, userdata, message):
        if message.topic != TOPIC or message.retain:
            return

        try:
            data = json.loads(message.payload)
            event_id = data["eventId"]

            if not isinstance(event_id, str):
                raise ValueError("eventId는 문자열이어야 합니다.")

            # MQTT QoS 1에서 같은 알림이 다시 올 수 있음
            if event_id in delivered:
                return

            incident = db["incidents"].find_one(
                {"eventId": event_id},
                {"_id": 0},
            )

            if incident is None:
                return

            with app.app_context():
                socketio.emit(
                    "incident.created",
                    {"incident": serialize_incident(incident)},
                )

            delivered[event_id] = None

            # 최근 1,000건의 중복 알림 방지
            if len(delivered) > 1000:
                delivered.popitem(last=False)

        except Exception:
            LOG.exception("사건 생성 알림 전달 실패")

    connection.on_connect = on_connect
    connection.on_message = on_message
    connect(connection)

    return connection