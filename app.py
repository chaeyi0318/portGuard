from flask import Flask

from routes.incidents import incidents_bp
from routes.devices import devices_bp
from routes.rois import rois_bp
from socket_server import socketio

from pymongo.errors import PyMongoError

app = Flask(__name__)
app.json.ensure_ascii = False

socketio.init_app(
    app,
    async_mode="threading",
    path="/vision-socket/socket.io",
)

app.register_blueprint(incidents_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(rois_bp)

@app.get("/vision-api/health")
def health():
    return {
        "status": "ok",
        "service": "portguard",
    }

@app.errorhandler(PyMongoError)
def handle_database_error(error):
    app.logger.exception("MongoDB 작업 실패")

    return {
        "error": "데이터베이스 작업을 완료하지 못했습니다",
        "code": "DATABASE_ERROR",
    }, 503


if __name__ == "__main__":
    from socket_notifications import start_notifications

    notifications = start_notifications(app)

    try:
        socketio.run(
            app,
            host="127.0.0.1",
            port=5001,
            debug=False,
            use_reloader=False,
        )
    finally:
        notifications.disconnect()
        notifications.loop_stop()