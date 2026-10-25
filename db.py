import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE")

if not uri or not database_name:
    raise RuntimeError("MongoDB 환경 설정을 확인해 주세요.")

client = MongoClient(
    uri,
    serverSelectionTimeoutMS=5000,
    tz_aware=True,
)

db = client[database_name]