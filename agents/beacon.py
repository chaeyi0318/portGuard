"""Run: python -m agents.beacon [--mode normal|fail|timeout]."""
import argparse
import json
import sqlite3
import threading
import time
from pathlib import Path
from uuid import uuid4
from mqtt.common import client, connect, now


class Beacon:
    def __init__(self, mode='normal', path='data/beacon.sqlite3'):
        self.mode = mode
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.store = sqlite3.connect(path, check_same_thread=False)
        self.store.execute('CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, action TEXT, result TEXT)')
        self.store.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, value TEXT)')
        row = self.store.execute('SELECT value FROM state WHERE id=1').fetchone()
        self.operation = row[0] if row else 'off'
        self.lock = threading.RLock()
        self.session = str(uuid4())
        self.started = now().isoformat()
        self.sequence = 0
        self.connection = client('portguard-BEACON-01')
        self.connection.on_connect = self.on_connect
        self.connection.on_message = self.on_message

    def publish(self, topic, **fields):
        with self.lock:
            self.sequence += 1
            data = dict(deviceId='BEACON-01', sessionId=self.session,
                        sessionStartedAt=self.started, sequence=self.sequence,
                        sentAt=now().isoformat(), simulated=True, **fields)
            self.connection.publish('devices/BEACON-01/' + topic, json.dumps(data), qos=1)

    def on_connect(self, connection, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return
        connection.subscribe('devices/BEACON-01/commands', qos=1)
        self.publish('status', operationStatus=self.operation)

    def on_message(self, connection, userdata, message):
        try:
            data = json.loads(message.payload)
            command_id, action = data['commandId'], data['action']
            if (message.retain or data.get('deviceId') != 'BEACON-01'
                    or data.get('simulated') is not True or action not in ('turn_on', 'turn_off')
                    or not isinstance(command_id, str) or not command_id):
                return
            from services.devices import utc
            if utc(data['deadlineAt']) <= now():
                return
            with self.lock:
                row = self.store.execute('SELECT action,result FROM commands WHERE id=?', (command_id,)).fetchone()
                if row and row[0] != action:
                    return
                if row:
                    result = row[1]
                else:
                    result = 'failed' if self.mode == 'fail' else 'succeeded'
                    if self.mode == 'timeout':
                        result = 'accepted'
                    if result == 'succeeded':
                        self.operation = 'on' if action == 'turn_on' else 'off'
                        self.store.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (self.operation,))
                    self.store.execute('INSERT INTO commands VALUES (?,?,?)', (command_id, action, result))
                    self.store.commit()
                self.publish('acks', commandId=command_id, status='accepted', operationStatus=self.operation)
                if result != 'accepted':
                    self.publish('acks', commandId=command_id, status=result,
                                 operationStatus=self.operation)
        except (ValueError, KeyError, TypeError):
            return

    def run(self):
        connect(self.connection)
        try:
            while True:
                if self.connection.is_connected():
                    self.publish('heartbeat', operationStatus=self.operation)
                time.sleep(3)
        except KeyboardInterrupt:
            pass
        finally:
            self.connection.disconnect()
            self.connection.loop_stop()
            self.store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['normal', 'fail', 'timeout'], default='normal')
    Beacon(parser.parse_args().mode).run()
