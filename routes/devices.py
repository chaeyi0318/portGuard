from datetime import datetime
from flask import Blueprint, request
from db import db
from services.devices import DEVICES
from services.commands import create_command


devices_bp = Blueprint('devices', __name__, url_prefix='/vision-api')


def public(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k != '_id'}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value


@devices_bp.get('/devices')
def devices():
    result = []
    for device_id, meta in DEVICES.items():
        state = db.devices.find_one({'deviceId': device_id}, {'_id': 0}) or {}
        result.append({**meta, 'connectionStatus': 'checking', 'operationStatus': 'unknown', **state})
    return public({'devices': result})


@devices_bp.post('/devices/<device_id>/commands')
def commands(device_id):
    if device_id not in DEVICES:
        return {'error': '장비를 찾을 수 없습니다'}, 404

    allowed_actions = {
        'beacon': ('turn_on', 'turn_off'),
        'gate': ('open', 'close'),
    }

    device_type = DEVICES[device_id]['type']
    actions = allowed_actions.get(device_type, ())

    data = request.get_json(silent=True)
    
    if not isinstance(data, dict) or data.get('action') not in actions:
        return {
            'error': f"action은 {', '.join(actions)} 중 하나여야 합니다"
        }, 400
    
    return public({'command': create_command(device_id, data['action'])}), 202


@devices_bp.get('/commands/<command_id>')
def command(command_id):
    item = db.commands.find_one({'commandId': command_id}, {'_id': 0})
    if item is None:
        return {'error': '명령을 찾을 수 없습니다'}, 404
    return public({'command': item})


@devices_bp.get('/devices/<device_id>/history')
def history(device_id):
    if device_id not in DEVICES:
        return {'error': '장비를 찾을 수 없습니다'}, 404
    state = db.devices.find_one({'deviceId': device_id}, {'_id': 0, 'history': 1}) or {}
    return public({'history': state.get('history', [])[-100:]})
