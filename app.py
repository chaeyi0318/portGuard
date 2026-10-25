from flask import Flask

app = Flask(__name__)

@app.get("/vision-api/health")
def health():
    return {
        "status": "ok",
        "service": "portguard",
    }