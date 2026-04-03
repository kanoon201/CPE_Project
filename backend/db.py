import os
import mysql.connector
from mysql.connector import Error
from pymongo import MongoClient

# โหลด config จาก local_config.py ถ้ามี
try:
    from local_config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, \
                             MYSQL_DATABASE, MYSQL_PORT, MONGO_URI, MONGO_DB
except ImportError:
    MYSQL_HOST     = os.getenv("MYSQL_HOST",     "localhost")
    MYSQL_USER     = os.getenv("MYSQL_USER",     "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "pickem_db")
    MYSQL_PORT     = int(os.getenv("MYSQL_PORT", 3306))
    MONGO_URI      = os.getenv("MONGO_URI",      "mongodb://localhost:27017")
    MONGO_DB       = os.getenv("MONGO_DB",       "pickem_db")


def get_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=int(MYSQL_PORT)
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None


def get_mongo_collection(collection_name):
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        print("Using Mongo collection:", collection_name)
        return db[collection_name]  # ← แก้จาก db["tournaments"]
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None