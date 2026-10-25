from flask import Flask

from routes.incidents import incidents_bp

app = Flask(__name__)
app.json.ensure_ascii = False

app.register_blueprint(incidents_bp)

@app.get("/vision-api/health")
def health():
    return {
        "status": "ok",
        "service": "portguard",
    }