import json
import time
from uuid import uuid4
import sqlite3
import threading
from pathlib import Path
import argparse

from mqtt.common import client, connect, now
from services.devices import CONFIG, utc


class Gate:
    def __init__(self, mode='normal'):
        self.mode = mode
        self.device_id = 'GATE-01'
        self.lock = threading.RLock()

        Path('data').mkdir(parents=True, exist_ok=True)
        self.store = sqlite3.connect(
            'data/gate.sqlite3',
            check_same_thread=False,
        )

        self.store.execute(
            '''
            CREATE TABLE IF NOT EXISTS commands (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                result TEXT NOT NULL
            )
            '''
        )

        self.store.execute(
            '''
            CREATE TABLE IF NOT EXISTS state (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            '''
        )
        self.store.commit()

        row = self.store.execute(
            'SELECT value FROM state WHERE id = 1'
        ).fetchone()

        self.operation = row[0] if row else 'closed'

        self.session_id = str(uuid4())
        self.session_started_at = now().isoformat()
        self.sequence = 0

        self.connection = client('portguard-GATE-01')
        self.connection.on_connect = self.on_connect
        self.connection.on_message = self.on_message

    def publish(self, topic, **fields):
        with self.lock:
            self.sequence += 1

            data = {
                'deviceId': self.device_id,
                'sessionId': self.session_id,
                'sessionStartedAt': self.session_started_at,
                'sequence': self.sequence,
                'sentAt': now().isoformat(),
                'simulated': True,
                'operationStatus': self.operation,
                **fields,
            }

            self.connection.publish(
                f'devices/{self.device_id}/{topic}',
                json.dumps(data),
                qos=1,
                retain=False,
            )

    def on_connect(self, connection, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return

        connection.subscribe(
            f'devices/{self.device_id}/commands',
            qos=1,
        )
        self.publish('status')
        print(f'GATE-01 연결 완료 — 현재 상태: {self.operation}')

    def on_message(self, connection, userdata, message):
        if message.retain:
            return

        try:
            data = json.loads(message.payload)

            if not isinstance(data, dict):
                return

            if data.get('deviceId') != self.device_id:
                return

            if data.get('simulated') is not True:
                return

            if data.get('action') not in ('open', 'close'):
                return

            command_id = data.get('commandId')

            if not isinstance(command_id, str) or not command_id.strip():
                return

            if utc(data['deadlineAt']) <= now():
                return

            action = data['action']

            with self.lock:
                row = self.store.execute(
                    'SELECT action, result FROM commands WHERE id = ?',
                    (command_id,),
                ).fetchone()

                if row:
                    if row[0] != action:
                        return

                    self.publish(
                        'acks',
                        commandId=command_id,
                        status=row[1],
                    )
                    print(f'중복 명령 — 저장 결과 재전송: {command_id}')
                    return

                self.publish(
                    'acks',
                    commandId=command_id,
                    status='accepted',
                )

                if self.mode == 'fail':
                    with self.store:
                        self.store.execute(
                            'INSERT INTO commands (id, action, result) VALUES (?, ?, ?)',
                            (command_id, action, 'failed'),
                        )

                    self.publish(
                        'acks',
                        commandId=command_id,
                        status='failed',
                    )

                    print(f'모의 작동 실패: {command_id}')
                    return

                target = 'open' if action == 'open' else 'closed'

                with self.store:
                    self.store.execute(
                        'INSERT OR REPLACE INTO state (id, value) VALUES (1, ?)',
                        (target,),
                    )
                    self.store.execute(
                        'INSERT INTO commands (id, action, result) VALUES (?, ?, ?)',
                        (command_id, action, 'succeeded'),
                    )

                self.operation = target

                self.publish(
                    'acks',
                    commandId=command_id,
                    status='succeeded',
                )

                print(f'모의 작동 완료: {command_id} / 상태: {target}')

        except (ValueError, TypeError, KeyError):
            print('잘못된 명령 메시지 무시')

    def run(self):
        connect(self.connection)

        try:
            while True:
                if self.connection.is_connected():
                    self.publish('heartbeat')

                time.sleep(CONFIG['heartbeatSeconds'])

        except KeyboardInterrupt:
            print('GATE-01 종료')

        finally:
            self.connection.disconnect()
            self.connection.loop_stop()
            self.store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--mode',
        choices=['normal', 'fail'],
        default='normal',
    )
    args = parser.parse_args()

    Gate(mode=args.mode).run()