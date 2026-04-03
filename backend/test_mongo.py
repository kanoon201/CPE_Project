from pymongo import MongoClient

uri = "mongodb://nattanon_ru:FGVkrcIo@p1.secondtrain.org:27017/nattanon_ru_mg"
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()
    print("✅ Connected!")
    db = client["pickem_db"]
    print("Collections:", db.list_collection_names())
except Exception as e:
    print("❌ Failed:", e)