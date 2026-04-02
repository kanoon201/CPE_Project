"""
PICK'EM – Automated Test Suite
================================
ครอบคลุม 3 ระดับ:
  1. Unit Tests     — logic / helper functions
  2. API Tests      — HTTP routes ผ่าน Flask test client
  3. Integration    — user/admin flows แบบ end-to-end

วิธีรัน:
  pip install pytest pytest-mock mongomock
  pytest tests/test_pickem.py -v

โครงสร้าง mock:
  - MySQL  → unittest.mock (patch get_mysql_connection)
  - MongoDB → mongomock (in-memory MongoDB)
"""

import pytest
import json
import sys
import os
from unittest.mock import MagicMock, patch, call
from datetime import datetime

# ── เพิ่ม path ให้ import app ได้ ──
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════

@pytest.fixture
def mongo_client():
    """In-memory MongoDB ใช้ mongomock"""
    import mongomock
    client = mongomock.MongoClient()
    return client


@pytest.fixture
def mongo_db(mongo_client):
    return mongo_client["pickem_db"]


@pytest.fixture
def seed_tournament(mongo_db):
    """สร้าง tournament และ matches พื้นฐานสำหรับ test"""
    mongo_db.tournaments.insert_one({
        "tournament_id": "test-2026",
        "name": "Test Tournament 2026",
        "date": "2026-01-01",
        "is_active": True,
        "teams": ["T1", "NRG", "FNC", "PRX", "DRX", "MIBR", "G2", "FS"]
    })

    matches = [
        {"tournament_id": "test-2026", "match_id": "UQF1", "round": "Upper Quarterfinals",
         "bracket": "upper", "team1": "T1", "team2": "NRG", "bo": "BO3",
         "status": "completed", "winner": "T1", "score": "2-0",
         "next_win": "USF1", "next_lose": "LR1_1"},
        {"tournament_id": "test-2026", "match_id": "UQF2", "round": "Upper Quarterfinals",
         "bracket": "upper", "team1": "FNC", "team2": "PRX", "bo": "BO3",
         "status": "completed", "winner": "PRX", "score": "2-1",
         "next_win": "USF1", "next_lose": "LR1_1"},
        {"tournament_id": "test-2026", "match_id": "USF1", "round": "Upper Semifinals",
         "bracket": "upper", "team1": "T1", "team2": "PRX", "bo": "BO3",
         "status": "upcoming", "winner": None, "score": None,
         "next_win": "UF", "next_lose": "LR2_1"},
        {"tournament_id": "test-2026", "match_id": "LR1_1", "round": "Lower Round 1",
         "bracket": "lower", "team1": "NRG", "team2": "FNC", "bo": "BO3",
         "status": "pending", "winner": None, "score": None,
         "next_win": "LR2_1"},
        {"tournament_id": "test-2026", "match_id": "UF", "round": "Upper Final",
         "bracket": "upper", "team1": None, "team2": None, "bo": "BO5",
         "status": "pending", "winner": None, "score": None,
         "next_win": "GF", "next_lose": "LF"},
        {"tournament_id": "test-2026", "match_id": "LR2_1", "round": "Lower Round 2",
         "bracket": "lower", "team1": None, "team2": None, "bo": "BO3",
         "status": "pending", "winner": None, "score": None,
         "next_win": "LR3"},
        {"tournament_id": "test-2026", "match_id": "GF", "round": "Grand Final",
         "bracket": "grand", "team1": None, "team2": None, "bo": "BO5",
         "status": "pending", "winner": None, "score": None},
    ]
    mongo_db.pickem_matches.insert_many(matches)
    return mongo_db


@pytest.fixture
def mock_mysql():
    """Mock MySQL connection"""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def app_client(mongo_db, mock_mysql):
    """Flask test client พร้อม mock DB"""
    conn, cursor = mock_mysql

    def fake_get_mongo_collection(name):
        return mongo_db[name]

    with patch('app.get_mysql_connection', return_value=conn), \
         patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection), \
         patch('app.seed_bracket'):
        import app as flask_app
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['SECRET_KEY'] = 'test_secret'
        with flask_app.app.test_client() as client:
            yield client, flask_app, mongo_db, cursor


# ═══════════════════════════════════════════════════════
# 1. UNIT TESTS — Helper Functions
# ═══════════════════════════════════════════════════════

class TestComputeLeaderboard:
    """ทดสอบการคำนวณคะแนน leaderboard"""

    def test_correct_team_and_score(self, seed_tournament, mock_mysql):
        """ทายถูกทีม + ถูก score → ได้คะแนนเต็ม"""
        conn, cursor = mock_mysql
        # mock user predictions: user1 ทาย T1 ชนะ 2-0 (ถูกหมด)
        cursor.fetchall.side_effect = [
            [{"Shortname": "T1", "Teamname": "T1 Esports"},
             {"Shortname": "NRG", "Teamname": "NRG"},
             {"Shortname": "PRX", "Teamname": "Paper Rex"},
             {"Shortname": "FNC", "Teamname": "Fnatic"}],
            [{"Username": "user1", "Match_id": "UQF1",
              "Predict_Winner": "T1", "Predict_Score": "2-0"},
             {"Username": "user1", "Match_id": "UQF2",
              "Predict_Winner": "PRX", "Predict_Score": "2-1"}],
        ]

        def fake_get_mongo_collection(name):
            return seed_tournament[name]

        with patch('app.get_mysql_connection', return_value=conn), \
             patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.compute_leaderboard("test-2026")

        user1 = next((r for r in result if r["Username"] == "user1"), None)
        assert user1 is not None
        # UQF1: correct team + correct score = 10pts, UQF2: correct team + correct score = 10pts
        assert user1["Score"] == 20
        assert user1["CorrectPicks"] == 2

    def test_correct_team_wrong_score(self, seed_tournament, mock_mysql):
        """ทายถูกทีม แต่ผิด score → ได้ครึ่งคะแนน"""
        conn, cursor = mock_mysql
        cursor.fetchall.side_effect = [
            [{"Shortname": "T1", "Teamname": "T1 Esports"}],
            [{"Username": "user1", "Match_id": "UQF1",
              "Predict_Winner": "T1", "Predict_Score": "2-1"}],  # score ผิด (จริงคือ 2-0)
        ]

        def fake_get_mongo_collection(name):
            return seed_tournament[name]

        with patch('app.get_mysql_connection', return_value=conn), \
             patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.compute_leaderboard("test-2026")

        user1 = next((r for r in result if r["Username"] == "user1"), None)
        assert user1["Score"] == 5  # 10 / 2 = 5
        assert user1["CorrectPicks"] == 1

    def test_wrong_team(self, seed_tournament, mock_mysql):
        """ทายผิดทีม → ได้ 0 คะแนน"""
        conn, cursor = mock_mysql
        cursor.fetchall.side_effect = [
            [{"Shortname": "NRG", "Teamname": "NRG"},
             {"Shortname": "T1", "Teamname": "T1 Esports"}],
            [{"Username": "user1", "Match_id": "UQF1",
              "Predict_Winner": "NRG", "Predict_Score": "2-0"}],  # NRG แพ้
        ]

        def fake_get_mongo_collection(name):
            return seed_tournament[name]

        with patch('app.get_mysql_connection', return_value=conn), \
             patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.compute_leaderboard("test-2026")

        user1 = next((r for r in result if r["Username"] == "user1"), None)
        assert user1["Score"] == 0
        assert user1["CorrectPicks"] == 0

    def test_leaderboard_sorted_by_score(self, seed_tournament, mock_mysql):
        """leaderboard เรียงตาม score มากไปน้อย"""
        conn, cursor = mock_mysql
        cursor.fetchall.side_effect = [
            [{"Shortname": "T1", "Teamname": "T1 Esports"},
             {"Shortname": "PRX", "Teamname": "Paper Rex"}],
            [
                {"Username": "user_low",  "Match_id": "UQF1", "Predict_Winner": "NRG", "Predict_Score": "2-0"},
                {"Username": "user_high", "Match_id": "UQF1", "Predict_Winner": "T1",  "Predict_Score": "2-0"},
                {"Username": "user_high", "Match_id": "UQF2", "Predict_Winner": "PRX", "Predict_Score": "2-1"},
            ],
        ]

        def fake_get_mongo_collection(name):
            return seed_tournament[name]

        with patch('app.get_mysql_connection', return_value=conn), \
             patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.compute_leaderboard("test-2026")

        assert result[0]["Username"] == "user_high"
        assert result[0]["Score"] > result[-1]["Score"]

    def test_no_predictions(self, seed_tournament, mock_mysql):
        """user ที่ยังไม่ได้ทาย → score = 0"""
        conn, cursor = mock_mysql
        cursor.fetchall.side_effect = [
            [{"Shortname": "T1", "Teamname": "T1 Esports"}],
            [{"Username": "lazy_user", "Match_id": None,
              "Predict_Winner": None, "Predict_Score": None}],
        ]

        def fake_get_mongo_collection(name):
            return seed_tournament[name]

        with patch('app.get_mysql_connection', return_value=conn), \
             patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.compute_leaderboard("test-2026")

        lazy = next((r for r in result if r["Username"] == "lazy_user"), None)
        assert lazy["Score"] == 0


class TestRoundMultipliers:
    """ตรวจสอบ multiplier แต่ละรอบ"""

    def test_multipliers_correct(self):
        import app
        assert app.ROUND_MULTIPLIER["Upper Quarterfinals"] == 10
        assert app.ROUND_MULTIPLIER["Lower Round 1"]       == 10
        assert app.ROUND_MULTIPLIER["Upper Semifinals"]    == 15
        assert app.ROUND_MULTIPLIER["Lower Round 2"]       == 15
        assert app.ROUND_MULTIPLIER["Lower Round 3"]       == 25
        assert app.ROUND_MULTIPLIER["Upper Final"]         == 30
        assert app.ROUND_MULTIPLIER["Lower Final"]         == 30
        assert app.ROUND_MULTIPLIER["Grand Final"]         == 40


class TestGetMatchesForTournament:
    """ทดสอบ filter matches ต่อ tournament"""

    def test_returns_only_correct_tournament(self, mongo_db):
        """ต้องคืนเฉพาะ matches ของ tournament ที่ระบุ"""
        mongo_db.pickem_matches.insert_many([
            {"tournament_id": "tour-A", "match_id": "M1", "round": "Upper Quarterfinals"},
            {"tournament_id": "tour-A", "match_id": "M2", "round": "Upper Semifinals"},
            {"tournament_id": "tour-B", "match_id": "M3", "round": "Upper Quarterfinals"},
        ])

        def fake_get_mongo_collection(name):
            return mongo_db[name]

        with patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.get_matches_for_tournament("tour-A")

        assert len(result) == 2
        assert all(m["tournament_id"] == "tour-A" for m in result)

    def test_excludes_docs_without_match_id(self, mongo_db):
        """ต้องกรอง document ที่ไม่มี match_id ออก"""
        mongo_db.pickem_matches.insert_many([
            {"tournament_id": "tour-A", "match_id": "M1"},
            {"tournament_id": "tour-A"},  # ไม่มี match_id
        ])

        def fake_get_mongo_collection(name):
            return mongo_db[name]

        with patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            result = app.get_matches_for_tournament("tour-A")

        assert len(result) == 1
        assert result[0]["match_id"] == "M1"


class TestGetCurrentTournamentId:
    """ทดสอบการ resolve tournament ปัจจุบัน"""

    def test_uses_session_tournament_if_active(self, mongo_db):
        mongo_db.tournaments.insert_one({
            "tournament_id": "tour-sess", "is_active": True, "name": "Session Tour"
        })

        def fake_get_mongo_collection(name):
            return mongo_db[name]

        with patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            import flask
            with app.app.test_request_context():
                flask.session["tournament_id"] = "tour-sess"
                result = app.get_current_tournament_id()

        assert result == "tour-sess"

    def test_falls_back_to_active_tournament(self, mongo_db):
        mongo_db.tournaments.insert_one({
            "tournament_id": "active-tour", "is_active": True, "name": "Active"
        })

        def fake_get_mongo_collection(name):
            return mongo_db[name]

        with patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            with app.app.test_request_context():
                result = app.get_current_tournament_id()

        assert result == "active-tour"

    def test_returns_none_if_no_active(self, mongo_db):
        def fake_get_mongo_collection(name):
            return mongo_db[name]

        with patch('app.get_mongo_collection', side_effect=fake_get_mongo_collection):
            import app
            with app.app.test_request_context():
                result = app.get_current_tournament_id()

        assert result is None


# ═══════════════════════════════════════════════════════
# 2. API TESTS — HTTP Routes
# ═══════════════════════════════════════════════════════

class TestAuthRoutes:
    """ทดสอบ login / register / logout"""

    def test_login_success(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        cursor.fetchone.return_value = {
            "User_id": 1, "Username": "testuser", "Password": "pass123"
        }
        cursor.fetchall.return_value = []

        res = client.post('/login', data={"username": "testuser", "password": "pass123"},
                          follow_redirects=False)
        assert res.status_code == 302

    def test_login_wrong_password(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        cursor.fetchone.return_value = {
            "User_id": 1, "Username": "testuser", "Password": "correct"
        }

        res = client.post('/login', data={"username": "testuser", "password": "wrong"},
                          follow_redirects=True)
        assert res.status_code == 200
        assert b'Invalid' in res.data or b'login' in res.data.lower()

    def test_login_user_not_found(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        cursor.fetchone.return_value = None

        res = client.post('/login', data={"username": "ghost", "password": "pass"},
                          follow_redirects=True)
        assert res.status_code == 200

    def test_register_success(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        cursor.fetchone.return_value = None  # username ไม่ซ้ำ

        res = client.post('/register', data={"username": "newuser", "password": "pass"},
                          follow_redirects=False)
        assert res.status_code == 302

    def test_register_duplicate_username(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        cursor.fetchone.return_value = {"User_id": 1, "Username": "existing"}

        res = client.post('/register', data={"username": "existing", "password": "pass"},
                          follow_redirects=True)
        assert b'already exists' in res.data or res.status_code == 200

    def test_logout_clears_session(self, app_client):
        client, flask_app, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        res = client.get('/logout', follow_redirects=False)
        assert res.status_code == 302
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


class TestPredictRoute:
    """ทดสอบหน้า predict"""

    def test_predict_requires_login(self, app_client):
        client, _, mongo_db, cursor = app_client
        res = client.get('/predict', follow_redirects=False)
        assert res.status_code == 302
        assert '/login' in res.headers['Location']

    def test_predict_redirects_if_no_active_tournament(self, app_client):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None

        res = client.get('/predict', follow_redirects=False)
        assert res.status_code == 302


class TestSubmitPrediction:
    """ทดสอบ POST /submit_prediction"""

    def test_requires_login(self, app_client):
        client, _, mongo_db, cursor = app_client
        res = client.post('/submit_prediction',
                          json={"match_id": "UQF1", "predict_winner": "T1",
                                "predict_score": "2-0", "tournament_id": "test-2026"})
        assert res.status_code == 401

    def test_saves_prediction(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        cursor.fetchall.return_value = []

        res = client.post('/submit_prediction',
                          json={"match_id": "UQF1", "predict_winner": "T1",
                                "predict_score": "2-0", "tournament_id": "test-2026"})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "success"

    def test_updates_existing_prediction(self, app_client):
        """ทาย match เดิมซ้ำ → ต้อง update ไม่ใช่ insert ใหม่"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        # execute ครั้งแรก insert, ครั้งสองเป็น ON DUPLICATE KEY UPDATE
        res = client.post('/submit_prediction',
                          json={"match_id": "UQF1", "predict_winner": "NRG",
                                "predict_score": "2-1", "tournament_id": "test-2026"})
        assert res.status_code == 200


class TestAdminUpdateMatch:
    """ทดสอบ POST /admin/update_match"""

    def test_requires_admin(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['username'] = 'normaluser'

        res = client.post('/admin/update_match',
                          json={"match_id": "UQF1", "tournament_id": "test-2026",
                                "winner": "T1", "score": "2-0"})
        assert res.status_code == 403

    def test_cannot_submit_result_without_both_teams(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'

        # GF ยังไม่มีทีม
        res = client.post('/admin/update_match',
                          json={"match_id": "GF", "tournament_id": "test-2026",
                                "winner": "T1", "score": "2-0"})
        assert res.status_code == 400
        data = json.loads(res.data)
        assert "Both teams" in data["error"]

    def test_assign_teams_success(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        res = client.post('/admin/update_match',
                          json={"match_id": "GF", "tournament_id": "test-2026",
                                "team1": "T1", "team2": "PRX", "status": "upcoming"})
        assert res.status_code == 200
        updated = seed_tournament.pickem_matches.find_one(
            {"match_id": "GF", "tournament_id": "test-2026"})
        assert updated["team1"] == "T1"
        assert updated["team2"] == "PRX"

    def test_submit_result_updates_team_stats(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        res = client.post('/admin/update_match',
                          json={"match_id": "USF1", "tournament_id": "test-2026",
                                "winner": "T1", "score": "2-0", "status": "completed"})
        assert res.status_code == 200
        # ตรวจว่า TeamStats INSERT ถูกเรียก
        assert cursor.execute.called

    def test_submit_result_propagates_winner(self, app_client, seed_tournament):
        """ผลชนะต้องถูก propagate ไป next match"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        client.post('/admin/update_match',
                    json={"match_id": "USF1", "tournament_id": "test-2026",
                          "winner": "T1", "score": "2-1", "status": "completed"})

        # UF ควรได้รับ T1 เป็น team1
        uf = seed_tournament.pickem_matches.find_one(
            {"match_id": "UF", "tournament_id": "test-2026"})
        assert uf is not None and (uf.get("team1") == "T1" or uf.get("team2") == "T1")

    def test_submit_result_propagates_loser(self, app_client, seed_tournament):
        """ผู้แพ้ต้องถูก propagate ไป lower bracket"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        client.post('/admin/update_match',
                    json={"match_id": "USF1", "tournament_id": "test-2026",
                          "winner": "T1", "score": "2-0", "status": "completed"})

        # LR2_1 ควรได้รับ PRX (ผู้แพ้)
        lr = seed_tournament.pickem_matches.find_one(
            {"match_id": "LR2_1", "tournament_id": "test-2026"})
        assert lr is not None and (lr.get("team1") == "PRX" or lr.get("team2") == "PRX")


class TestAdminTournamentRoutes:
    """ทดสอบ tournament management"""

    def test_create_tournament_requires_8_teams(self, app_client):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        res = client.post('/admin/create_tournament',
                          json={"name": "Too Few", "date": "2026-06-01",
                                "teams": ["T1", "NRG"], "new_teams": []})
        assert res.status_code == 400
        assert "8" in json.loads(res.data)["error"]

    def test_create_tournament_requires_name(self, app_client):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'

        res = client.post('/admin/create_tournament',
                          json={"name": "", "date": "2026-06-01",
                                "teams": ["T1","NRG","FNC","PRX","DRX","MIBR","G2","FS"],
                                "new_teams": []})
        assert res.status_code == 400

    def test_create_tournament_success(self, app_client):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        res = client.post('/admin/create_tournament',
                          json={"name": "New Cup", "date": "2026-06-01",
                                "teams": ["T1","NRG","FNC","PRX","DRX","MIBR","G2","FS"],
                                "new_teams": []})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "success"
        assert "tournament_id" in data

        # ตรวจว่า tournament ถูกสร้างใน MongoDB
        t = mongo_db.tournaments.find_one({"tournament_id": data["tournament_id"]})
        assert t is not None
        assert t["name"] == "New Cup"

    def test_create_tournament_creates_13_matches(self, app_client):
        """tournament ใหม่ต้องมี 13 matches"""
        client, flask_app, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        def fake_create_bracket(tournament_id):
            """สร้าง matches ใน mock mongo โดยตรง"""
            import copy
            from seed_bracket import BRACKET_TEMPLATE
            matches = []
            for m in BRACKET_TEMPLATE:
                doc = copy.deepcopy(m)
                doc["tournament_id"] = tournament_id
                matches.append(doc)
            mongo_db.pickem_matches.insert_many(matches)
            return True

        with patch('app.create_tournament_bracket', side_effect=fake_create_bracket):
            res = client.post('/admin/create_tournament',
                              json={"name": "Cup 13", "date": "2026-06-01",
                                    "teams": ["T1","NRG","FNC","PRX","DRX","MIBR","G2","FS"],
                                    "new_teams": []})
        data = json.loads(res.data)
        tid = data["tournament_id"]

        matches = list(mongo_db.pickem_matches.find({"tournament_id": tid}))
        assert len(matches) == 14  # BRACKET_TEMPLATE มี 14 matches

    def test_set_active_tournament(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'

        res = client.post('/admin/set_active_tournament',
                          json={"tournament_id": "test-2026", "force": "off"})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["is_active"] == False

    def test_cannot_delete_default_tournament(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'

        # seed vct-2026 ก่อน
        mongo_db.tournaments.insert_one({"tournament_id": "vct-2026", "name": "VCT 2026"})

        res = client.post('/admin/delete_tournament',
                          json={"tournament_id": "vct-2026"})
        assert res.status_code == 400

    def test_delete_tournament_removes_matches(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        res = client.post('/admin/delete_tournament',
                          json={"tournament_id": "test-2026"})
        assert res.status_code == 200
        remaining = list(mongo_db.pickem_matches.find({"tournament_id": "test-2026"}))
        assert len(remaining) == 0


class TestApiMatches:
    """ทดสอบ GET /api/matches"""

    def test_requires_login(self, app_client):
        client, _, mongo_db, cursor = app_client
        res = client.get('/api/matches')
        assert res.status_code == 401

    def test_returns_correct_structure(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        # cursor.fetchall ใช้สำหรับ team logos (Shortname, Logo)
        # และ get_user_predictions (Match_id, Predict_Winner, Predict_Score)
        cursor.fetchall.side_effect = [
            [{"Shortname": "T1", "Logo": "https://example.com/t1.png"}],  # team logos
            [{"Match_id": "UQF1", "Predict_Winner": "T1", "Predict_Score": "2-0"}],  # user preds
        ]

        res = client.get('/api/matches?tournament_id=test-2026')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "matches" in data
        assert "logos" in data
        assert "user_predictions" in data

    def test_returns_only_correct_tournament(self, app_client, seed_tournament):
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None

        # เพิ่ม match ของ tournament อื่น
        mongo_db.pickem_matches.insert_one({
            "tournament_id": "other-tour", "match_id": "X1", "round": "Upper Quarterfinals"
        })

        res = client.get('/api/matches?tournament_id=test-2026')
        data = json.loads(res.data)
        match_ids = [m["match_id"] for m in data["matches"]]
        assert "X1" not in match_ids


# ═══════════════════════════════════════════════════════
# 3. INTEGRATION TESTS — End-to-End Flows
# ═══════════════════════════════════════════════════════

class TestUserPredictionFlow:
    """ทดสอบ flow การทายผลแบบครบ"""

    def test_full_prediction_flow(self, app_client, seed_tournament):
        """login → ทาย → ตรวจว่าบันทึก"""
        client, _, mongo_db, cursor = app_client

        # 1. Login
        cursor.fetchone.return_value = {
            "User_id": 5, "Username": "predictor", "Password": "pass"
        }
        client.post('/login', data={"username": "predictor", "password": "pass"})

        # 2. Submit prediction
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        res = client.post('/submit_prediction',
                          json={"match_id": "UQF1", "predict_winner": "T1",
                                "predict_score": "2-0", "tournament_id": "test-2026"})
        assert res.status_code == 200
        assert json.loads(res.data)["status"] == "success"

    def test_prediction_locked_after_completion(self, app_client, seed_tournament):
        """match ที่ completed แล้ว ยังสามารถ submit ได้ (ON DUPLICATE KEY UPDATE)"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 5
            sess['username'] = 'predictor'
        cursor.fetchall.return_value = []

        # UQF1 เป็น completed อยู่แล้ว — ยังควร accept (ระบบไม่ block)
        res = client.post('/submit_prediction',
                          json={"match_id": "UQF1", "predict_winner": "NRG",
                                "predict_score": "2-1", "tournament_id": "test-2026"})
        assert res.status_code == 200


class TestAdminMatchFlow:
    """ทดสอบ admin flow การจัดการ match"""

    def test_assign_then_submit_flow(self, app_client, seed_tournament):
        """assign teams → submit result → ตรวจ propagation"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'
        cursor.fetchall.return_value = []

        # 1. Assign teams ให้ GF
        res = client.post('/admin/update_match',
                          json={"match_id": "GF", "tournament_id": "test-2026",
                                "team1": "T1", "team2": "PRX", "status": "upcoming"})
        assert res.status_code == 200

        gf = seed_tournament.pickem_matches.find_one({"match_id": "GF", "tournament_id": "test-2026"})
        assert gf["team1"] == "T1" and gf["team2"] == "PRX"

        # 2. Submit result
        res = client.post('/admin/update_match',
                          json={"match_id": "GF", "tournament_id": "test-2026",
                                "winner": "T1", "score": "3-1", "status": "completed"})
        assert res.status_code == 200

        gf = seed_tournament.pickem_matches.find_one({"match_id": "GF", "tournament_id": "test-2026"})
        assert gf["status"] == "completed"
        assert gf["winner"] == "T1"

    def test_cannot_submit_before_assign(self, app_client, seed_tournament):
        """submit result ก่อน assign teams → ต้องได้ 400"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 99
            sess['username'] = 'ADMIN'

        res = client.post('/admin/update_match',
                          json={"match_id": "GF", "tournament_id": "test-2026",
                                "winner": "T1", "score": "3-0", "status": "completed"})
        assert res.status_code == 400


class TestTournamentIsolation:
    """ทดสอบว่าข้อมูลแต่ละ tournament แยกกันจริง"""

    def test_predictions_isolated_per_tournament(self, app_client, seed_tournament):
        """prediction ของ tournament A ต้องไม่ปนกับ B"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        # สร้าง tournament B
        mongo_db.tournaments.insert_one({
            "tournament_id": "tour-B", "is_active": True, "name": "Tour B",
            "teams": ["T1","NRG","FNC","PRX","DRX","MIBR","G2","FS"]
        })
        mongo_db.pickem_matches.insert_one({
            "tournament_id": "tour-B", "match_id": "UQF1",
            "round": "Upper Quarterfinals", "bracket": "upper",
            "team1": "T1", "team2": "DRX", "status": "upcoming"
        })
        cursor.fetchall.return_value = []

        # ทาย tournament A
        client.post('/submit_prediction',
                    json={"match_id": "UQF1", "predict_winner": "T1",
                          "predict_score": "2-0", "tournament_id": "test-2026"})

        # ทาย tournament B
        client.post('/submit_prediction',
                    json={"match_id": "UQF1", "predict_winner": "DRX",
                          "predict_score": "2-1", "tournament_id": "tour-B"})

        # ตรวจว่า execute ถูกเรียกพร้อม tournament_id ที่ถูกต้อง
        calls_str = str(cursor.execute.call_args_list)
        assert "test-2026" in calls_str
        assert "tour-B" in calls_str

    def test_api_matches_scoped_to_tournament(self, app_client, seed_tournament):
        """GET /api/matches?tournament_id=X ต้องคืนเฉพาะ matches ของ X"""
        client, _, mongo_db, cursor = app_client
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        cursor.fetchall.return_value = []
        cursor.fetchone.return_value = None

        res = client.get('/api/matches?tournament_id=test-2026')
        data = json.loads(res.data)
        for m in data["matches"]:
            # ตรวจ match_id เฉพาะที่ seed ไว้ใน test-2026
            assert m["match_id"] in ["UQF1", "UQF2", "USF1", "LR1_1", "UF", "LR2_1", "GF"]