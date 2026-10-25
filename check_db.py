import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

uri = os.getenv("MONGODB_URI")

if not uri:
    raise SystemExit(".env에 MONGODB_URI를 설정해 주세요.")

try:
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        client.admin.command("ping")
        print("MongoDB 연결 성공!")
except PyMongoError as error:
    print(f"MongoDB 연결 실패: {type(error).__name__}")