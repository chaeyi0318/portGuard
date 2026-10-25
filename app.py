from flask import Flask

from routes.incidents import incidents_bp
from routes.devices import devices_bp
from routes.rois import rois_bp

from pymongo.errors import PyMongoError

app = Flask(__name__)
app.json.ensure_ascii = False

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