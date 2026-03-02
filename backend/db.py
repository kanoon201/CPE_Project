import os
import mysql.connector
from pymongo import MongoClient
import redis


# MySQL Connection
# Note: In a production environment, consider using connection pooling for better performance.
#query = "SELECT * FROM User"
def get_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "root"),
            database=os.getenv("MYSQL_DATABASE", "pickem_db"),
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        return connection # Placeholder
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None


def get_mongo_collection(collection_name):
    try:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/pickem_db")
        client = MongoClient(uri)
        db = client.get_database()
        return db[collection_name]
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return None