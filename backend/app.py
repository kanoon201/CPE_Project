from flask import abort

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
    if "user_id" not in session:
        return redirect(url_for("login"))

    is_admin = session.get("username") == "ADMIN"

    match_col = get_mongo_collection("pickem_matches")
    matches = list(match_col.find().sort("order", 1))

    # ดึง team logos จาก MySQL
    conn_t = get_mysql_connection()
    cursor_t = conn_t.cursor(dictionary=True)
    cursor_t.execute("SELECT Shortname, Teamname, Logo FROM Team")
    team_logos = {row["Shortname"]: row for row in cursor_t.fetchall()}
    cursor_t.close()
    conn_t.close()

    user_predictions = {}

    # หลังจากดึง matches จาก MongoDB แล้ว

    user_predictions = {}

    if "user_id" in session:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT Match_id, Predict_Winner, Predict_Score
            FROM Pickem_DATA
            WHERE User_id = %s
        """, (session["user_id"],))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # แปลงเป็น dict
        for r in rows:
            user_predictions[r["Match_id"]] = r

    return render_template(
        "index.html",
        matches=matches,
        user_predictions=user_predictions,
        team_logos=team_logos,          # ← เพิ่มบรรทัดนี้
        logged_in=("user_id" in session),
        is_admin=(session.get("username") == "ADMIN")
    )

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
        logged_in=("username" in session),
        is_admin=(session.get("username") == "ADMIN")
    )


@app.route("/results")
def results_page():
    if session.get("username") != "ADMIN":
        return redirect(url_for("index"))

    collection = get_mongo_collection("match_results")

    if collection is None:
        results = []
    else:
        results = list(collection.find())

    return render_template(
        "results.html",
        results=results,
        logged_in=True,
        is_admin=True
    )
from datetime import datetime

@app.route("/admin/result", methods=["POST"])
def admin_add_result():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403

    data = request.json
    collection = get_mongo_collection("match_results")

    collection.update_one(
        {"match_id": data["match_id"]},
        {"$set": {
            "match_id": data["match_id"],
            "team1": data["team1"],
            "team2": data["team2"],
            "score": data["score"],
            "winner": data["winner"],
            "played_at": data.get("played_at"),
            "updated_by": session["username"],
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )

    return {"status": "success", "message": "Result saved"}


@app.route("/admin/update_match", methods=["POST"])
def admin_update_match():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403

    data = request.json
    col = get_mongo_collection("pickem_matches")

    update_fields = {
        "team1": data.get("team1"),
        "team2": data.get("team2"),
        "status": data.get("status", "upcoming")
    }

    if data.get("score"):
        update_fields["score"] = data["score"]
        update_fields["winner"] = data["winner"]
        update_fields["status"] = "completed"

    col.update_one(
        {"match_id": data["match_id"]},
        {"$set": update_fields}
    )

    return {"status": "success"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)