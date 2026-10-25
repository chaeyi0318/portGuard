from datetime import datetime, timezone, timedelta
from uuid import uuid4
from db import db
from services.devices import CONFIG


def create_command(device_id, action):
    now = datetime.now(timezone.utc)
    command = dict(commandId=str(uuid4()), deviceId=device_id, action=action,
                   simulated=True, status='queued', requestedAt=now,
                   deadlineAt=now + timedelta(seconds=CONFIG['commandTimeoutSeconds']),
                   history=[{'status': 'queued', 'at': now}])
    db.commands.insert_one(command.copy())
    return command
