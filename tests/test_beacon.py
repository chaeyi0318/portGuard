import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock
import mongomock
import pytest
from mqtt.common import now
from agents.beacon import Beacon
from mqtt import worker
from services import commands
from routes import devices
from app import app


@pytest.fixture
def database(monkeypatch):
    database = mongomock.MongoClient(tz_aware=True).test
    for module in (worker, commands, devices):
        monkeypatch.setattr(module, 'db', database)
    return database


def test_command_roundtrip_and_duplicate(database, tmp_path):
    api = app.test_client()
    response = api.post('/vision-api/devices/BEACON-01/commands', json={'action': 'turn_on'})
    assert response.status_code == 202
    command = response.json['command']
    agent = Beacon(path=str(tmp_path / 'agent.sqlite3'))
    agent.connection = Mock()
    packet = SimpleNamespace(payload=json.dumps(command).encode(), retain=False)
    agent.on_message(None, None, packet)
    agent.on_message(None, None, packet)
    assert agent.store.execute('SELECT count(*) FROM commands').fetchone()[0] == 1
    for call in agent.connection.publish.call_args_list:
        worker.receive(call.args[0], call.args[1])
    result = api.get('/vision-api/commands/' + command['commandId']).json['command']
    assert result['status'] == 'succeeded'
    assert [h['status'] for h in result['history']] == ['queued', 'accepted', 'succeeded']
    assert api.get('/vision-api/devices').json['devices'][0]['operationStatus'] == 'on'
    agent.store.close()


def test_timeout_disconnect_and_recovery(database):
    stamp = now()
    command = commands.create_command('BEACON-01', 'turn_off')
    database.commands.update_one({'commandId': command['commandId']}, {'$set': {'deadlineAt': stamp - timedelta(seconds=1)}})
    def message(sequence, session='a', started=None):
        return dict(deviceId='BEACON-01', sessionId=session, sessionStartedAt=(started or stamp).isoformat(),
                    sequence=sequence, sentAt=now().isoformat(), simulated=True, operationStatus='off')
    worker.receive('devices/BEACON-01/heartbeat', json.dumps(message(2)))
    worker.receive('devices/BEACON-01/heartbeat', json.dumps({**message(1), 'operationStatus': 'on'}))
    assert database.devices.find_one()['operationStatus'] == 'off'
    database.devices.update_one({}, {'$set': {'lastSeenAt': stamp-timedelta(seconds=11)}})
    worker.tick(SimpleNamespace(is_connected=lambda: False))
    assert database.commands.find_one()['status'] == 'timed_out'
    assert database.devices.find_one()['connectionStatus'] == 'disconnected'
    worker.receive('devices/BEACON-01/heartbeat', json.dumps(message(3)))
    worker.receive('devices/BEACON-01/heartbeat', json.dumps(message(9, 'old', stamp-timedelta(days=1))))
    assert database.devices.find_one()['connectionStatus'] == 'online'
    assert database.devices.find_one()['sessionId'] == 'a'
    assert [h['status'] for h in database.devices.find_one()['history']] == ['online', 'disconnected', 'online']


@pytest.mark.parametrize('mode,result', [('fail','failed'), ('timeout','timed_out')])
def test_fault_modes(database, tmp_path, mode, result):
    command = commands.create_command('BEACON-01', 'turn_on')
    agent = Beacon(mode=mode, path=str(tmp_path / 'agent.sqlite3'))
    agent.connection = Mock()
    packet = devices.public(command)
    agent.on_message(None, None, SimpleNamespace(payload=json.dumps(packet).encode(), retain=False))
    for call in agent.connection.publish.call_args_list:
        worker.receive(call.args[0], call.args[1])
    if mode == 'timeout':
        assert database.commands.find_one()['status'] == 'accepted'
        database.commands.update_one({}, {'$set': {'deadlineAt': now()-timedelta(seconds=1)}})
        worker.tick(SimpleNamespace(is_connected=lambda: False))
    assert database.commands.find_one()['status'] == result
    assert agent.operation == 'off'
    agent.store.close()


def test_bad_requests(database):
    api = app.test_client()
    assert api.post('/vision-api/devices/BEACON-01/commands', json={'action':'open'}).status_code == 400
    assert api.post('/vision-api/devices/missing/commands', json={'action':'turn_on'}).status_code == 404


@pytest.mark.parametrize('fields', [
    {'commandId': 'test', 'status': 'invalid'},
    {'status': 'accepted'},
    {'commandId': ' ', 'status': 'succeeded'},
    {'commandId': 1, 'status': 'failed'},
])
def test_invalid_ack_does_not_restore_device(database, fields):
    stamp = now().isoformat()
    database.devices.insert_one(dict(deviceId='BEACON-01',
                                    connectionStatus='disconnected', operationStatus='off'))
    previous = database.devices.find_one()
    packet = dict(deviceId='BEACON-01', sessionId='new', sessionStartedAt=stamp,
                  sequence=1, sentAt=stamp, simulated=True, operationStatus='on', **fields)
    with pytest.raises(ValueError):
        worker.receive('devices/BEACON-01/acks', json.dumps(packet))
    assert database.devices.find_one() == previous
    assert database.commands.count_documents({}) == 0
