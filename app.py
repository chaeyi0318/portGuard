from flask import Flask
from db import db

app = Flask(__name__)

@app.get("/vision-api/health")
def health():
    return {
        "status": "ok",
        "service": "portguard",
    }