"""One worker per deployment: python -m mqtt.worker."""
import json
import logging
import queue
import time
from datetime import timedelta
from pymongo import ReturnDocument
from db import db
from mqtt.common import client, connect, now
from services.devices import CONFIG, DEVICES, newer, utc, validate_message
from mqtt.vision import receive_event

LOG = logging.getLogger(__name__)


def receive(topic, payload):
    parts = topic.split('/')
    if len(parts) != 3 or parts[0] != 'devices' or parts[1] not in DEVICES:
        return
    device_id, kind = parts[1:]
    if kind not in ('heartbeat', 'status', 'acks'):
        return
    data = json.loads(payload)
    validate_message(data, device_id)
    if kind == 'acks':
        if data.get('status') not in ('accepted', 'succeeded', 'failed'):
            raise ValueError('Invalid command result')
        if not isinstance(data.get('commandId'), str) or not data['commandId'].strip():
            raise ValueError('Invalid command ID')
    # Retained/replayed packets cannot prove a fresh connection.
    age = (now() - utc(data['sentAt'])).total_seconds()
    if age < -5 or age > CONFIG['disconnectSeconds']:
        return
    previous = db.devices.find_one({'deviceId': device_id})
    if not newer(previous, data):
        return
    operation = data.get('operationStatus')
    if operation not in ('on', 'off', 'error'):
        raise ValueError('Invalid operation status')
    stamp = now()
    fields = {key: data[key] for key in ('sessionId', 'sessionStartedAt', 'sequence')}
    fields.update(lastSeenAt=stamp, observedAt=utc(data['sentAt']),
                  connectionStatus='online', operationStatus=operation, simulated=True)
    update = {'$set': fields}
    if not previous or previous.get('connectionStatus') != 'online':
        update['$push'] = {'history': {'$each': [{'status': 'online', 'at': stamp}], '$slice': -1000}}
    # A single worker owns device ordering. Do not run several copies.
    db.devices.update_one({'deviceId': device_id}, update, upsert=True)
    if kind == 'acks':
        status = data.get('status')
        allowed = ['queued', 'sent'] if status == 'accepted' else ['queued', 'sent', 'accepted']
        db.commands.update_one(
            {'commandId': data.get('commandId'), 'deviceId': device_id,
             'status': {'$in': allowed}, 'deadlineAt': {'$gt': stamp}},
            {'$set': {'status': status, 'updatedAt': stamp},
             '$push': {'history': {'status': status, 'at': stamp}}})


def tick(connection):
    stamp = now()
    for device_id in DEVICES:
        db.devices.update_one(
            {'deviceId': device_id, 'connectionStatus': 'online',
             'lastSeenAt': {'$lt': stamp - timedelta(seconds=CONFIG['disconnectSeconds'])}},
            {'$set': {'connectionStatus': 'disconnected'},
             '$push': {'history': {'$each': [{'status': 'disconnected', 'at': stamp}], '$slice': -1000}}})
    db.commands.update_many(
        {'status': {'$in': ['queued', 'sent', 'accepted']}, 'deadlineAt': {'$lte': stamp}},
        {'$set': {'status': 'timed_out', 'updatedAt': stamp},
         '$push': {'history': {'status': 'timed_out', 'at': stamp}}})
    if not connection.is_connected():
        return
    # Retry pending delivery; the agent deduplicates by commandId.
    for command in db.commands.find({'status': {'$in': ['queued', 'sent', 'accepted']},
                                     'deadlineAt': {'$gt': stamp}}).limit(100):
        if command.get('lastSentAt') and (stamp - command['lastSentAt']).total_seconds() < 2:
            continue
        packet = {key: command[key] for key in ('commandId', 'deviceId', 'action', 'simulated')}
        packet.update(requestedAt=command['requestedAt'].isoformat(), deadlineAt=command['deadlineAt'].isoformat())
        info = connection.publish(f"devices/{command['deviceId']}/commands", json.dumps(packet), qos=1, retain=False)
        if info.rc == 0:
            db.commands.update_one({'commandId': command['commandId']}, {'$set': {'lastSentAt': stamp}})
            db.commands.update_one({'commandId': command['commandId'], 'status': 'queued'},
                                  {'$set': {'status': 'sent'}, '$push': {'history': {'status': 'sent', 'at': stamp}}})


def main():
    logging.basicConfig(level=logging.INFO)
    db.devices.create_index('deviceId', unique=True)
    db.commands.create_index('commandId', unique=True)
    db.incidents.create_index('eventId', unique=True, name='uq_incidents_event_id')
    inbox = queue.Queue(maxsize=1000)
    connection = client('portguard-device-worker')

    def on_connect(c, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            c.subscribe('devices/CAM-01/events', qos=1)
            for device_id in DEVICES:
                for kind in ('heartbeat', 'status', 'acks'):
                    c.subscribe(f'devices/{device_id}/{kind}', qos=1)

    def on_message(c, userdata, message):
        try:
            if not message.retain:
                inbox.put_nowait((message.topic, message.payload))
        except queue.Full:
            LOG.error('Device inbox full; awaiting next heartbeat/result retry')

    connection.on_connect = on_connect
    connection.on_message = on_message
    connect(connection)
    try:
        while True:
            try:
                topic, payload = inbox.get(timeout=0.2)
                if topic == 'devices/CAM-01/events':
                    receive_event(payload, connection)
                else:
                    receive(topic, payload)
            except queue.Empty:
                pass
            except Exception:
                LOG.exception('Device message failed')
            try:
                tick(connection)
            except Exception:
                LOG.exception('Device worker tick failed')
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        connection.disconnect()
        connection.loop_stop()


if __name__ == '__main__':
    main()
