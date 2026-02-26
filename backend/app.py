from flask import Flask, render_template, request, redirect, url_for, session
from db import get_mysql_connection, get_mongo_collection
import mysql.connector

app = Flask(
    __name__,
    template_folder = "../frontend/template",
    static_folder = "../frontend/static"
)      

app.secret_key = 'your_super_secret_key_here'

@app.route("/")
def index():
    # หน้าแรกสำหรับคนทั่วไป (Guest) 
    # แม้จะล็อกอินแล้วมาหน้านี้ ก็จะเห็นสถานะแบบ Guest หรือจะสั่ง redirect ไป /predict ก็ได้
    if "username" in session:
        return redirect(url_for("predict_page"))
    return render_template("index.html")

@app.route("/predict")
def predict_page():
    # หน้าสำหรับคนล็อกอินแล้วเท่านั้น
    if "username" not in session:
        return redirect(url_for("login")) # ถ้าแอบเข้าหน้านี้โดยไม่ล็อกอิน ให้ไล่ไปหน้า login
    return render_template("index.html", logged_in=True)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM User WHERE Username = %s",
                (username,)
            )
            existing = cursor.fetchone()

            if existing:
                return "Username already exists"

            cursor.execute(
                "INSERT INTO User (Username, Password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM User WHERE Username = %s",
                (username,)
            )
            user = cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

        # ตรวจสอบรหัสผ่านแบบเทียบ String ตรงๆ
        if user and user["Password"] == password:
            session["user_id"] = user["User_id"]
            session["username"] = user["Username"]
            return redirect(url_for("index"))

        return "Invalid username or password"

    return render_template("login.html")



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)