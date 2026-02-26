from flask import Flask, render_template, request, redirect, url_for, session, flash
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
    if "username" in session:
        return redirect(url_for("predict_page"))
    return render_template("index.html")

@app.route("/predict")
def predict_page():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", logged_in=True)

@app.route("/submit_prediction", methods=["POST"])
def submit_prediction():

    # 1. เช็ก login
    if "user_id" not in session:
        return {"error": "unauthorized"}, 401

    data = request.json
    match_id = data["match_id"]
    predict_winner = data["predict_winner"]
    predict_score = data["predict_score"]

    user_id = session["user_id"]

    conn = get_mysql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO Pickem_DATA
            (Match_id, User_id, Predict_Winner, Predict_Score)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                Predict_Winner = VALUES(Predict_Winner),
                Predict_Score  = VALUES(Predict_Score)
            """,
            (match_id, user_id, predict_winner, predict_score)
        )
        conn.commit()
        print("✅ INSERT SUCCESS")
    except Exception as e:
        print("DB ERROR:", e)
        return {"status": "error"}, 500
    finally:
        cursor.close()
        conn.close()

    return {"status": "success"}

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
                flash('Username already exists', 'error')
                return render_template('register.html')

            cursor.execute(
                "INSERT INTO User (Username, Password) VALUES (%s, %s)",
                (username, password)
            )
            conn.commit()

        finally:
            cursor.close()
            conn.close()

        flash('Registration successful! Please log in.', 'success')
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

        if user and user["Password"] == password:
            session["user_id"] = user["User_id"]
            session["username"] = user["Username"]
            return redirect(url_for("predict_page"))

        flash('Invalid username or password', 'error') 
        return render_template('login.html')

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/teams")
def teams_page():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT Teamname, Shortname, Region, Logo, Wins, Losses, Points
        FROM Team
        ORDER BY Points DESC
    """)
    teams = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "teams.html",
        teams=teams,
        logged_in=("username" in session)
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)