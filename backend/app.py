from flask import abort, Flask, render_template, request, redirect, url_for, session, flash, jsonify
from db import get_mysql_connection, get_mongo_collection
from seed_bracket import seed_bracket, create_tournament_bracket
import mysql.connector
from datetime import datetime

import os

try:
    from local_config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, \
                             MYSQL_DATABASE, MYSQL_PORT, MONGO_URI, MONGO_DB
except ImportError:
    MYSQL_HOST     = os.environ.get("MYSQL_HOST",     "localhost")
    MYSQL_USER     = os.environ.get("MYSQL_USER",     "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "root")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "pickem_db")
    MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", 3306))
    MONGO_URI      = os.environ.get("MONGO_URI",      "mongodb://localhost:27017")
    MONGO_DB       = os.environ.get("MONGO_DB",       "pickem_db")


app = Flask(__name__,
    template_folder="template",
    static_folder="static"
)
app.secret_key = os.environ.get('SECRET_KEY', 'your_super_secret_key_here')

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

ROUND_MULTIPLIER = {
    "Upper Quarterfinals": 10,
    "Lower Round 1":       10,
    "Upper Semifinals":    15,
    "Lower Round 2":       15,
    "Lower Round 3":       25,
    "Upper Final":         30,
    "Lower Final":         30,
    "Grand Final":         40,
}

def get_active_tournaments():
    """ดึงทุก tournament ที่ active (อาจมีมากกว่า 1)"""
    t_col = get_mongo_collection("tournaments")
    return list(t_col.find({"is_active": True}).sort("date", -1))

def get_active_tournament():
    """backward-compat: ดึงอันแรกที่ active"""
    actives = get_active_tournaments()
    return actives[0] if actives else None

def get_tournament(tournament_id):
    t_col = get_mongo_collection("tournaments")
    return t_col.find_one({"tournament_id": tournament_id})

def get_all_tournaments():
    t_col = get_mongo_collection("tournaments")
    return list(t_col.find().sort("date", -1))



def get_current_tournament_id():
    if "tournament_id" in session:
        t = get_tournament(session["tournament_id"])
        if t and t.get("is_active"):
            return session["tournament_id"]
    # ถ้าไม่มีใน session หรือ tournament ที่เลือกถูก deactivate → ใช้อันแรกที่ active
    actives = get_active_tournaments()
    if actives:
        return actives[0]["tournament_id"]
    return None

def get_team_logos_for_tournament(tournament_id):
    # โหลดเฉพาะทีมที่อยู่ใน tournament นี้ (สำหรับ predict/bracket)
    t = get_tournament(tournament_id)
    if not t:
        return {}
    team_list = t.get("teams", [])
    if not team_list:
        return {}
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ",".join(["%s"] * len(team_list))
    cursor.execute(f"SELECT Shortname, Teamname, Logo FROM Team WHERE Shortname IN ({placeholders})", team_list)
    result = {row["Shortname"]: row for row in cursor.fetchall()}
    cursor.close(); conn.close()
    return result

def get_all_team_logos():
    # โหลดทีมทั้งหมดจาก DB (สำหรับ admin assign dropdown)
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Shortname, Teamname, Logo FROM Team ORDER BY Shortname")
    result = {row["Shortname"]: row for row in cursor.fetchall()}
    cursor.close(); conn.close()
    return result

def get_user_predictions(user_id, tournament_id):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT Match_id, Predict_Winner, Predict_Score
        FROM Pickem_DATA WHERE User_id = %s AND Tournament_id = %s
    """, (user_id, tournament_id))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return {r["Match_id"]: r for r in rows}

def get_matches_for_tournament(tournament_id):
    col = get_mongo_collection("pickem_matches")
    # filter เฉพาะ doc ที่มี match_id (ป้องกัน doc เก่าที่ไม่มี field นี้)
    return list(col.find(
        {"tournament_id": tournament_id, "match_id": {"$exists": True}}
    ).sort("_id", 1))

def compute_leaderboard(tournament_id):
    matches = get_matches_for_tournament(tournament_id)
    match_info = {}
    for m in matches:
        if m.get("winner"):
            match_info[m["match_id"]] = {
                "winner": m.get("winner"),
                "score":  m.get("score"),
                "round":  m.get("round", "")
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
        LEFT JOIN Pickem_DATA pd ON u.User_id = pd.User_id AND pd.Tournament_id = %s
    """, (tournament_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()

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
            pts = multiplier if (row["Predict_Score"] and row["Predict_Score"] == info["score"]) else multiplier / 2
            scores[uname]["CorrectPicks"] += 1
            scores[uname]["Score"] += pts

    return sorted(scores.values(), key=lambda x: x["Score"], reverse=True)


# ─────────────────────────────────────────────
# MAIN PAGES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    tournaments = get_all_tournaments()
    active_tournaments = get_active_tournaments()
    return render_template(
        "index.html",
        logged_in=("user_id" in session),
        is_admin=(session.get("username") == "ADMIN"),
        tournaments=tournaments,
        active_tournaments=active_tournaments
    )

@app.route("/tournaments")
def tournaments_page():
    all_t = get_all_tournaments()
    active_tournaments = [t for t in all_t if t.get("is_active")]
    other_tournaments  = [t for t in all_t if not t.get("is_active")]
    tournament_id      = get_current_tournament_id()

    # ดึง logos ของทุกทีมในทุก tournament
    all_shorts = list({s for t in all_t for s in t.get("teams", [])})
    team_logos = {}
    if all_shorts:
        conn = get_mysql_connection(); cursor = conn.cursor(dictionary=True)
        ph = ",".join(["%s"] * len(all_shorts))
        cursor.execute(f"SELECT Shortname, Teamname, Logo FROM Team WHERE Shortname IN ({ph})", all_shorts)
        team_logos = {r["Shortname"]: r for r in cursor.fetchall()}
        cursor.close(); conn.close()

    return render_template(
        "tournaments.html",
        active_tournaments=active_tournaments,
        other_tournaments=other_tournaments,
        team_logos=team_logos,
        current_tournament_id=tournament_id,
        logged_in=("user_id" in session),
        username=session.get("username", ""),
        is_admin=(session.get("username") == "ADMIN"),
    )


@app.route("/select_tournament/<tournament_id>")
def select_tournament(tournament_id):
    t = get_tournament(tournament_id)
    if t:
        session["tournament_id"] = tournament_id
    next_page = request.args.get("next", "/predict")
    return redirect(next_page)

@app.route("/predict")
def predict_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    tournament_id = get_current_tournament_id()
    if not tournament_id:
        flash("No active tournament at the moment.", "error")
        return redirect(url_for("index"))

    tournament  = get_tournament(tournament_id)
    is_admin    = session.get("username") == "ADMIN"
    matches     = get_matches_for_tournament(tournament_id)
    team_logos  = get_team_logos_for_tournament(tournament_id)
    user_predictions = get_user_predictions(session["user_id"], tournament_id)
    matches_map = {m["match_id"]: m for m in matches}
    all_tournaments = get_all_tournaments()

    return render_template(
        "predict.html",
        matches=matches,
        matches_map=matches_map,
        user_predictions=user_predictions,
        team_logos=team_logos,
        logged_in=True,
        is_admin=is_admin,
        tournament=tournament,
        all_tournaments=all_tournaments,
        current_tournament_id=tournament_id
    )

@app.route("/submit_prediction", methods=["POST"])
def submit_prediction():
    if "user_id" not in session:
        return {"error": "unauthorized"}, 401

    data           = request.json
    match_id       = data["match_id"]
    predict_winner = data["predict_winner"]
    predict_score  = data["predict_score"]
    tournament_id  = data.get("tournament_id") or get_current_tournament_id()
    user_id        = session["user_id"]

    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Pickem_DATA (Tournament_id, Match_id, User_id, Predict_Winner, Predict_Score)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                Predict_Winner = VALUES(Predict_Winner),
                Predict_Score  = VALUES(Predict_Score)
        """, (tournament_id, match_id, user_id, predict_winner, predict_score))
        conn.commit()
    except Exception as e:
        print("DB ERROR:", e)
        return {"status": "error"}, 500
    finally:
        cursor.close(); conn.close()

    return {"status": "success"}

@app.route("/matches")
def matches_page():
    tournament_id = get_current_tournament_id()
    if not tournament_id:
        flash("No active tournament.", "error")
        return redirect(url_for("index"))

    tournament = get_tournament(tournament_id)
    matches    = get_matches_for_tournament(tournament_id)

    upper_rounds = {}; lower_rounds = {}; grand_rounds = {}
    for m in matches:
        bracket = m.get("bracket"); round_name = m.get("round")
        if bracket == "upper":
            upper_rounds.setdefault(round_name, []).append(m)
        elif bracket == "lower":
            lower_rounds.setdefault(round_name, []).append(m)
        elif bracket == "grand":
            grand_rounds.setdefault(round_name, []).append(m)

    team_logos       = get_team_logos_for_tournament(tournament_id)
    user_predictions = get_user_predictions(session["user_id"], tournament_id) if "user_id" in session else {}
    all_tournaments  = get_all_tournaments()

    return render_template(
        "matches.html",
        upper_rounds=upper_rounds, lower_rounds=lower_rounds, grand_rounds=grand_rounds,
        team_logos=team_logos,
        logged_in=("username" in session),
        is_admin=(session.get("username") == "ADMIN"),
        user_predictions=user_predictions,
        tournament=tournament,
        all_tournaments=all_tournaments,
        current_tournament_id=tournament_id
    )

@app.route("/teams")
def teams_page():
    tournament_id = get_current_tournament_id()
    tournament    = get_tournament(tournament_id) if tournament_id else None
    team_shortnames = tournament.get("teams", []) if tournament else []

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    if team_shortnames:
        placeholders = ",".join(["%s"] * len(team_shortnames))
        cursor.execute(f"""
            SELECT t.Teamname, t.Shortname, t.Region, t.Logo,
                   COALESCE(ts.Wins,0) as Wins,
                   COALESCE(ts.Losses,0) as Losses,
                   COALESCE(ts.Points,0) as Points
            FROM Team t
            LEFT JOIN TeamStats ts ON t.Shortname = ts.Shortname AND ts.Tournament_id = %s
            WHERE t.Shortname IN ({placeholders})
            ORDER BY COALESCE(ts.Points,0) DESC, COALESCE(ts.Wins,0) DESC
        """, [tournament_id] + team_shortnames)
    else:
        cursor.execute("SELECT Teamname, Shortname, Region, Logo, 0 as Wins, 0 as Losses, 0 as Points FROM Team")
    teams = cursor.fetchall()
    cursor.close(); conn.close()

    return render_template(
        "teams.html", teams=teams,
        logged_in=("username" in session),
        is_admin=(session.get("username") == "ADMIN"),
        tournament=tournament,
        all_tournaments=get_all_tournaments(),
        current_tournament_id=tournament_id
    )

@app.route("/teams/data")
def teams_data():
    tournament_id   = request.args.get("tournament_id") or get_current_tournament_id()
    tournament      = get_tournament(tournament_id) if tournament_id else None
    team_shortnames = tournament.get("teams", []) if tournament else []

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    if team_shortnames:
        placeholders = ",".join(["%s"] * len(team_shortnames))
        cursor.execute(f"""
            SELECT t.Teamname, t.Shortname, t.Region, t.Logo,
                   COALESCE(ts.Wins,0) as Wins,
                   COALESCE(ts.Losses,0) as Losses,
                   COALESCE(ts.Points,0) as Points
            FROM Team t
            LEFT JOIN TeamStats ts ON t.Shortname = ts.Shortname AND ts.Tournament_id = %s
            WHERE t.Shortname IN ({placeholders})
            ORDER BY COALESCE(ts.Points,0) DESC, COALESCE(ts.Wins,0) DESC
        """, [tournament_id] + team_shortnames)
        teams = cursor.fetchall()
    else:
        teams = []
    cursor.close(); conn.close()
    return {"teams": teams}

@app.route("/leaderboard")
def leaderboard_page():
    tournament_id = get_current_tournament_id()
    if not tournament_id:
        flash("No active tournament.", "error")
        return redirect(url_for("index"))

    tournament  = get_tournament(tournament_id)
    leaderboard = compute_leaderboard(tournament_id)

    user_rank = None; user_score = None
    if "username" in session:
        for i, entry in enumerate(leaderboard):
            if entry["Username"] == session["username"]:
                user_rank = i + 1; user_score = entry["Score"]; break

    return render_template(
        "leaderboard.html",
        leaderboard=leaderboard,
        logged_in=("user_id" in session),
        username=session.get("username"),
        is_admin=(session.get("username") == "ADMIN"),
        user_rank=user_rank, user_score=user_score,
        tournament=tournament,
        all_tournaments=get_all_tournaments(),
        current_tournament_id=tournament_id
    )

@app.route("/user/<profile_username>")
def user_profile(profile_username):
    tournament_id = get_current_tournament_id()
    tournament    = get_tournament(tournament_id) if tournament_id else None
    matches       = get_matches_for_tournament(tournament_id) if tournament_id else []

    upper_rounds = {}; lower_rounds = {}; grand_rounds = {}
    for m in matches:
        bracket = m.get("bracket"); round_name = m.get("round")
        if bracket == "upper":   upper_rounds.setdefault(round_name, []).append(m)
        elif bracket == "lower": lower_rounds.setdefault(round_name, []).append(m)
        elif bracket == "grand": grand_rounds.setdefault(round_name, []).append(m)

    team_logos = get_team_logos_for_tournament(tournament_id) if tournament_id else {}

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT User_id FROM User WHERE Username = %s", (profile_username,))
    target_user = cursor.fetchone()
    cursor.close(); conn.close()

    user_predictions = {}
    if target_user and tournament_id:
        user_predictions = get_user_predictions(target_user["User_id"], tournament_id)

    total_score = 0; correct_picks = 0; total_picks = len(user_predictions)
    for m in matches:
        if m.get("status") != "completed" or not m.get("winner"):
            continue
        pred = user_predictions.get(m["match_id"])
        if not pred:
            continue
        multiplier = ROUND_MULTIPLIER.get(m.get("round", ""), 1)
        t1_full = team_logos.get(m.get("team1", ""), {}).get("Teamname", m.get("team1", ""))
        t2_full = team_logos.get(m.get("team2", ""), {}).get("Teamname", m.get("team2", ""))
        aw = m["winner"]; pw = pred["Predict_Winner"]
        winner_correct = (
            (aw == m.get("team1") or aw == t1_full) and (pw == m.get("team1") or pw == t1_full)
        ) or (
            (aw == m.get("team2") or aw == t2_full) and (pw == m.get("team2") or pw == t2_full)
        )
        if winner_correct:
            correct_picks += 1
            total_score += multiplier if pred.get("Predict_Score") == m.get("score") else multiplier / 2

    leaderboard = compute_leaderboard(tournament_id) if tournament_id else []
    user_rank   = next((i + 1 for i, e in enumerate(leaderboard) if e["Username"] == profile_username), None)

    return render_template(
        "user_profile.html",
        profile_username=profile_username,
        upper_rounds=upper_rounds, lower_rounds=lower_rounds, grand_rounds=grand_rounds,
        team_logos=team_logos, user_predictions=user_predictions,
        total_score=total_score, correct_picks=correct_picks,
        total_picks=total_picks, user_rank=user_rank,
        logged_in=("user_id" in session),
        is_admin=(session.get("username") == "ADMIN"),
        tournament=tournament,
        all_tournaments=get_all_tournaments(),
        current_tournament_id=tournament_id
    )

@app.route("/api/matches")
def api_matches():
    if "user_id" not in session:
        return {"error": "unauthorized"}, 401

    tournament_id = request.args.get("tournament_id") or get_current_tournament_id()
    matches = get_matches_for_tournament(tournament_id)

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Shortname, Logo FROM Team")
    team_logos = {row["Shortname"]: row["Logo"] for row in cursor.fetchall()}
    cursor.close(); conn.close()

    user_predictions = get_user_predictions(session["user_id"], tournament_id)

    serialized = [{
        "match_id": m.get("match_id"), "bracket": m.get("bracket"),
        "round":    m.get("round"),    "team1":   m.get("team1") or "",
        "team2":    m.get("team2") or "", "status": m.get("status") or "upcoming",
        "winner":   m.get("winner") or "", "score":  m.get("score") or "",
        "order":    m.get("order", 0),
    } for m in matches]

    return {"matches": serialized, "logos": team_logos, "user_predictions": user_predictions}


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]; password = request.form["password"]
        conn = get_mysql_connection(); cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM User WHERE Username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'error')
                return render_template('register.html')
            cursor.execute("INSERT INTO User (Username, Password) VALUES (%s, %s)", (username, password))
            conn.commit()
        finally:
            cursor.close(); conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]; password = request.form["password"]
        conn = get_mysql_connection(); cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM User WHERE Username = %s", (username,))
            user = cursor.fetchone()
        finally:
            cursor.close(); conn.close()
        if user and user["Password"] == password:
            session["user_id"] = user["User_id"]; session["username"] = user["Username"]
            next_page = request.args.get("next", "")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("tournaments_page"))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─────────────────────────────────────────────
# ADMIN — TOURNAMENT MANAGEMENT
# ─────────────────────────────────────────────

@app.route("/admin/tournaments")
def admin_tournaments():
    if session.get("username") != "ADMIN":
        return redirect(url_for("index"))
    tournaments = get_all_tournaments()
    conn = get_mysql_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Shortname, Teamname, Region, Logo FROM Team ORDER BY Teamname")
    all_teams = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template(
        "admin_tournaments.html",
        tournaments=tournaments, all_teams=all_teams,
        logged_in=True, is_admin=True,
        all_tournaments=tournaments, current_tournament_id=get_current_tournament_id()
    )

@app.route("/admin/add_team", methods=["POST"])
def admin_add_team():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403
    data = request.json
    name      = data.get("name", "").strip()
    shortname = data.get("shortname", "").strip().upper()
    region    = data.get("region", "").strip()
    logo      = data.get("logo", "").strip()
    if not name or not shortname:
        return {"error": "Name and shortname required"}, 400
    conn = get_mysql_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Shortname FROM Team WHERE Shortname = %s", (shortname,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return {"error": f"Shortname '{shortname}' already exists"}, 409
    cursor.execute(
        "INSERT INTO Team (Teamname, Shortname, Region, Logo) VALUES (%s, %s, %s, %s)",
        (name, shortname, region, logo)
    )
    conn.commit(); cursor.close(); conn.close()
    return {"status": "success", "shortname": shortname}

@app.route("/admin/edit_team", methods=["POST"])
def admin_edit_team():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403
    data = request.json
    shortname = data.get("shortname", "").strip().upper()
    name      = data.get("name", "").strip()
    region    = data.get("region", "").strip()
    logo      = data.get("logo", "").strip()
    conn = get_mysql_connection(); cursor = conn.cursor()
    cursor.execute(
        "UPDATE Team SET Teamname=%s, Region=%s, Logo=%s WHERE Shortname=%s",
        (name, region, logo, shortname)
    )
    conn.commit(); cursor.close(); conn.close()
    return {"status": "success"}

@app.route("/admin/delete_team", methods=["POST"])
def admin_delete_team():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403
    data = request.json
    shortname = data.get("shortname", "").strip().upper()
    conn = get_mysql_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM TeamStats WHERE Shortname=%s", (shortname,))
    cursor.execute("DELETE FROM Team WHERE Shortname=%s", (shortname,))
    conn.commit(); cursor.close(); conn.close()
    return {"status": "success"}

@app.route("/admin/create_tournament", methods=["POST"])
def admin_create_tournament():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403

    data        = request.json
    name        = data.get("name", "").strip()
    date        = data.get("date", "")
    sel_teams   = data.get("teams", [])
    new_teams   = data.get("new_teams", [])

    if not name:
        return {"error": "Tournament name is required"}, 400
    if len(sel_teams) + len(new_teams) != 8:
        return {"error": "Exactly 8 teams required"}, 400

    import re
    tournament_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    t_col = get_mongo_collection("tournaments")
    if t_col.find_one({"tournament_id": tournament_id}):
        tournament_id = f"{tournament_id}-{int(datetime.utcnow().timestamp())}"

    conn = get_mysql_connection(); cursor = conn.cursor()
    # เพิ่มทีมใหม่ใน MySQL
    for nt in new_teams:
        try:
            cursor.execute("""
                INSERT IGNORE INTO Team (Teamname, Shortname, Region, Logo)
                VALUES (%s, %s, %s, %s)
            """, (nt["name"], nt["shortname"], nt.get("region", ""), nt.get("logo", "")))
        except Exception as e:
            print("Error inserting new team:", e)
    conn.commit()

    all_shorts = sel_teams + [nt["shortname"] for nt in new_teams]
    for short in all_shorts:
        cursor.execute("""
            INSERT IGNORE INTO TeamStats (Tournament_id, Shortname, Wins, Losses, Points)
            VALUES (%s, %s, 0, 0, 0)
        """, (tournament_id, short))
    conn.commit(); cursor.close(); conn.close()

    t_col.insert_one({
        "tournament_id": tournament_id,
        "name": name, "date": date,
        "is_active": False, "teams": all_shorts,
        "created_at": datetime.utcnow()
    })
    create_tournament_bracket(tournament_id)

    return {"status": "success", "tournament_id": tournament_id, "name": name}

@app.route("/admin/set_active_tournament", methods=["POST"])
def admin_set_active_tournament():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403
    data = request.json
    tournament_id = data.get("tournament_id")
    force = data.get("force")  # "on" | "off" | None (toggle)
    t_col = get_mongo_collection("tournaments")
    t = t_col.find_one({"tournament_id": tournament_id})
    if not t:
        return {"error": "Not found"}, 404
    if force == "on":
        new_state = True
    elif force == "off":
        new_state = False
    else:
        new_state = not t.get("is_active", False)
    t_col.update_one({"tournament_id": tournament_id}, {"$set": {"is_active": new_state}})
    return {"status": "success", "is_active": new_state}

@app.route("/admin/delete_tournament", methods=["POST"])
def admin_delete_tournament():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403
    tournament_id = request.json.get("tournament_id")
    if tournament_id == "vct-2026":
        return {"error": "Cannot delete the default tournament"}, 400
    get_mongo_collection("pickem_matches").delete_many({"tournament_id": tournament_id})
    get_mongo_collection("tournaments").delete_one({"tournament_id": tournament_id})
    conn = get_mysql_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM TeamStats WHERE Tournament_id = %s", (tournament_id,))
    cursor.execute("DELETE FROM Pickem_DATA WHERE Tournament_id = %s", (tournament_id,))
    conn.commit(); cursor.close(); conn.close()
    return {"status": "success"}


# ─────────────────────────────────────────────
# ADMIN — MATCH MANAGEMENT
# ─────────────────────────────────────────────

@app.route("/admin/update_match", methods=["POST"])
def admin_update_match():
    if session.get("username") != "ADMIN":
        return {"error": "unauthorized"}, 403

    data          = request.json
    col           = get_mongo_collection("pickem_matches")
    match_id      = data.get("match_id")
    team1         = data.get("team1")
    team2         = data.get("team2")
    score         = data.get("score")
    winner        = data.get("winner")
    tournament_id = data.get("tournament_id") or get_current_tournament_id()

    current_match = col.find_one({"match_id": match_id, "tournament_id": tournament_id})
    if not current_match:
        return {"error": "Match not found"}, 404

    already_completed = current_match.get("status") == "completed"
    resolved_t1 = team1 if team1 else current_match.get("team1")
    resolved_t2 = team2 if team2 else current_match.get("team2")

    if score and winner and (not resolved_t1 or not resolved_t2):
        return {"error": "Both teams must be assigned before submitting a result"}, 400

    update_fields = {
        "team1": resolved_t1, "team2": resolved_t2,
        "status": data.get("status", "upcoming")
    }
    if score and winner:
        update_fields.update({"score": score, "winner": winner, "status": "completed"})

    col.update_one({"match_id": match_id, "tournament_id": tournament_id}, {"$set": update_fields})

    # อัปเดต TeamStats
    if score and winner and not already_completed:
        loser = resolved_t2 if resolved_t1 == winner else resolved_t1
        if winner and loser:
            conn = get_mysql_connection(); cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO TeamStats (Tournament_id, Shortname, Wins, Losses, Points)
                    VALUES (%s, %s, 1, 0, 3)
                    ON DUPLICATE KEY UPDATE Wins = Wins + 1, Points = Points + 3
                """, (tournament_id, winner))
                cursor.execute("""
                    INSERT INTO TeamStats (Tournament_id, Shortname, Wins, Losses, Points)
                    VALUES (%s, %s, 0, 1, 0)
                    ON DUPLICATE KEY UPDATE Losses = Losses + 1
                """, (tournament_id, loser))
                conn.commit()
            except Exception as e:
                print("DB ERROR:", e)
            finally:
                cursor.close(); conn.close()

    # Propagate
    updated = col.find_one({"match_id": match_id, "tournament_id": tournament_id})
    if score and winner and updated:
        loser = updated["team2"] if updated["team1"] == winner else updated["team1"]
        for field_key, next_key in [("next_win", winner), ("next_lose", loser)]:
            next_id = updated.get(field_key)
            team_val = next_key
            if next_id and team_val:
                nxt = col.find_one({"match_id": next_id, "tournament_id": tournament_id})
                if nxt:
                    tf = "team1" if not nxt.get("team1") else ("team2" if not nxt.get("team2") else None)
                    if tf:
                        col.update_one({"match_id": next_id, "tournament_id": tournament_id},
                                       {"$set": {tf: team_val, "status": "upcoming"}})

    return {"status": "success"}

@app.route("/results")
def results_page():
    if session.get("username") != "ADMIN":
        return redirect(url_for("index"))
    tournament_id = get_current_tournament_id()
    return render_template("results.html",
        results=get_matches_for_tournament(tournament_id) if tournament_id else [],
        logged_in=True, is_admin=True)


if __name__ == '__main__':
    seed_bracket()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)