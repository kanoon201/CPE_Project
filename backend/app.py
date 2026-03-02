from flask import abort
from flask import Flask, render_template, request, redirect, url_for, session, flash
from db import get_mysql_connection, get_mongo_collection
from seed_bracket import seed_bracket
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
    
    is_admin = session.get("username") == "โ"
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
        
        for r in rows:
            user_predictions[r["Match_id"]] = r

    # สร้าง dict match_id -> match สำหรับ lookup team1_src/team2_src ใน template
    matches_map = {m["match_id"]: m for m in matches}

    return render_template(
        "index.html",
        matches=matches,
        matches_map=matches_map,
        user_predictions=user_predictions,
        team_logos=team_logos,
        logged_in=("user_id" in session),
        is_admin=(session.get("username") == "ADMIN")
    )

@app.route("/submit_prediction", methods=["POST"])
def submit_prediction():
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
        cursor.execute("""
            INSERT INTO Pickem_DATA (Match_id, User_id, Predict_Winner, Predict_Score)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                Predict_Winner = VALUES(Predict_Winner), 
                Predict_Score = VALUES(Predict_Score)
        """, (match_id, user_id, predict_winner, predict_score))
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
            cursor.execute("SELECT * FROM User WHERE Username = %s", (username,))
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
            cursor.execute("SELECT * FROM User WHERE Username = %s", (username,))
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/matches")
def matches_page():
    match_col = get_mongo_collection("pickem_matches")
    matches = list(match_col.find().sort("order", 1))

    # จัดกลุ่มตาม bracket และ round
    upper_rounds = {}
    lower_rounds = {}
    grand_rounds = {}

    for m in matches:
        bracket = m.get("bracket")
        round_name = m.get("round")

        if bracket == "upper":
            upper_rounds.setdefault(round_name, []).append(m)
        elif bracket == "lower":
            lower_rounds.setdefault(round_name, []).append(m)
        elif bracket == "grand":
            grand_rounds.setdefault(round_name, []).append(m)

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Shortname, Teamname, Logo FROM Team")
    team_logos = {row["Shortname"]: row for row in cursor.fetchall()}
    cursor.close()
    conn.close()

    user_predictions = {}
    if "user_id" in session:
        conn2 = get_mysql_connection()
        cursor2 = conn2.cursor(dictionary=True)
        cursor2.execute("""
            SELECT Match_id, Predict_Winner, Predict_Score
            FROM Pickem_DATA
            WHERE User_id = %s
        """, (session["user_id"],))
        for r in cursor2.fetchall():
            user_predictions[r["Match_id"]] = r
        cursor2.close()
        conn2.close()

    return render_template(
        "matches.html",
        upper_rounds=upper_rounds,
        lower_rounds=lower_rounds,
        grand_rounds=grand_rounds,
        team_logos=team_logos,
        logged_in=("username" in session),
        is_admin=(session.get("username") == "ADMIN"),
        user_predictions=user_predictions
    )
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
    results = list(collection.find()) if collection is not None else []
    
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
    match_id = data.get("match_id")
    team1 = data.get("team1")
    team2 = data.get("team2")
    score = data.get("score")
    winner = data.get("winner")
    
    current_match = col.find_one({"match_id": match_id})
    already_completed = current_match.get("status") == "completed"

    update_fields = {
        "team1": team1,
        "team2": team2,
        "status": data.get("status", "upcoming")
    }

    if score and winner:
        update_fields["score"] = score
        update_fields["winner"] = winner
        update_fields["status"] = "completed"

    col.update_one({"match_id": match_id}, {"$set": update_fields})
    if score and winner and not already_completed:
        loser = None
        if team1 == winner:
            loser = team2
        elif team2 == winner:
            loser = team1

        if winner and loser:
            conn = get_mysql_connection()
            cursor = conn.cursor()
            try:
                # Winner gets +1 Win, +3 Points
                cursor.execute("""
                    UPDATE Team
                    SET Wins = Wins + 1, Points = Points + 3
                    WHERE Shortname = %s
                """, (winner,))

                # Loser gets +1 Loss
                cursor.execute("""
                    UPDATE Team
                    SET Losses = Losses + 1
                    WHERE Shortname = %s
                """, (loser,))

                conn.commit()
                print(f"✅ Team stats updated: {winner} won, {loser} lost")
            except Exception as e:
                print("DB ERROR updating team stats:", e)
            finally:
                cursor.close()
                conn.close()
    updated_match = col.find_one({"match_id": match_id})
    if score and winner and updated_match:
        loser = updated_match["team2"] if updated_match["team1"] == winner else updated_match["team1"]

        next_win_id = updated_match.get("next_win")
        if next_win_id:
            next_match = col.find_one({"match_id": next_win_id})
            if next_match:
                target_field = "team1" if not next_match.get("team1") else (
                    "team2" if not next_match.get("team2") else None)
                if target_field:
                    col.update_one({"match_id": next_win_id},
                                   {"$set": {target_field: winner, "status": "upcoming"}})

        next_lose_id = updated_match.get("next_lose")
        if next_lose_id and loser:
            next_match = col.find_one({"match_id": next_lose_id})
            if next_match:
                target_field = "team1" if not next_match.get("team1") else (
                    "team2" if not next_match.get("team2") else None)
                if target_field:
                    col.update_one({"match_id": next_lose_id},
                                   {"$set": {target_field: loser, "status": "upcoming"}})

    return {"status": "success"}

@app.route("/teams/data")
def teams_data():
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT Teamname, Shortname, Region, Logo, Wins, Losses, Points
        FROM Team ORDER BY Points DESC
    """)
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"teams": teams}

@app.route("/leaderboard")
def leaderboard_page():
    result_col = get_mongo_collection("pickem_matches")
    results = list(result_col.find())

    # round multiplier ตาม bracket round
    ROUND_MULTIPLIER = {
        "Upper Quarterfinals": 1,
        "Lower Round 1":       1,
        "Upper Semifinals":    2,
        "Lower Round 2":       2,
        "Lower Round 3":       4,
        "Upper Final":         4,
        "Lower Final":         8,
        "Grand Final":         16,
    }

    # map match_id → {winner, score, round}
    match_info = {}
    for r in results:
        if r.get("winner"):
            match_info[r["match_id"]] = {
                "winner": r.get("winner"),
                "score":  r.get("score"),
                "round":  r.get("round", "")
            }

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT Shortname, Teamname FROM Team")
    teams = cursor.fetchall()
    name_to_short = {}
    for t in teams:
        name_to_short[t["Teamname"]] = t["Shortname"]
        name_to_short[t["Shortname"]] = t["Shortname"]

    cursor.execute("""
        SELECT u.Username, pd.Match_id, pd.Predict_Winner, pd.Predict_Score
        FROM User u
        LEFT JOIN Pickem_DATA pd ON u.User_id = pd.User_id
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    scores = {}
    for row in rows:
        uname = row["Username"]
        if uname not in scores:
            scores[uname] = {"Username": uname, "CorrectPicks": 0, "Score": 0}

        if not row["Match_id"] or not row["Predict_Winner"]:
            continue

        info = match_info.get(row["Match_id"])
        if not info:
            continue

        multiplier = ROUND_MULTIPLIER.get(info["round"], 1)

        predicted_short = name_to_short.get(row["Predict_Winner"], row["Predict_Winner"])
        actual_short    = name_to_short.get(info["winner"], info["winner"])

        if actual_short and predicted_short == actual_short:
            # ทายทีมถูก — เช็คสกอร์ด้วย
            if row["Predict_Score"] and row["Predict_Score"] == info["score"]:
                # ถูกหมด → 10 คะแนน × multiplier
                pts = 10 * multiplier
            else:
                # ถูกทีม สกอร์ผิด → 5 คะแนน × multiplier
                pts = 5 * multiplier
            scores[uname]["CorrectPicks"] += 1
            scores[uname]["Score"] += pts
        # ทายผิด → 0 คะแนน (ไม่ต้องทำอะไร)

    leaderboard = sorted(scores.values(), key=lambda x: x["Score"], reverse=True)

    user_rank = None
    user_score = None
    if "username" in session:
        for i, entry in enumerate(leaderboard):
            if entry["Username"] == session["username"]:
                user_rank = i + 1
                user_score = entry["Score"]
                break

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard,
        logged_in=("user_id" in session),
        username=session.get("username"),
        is_admin=(session.get("username") == "ADMIN"),
        user_rank=user_rank,
        user_score=user_score
    )

if __name__ == '__main__':
    seed_bracket()
    app.run(host='0.0.0.0', port=5001, debug=True)