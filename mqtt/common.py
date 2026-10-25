"""Shared MQTT connection and UTC helpers; never imported by Flask."""
import os
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from dotenv import load_dotenv


def now():
    return datetime.now(timezone.utc)


def client(client_id):
    load_dotenv()
    connection = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if os.getenv('MQTT_USERNAME'):
        connection.username_pw_set(os.environ['MQTT_USERNAME'], os.getenv('MQTT_PASSWORD'))
    if os.getenv('MQTT_TLS', '0') == '1':
        connection.tls_set()
    connection.enable_logger()
    return connection


def connect(connection):
    connection.connect_async(os.getenv('MQTT_HOST', '127.0.0.1'), int(os.getenv('MQTT_PORT', '1883')), 6)
    connection.loop_start()
