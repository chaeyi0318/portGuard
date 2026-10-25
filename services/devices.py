"""Device metadata. CAM-01 contracts are deliberately separate."""
import json
from pathlib import Path
from datetime import datetime, timezone

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/devices.json').read_text())
DEVICES = {item['deviceId']: item for item in CONFIG['devices']}


def utc(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(timezone.utc)


def validate_message(data, device_id):
    if not isinstance(data, dict) or data.get('deviceId') != device_id or data.get('simulated') is not True:
        raise ValueError('Invalid device envelope')
    if not isinstance(data.get('sessionId'), str) or not data['sessionId']:
        raise ValueError('Invalid session')
    if type(data.get('sequence')) is not int or data['sequence'] < 1:
        raise ValueError('Invalid sequence')
    utc(data['sessionStartedAt'])
    utc(data['sentAt'])


def newer(previous, message):
    if not previous or not previous.get('sessionId'):
        return True
    if previous['sessionId'] == message['sessionId']:
        return message['sequence'] > previous['sequence']
    return utc(message['sessionStartedAt']) > utc(previous['sessionStartedAt'])
