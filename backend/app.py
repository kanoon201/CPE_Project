from flask import Flask, jsonify, request, render_template
from db import get_mysql_connection, get_mongo_collection, get_redis_client
import mysql.connector

app = Flask(__name__)


#qwertyuiopadadadadada
# - Database Initialization aaa
def init_mysql_db():
    conn = get_mysql_connection()
    if conn:
        cursor = conn.cursor()

        # ---------------- USER ----------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS User (
                User_id INT AUTO_INCREMENT PRIMARY KEY,
                Username VARCHAR(100) NOT NULL UNIQUE,
                Password VARCHAR(255) NOT NULL
            )
        """)

        # ---------------- TEAM ----------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Team (
                Team_id INT AUTO_INCREMENT PRIMARY KEY,
                Teamname VARCHAR(100) NOT NULL,
                Shortname VARCHAR(20) NOT NULL UNIQUE,
                Region VARCHAR(100)
            )
        """)

        # ---------------- LEADERBOARD ----------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS LeaderBoard (
                User_id INT PRIMARY KEY,
                Username VARCHAR(100) NOT NULL,
                Score INT DEFAULT 0,
                Ranking INT DEFAULT NULL,
                FOREIGN KEY (User_id) REFERENCES User(User_id)
                    ON DELETE CASCADE
            )
        """)

        # ---------------- PICKEM_DATA ----------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Pickem_DATA (
                Pickem_id INT AUTO_INCREMENT PRIMARY KEY,
                Match_id VARCHAR(50) NOT NULL,
                User_id INT NOT NULL,
                Predict_Winner VARCHAR(20),
                Predict_Score VARCHAR(20),
                FOREIGN KEY (User_id) REFERENCES User(User_id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("All MySQL tables initialized successfully.")

if __name__ == '__main__':
    try:
        init_mysql_db()
    except Exception as e:
        print(f"Warning: DB init failed: {e}")

    app.run(host='0.0.0.0', port=5001, debug=True)