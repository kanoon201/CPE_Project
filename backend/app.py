from flask import Flask, jsonify, request, render_template, redirect
from db import get_mysql_connection, get_mongo_collection
import mysql.connector

app = Flask(
    __name__,
    template_folder = "../frontend/template",
    static_folder = "../frontend/static"
)

# --- Frontend Route ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Register Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        # check user exists
        cursor.execute(
            "SELECT * FROM User WHERE Username = %s",
            (username,)
        )

        existing = cursor.fetchone()

        if existing:
            return "Username already exists"

        # insert new user
        cursor.execute(
            "INSERT INTO User (Username, Password) VALUES (%s, %s)",
            (username, password)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')







































