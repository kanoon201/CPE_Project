from db import get_mongo_collection

BRACKET_TEMPLATE = [
    # ===== Upper Quarterfinals =====
    {"match_id": "UQF1", "round": "Upper Quarterfinals", "bracket": "upper",
     "team1": None, "team2": None, "team1_src": None, "team2_src": None,
     "bo": "BO3", "status": "pending", "next_win": "USF1", "next_lose": "LR1_1"},
    {"match_id": "UQF2", "round": "Upper Quarterfinals", "bracket": "upper",
     "team1": None, "team2": None, "team1_src": None, "team2_src": None,
     "bo": "BO3", "status": "pending", "next_win": "USF1", "next_lose": "LR1_1"},
    {"match_id": "UQF3", "round": "Upper Quarterfinals", "bracket": "upper",
     "team1": None, "team2": None, "team1_src": None, "team2_src": None,
     "bo": "BO3", "status": "pending", "next_win": "USF2", "next_lose": "LR1_2"},
    {"match_id": "UQF4", "round": "Upper Quarterfinals", "bracket": "upper",
     "team1": None, "team2": None, "team1_src": None, "team2_src": None,
     "bo": "BO3", "status": "pending", "next_win": "USF2", "next_lose": "LR1_2"},

    # ===== Upper Semifinals =====
    {"match_id": "USF1", "round": "Upper Semifinals", "bracket": "upper",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "UQF1"}, "team2_src": {"type": "win", "from": "UQF2"},
     "bo": "BO3", "status": "pending", "next_win": "UF", "next_lose": "LR2_1"},
    {"match_id": "USF2", "round": "Upper Semifinals", "bracket": "upper",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "UQF3"}, "team2_src": {"type": "win", "from": "UQF4"},
     "bo": "BO3", "status": "pending", "next_win": "UF", "next_lose": "LR2_2"},

    # ===== Upper Final =====
    {"match_id": "UF", "round": "Upper Final", "bracket": "upper",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "USF1"}, "team2_src": {"type": "win", "from": "USF2"},
     "bo": "BO5", "status": "pending", "next_win": "GF", "next_lose": "LF"},

    # ===== Lower Round 1 =====
    {"match_id": "LR1_1", "round": "Lower Round 1", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "lose", "from": "UQF1"}, "team2_src": {"type": "lose", "from": "UQF2"},
     "bo": "BO3", "status": "pending", "next_win": "LR2_1"},
    {"match_id": "LR1_2", "round": "Lower Round 1", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "lose", "from": "UQF3"}, "team2_src": {"type": "lose", "from": "UQF4"},
     "bo": "BO3", "status": "pending", "next_win": "LR2_2"},

    # ===== Lower Round 2 =====
    {"match_id": "LR2_1", "round": "Lower Round 2", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "LR1_1"}, "team2_src": {"type": "lose", "from": "USF1"},
     "bo": "BO3", "status": "pending", "next_win": "LR3"},
    {"match_id": "LR2_2", "round": "Lower Round 2", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "LR1_2"}, "team2_src": {"type": "lose", "from": "USF2"},
     "bo": "BO3", "status": "pending", "next_win": "LR3"},

    # ===== Lower Round 3 =====
    {"match_id": "LR3", "round": "Lower Round 3", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "LR2_1"}, "team2_src": {"type": "win", "from": "LR2_2"},
     "bo": "BO3", "status": "pending", "next_win": "LF"},

    # ===== Lower Final =====
    {"match_id": "LF", "round": "Lower Final", "bracket": "lower",
     "team1": None, "team2": None,
     "team1_src": {"type": "lose", "from": "UF"}, "team2_src": {"type": "win", "from": "LR3"},
     "bo": "BO5", "status": "pending", "next_win": "GF"},

    # ===== Grand Final =====
    {"match_id": "GF", "round": "Grand Final", "bracket": "grand",
     "team1": None, "team2": None,
     "team1_src": {"type": "win", "from": "UF"}, "team2_src": {"type": "win", "from": "LF"},
     "bo": "BO5", "status": "pending"},
]


def seed_bracket():
    """Seed the default VCT 2026 tournament on first run."""
    col = get_mongo_collection("pickem_matches")
    t_col = get_mongo_collection("tournaments")

    if col is None or t_col is None:
        print("❌ MongoDB connection failed")
        return

    # ── MIGRATION: tournaments เก่าที่ใช้ status → แปลงเป็น is_active ──
    t_old = list(t_col.find({"status": {"$exists": True}, "is_active": {"$exists": False}}))
    if t_old:
        print(f"🔄 Migrating {len(t_old)} tournaments status → is_active")
        for t in t_old:
            t_col.update_one(
                {"tournament_id": t["tournament_id"]},
                {"$set": {"is_active": t.get("status") == "active"}, "$unset": {"status": ""}}
            )

    # ── MIGRATION: matches เก่าที่ไม่มี tournament_id → ใส่ vct-2026 ให้ ──
    old_matches = list(col.find({"tournament_id": {"$exists": False}, "match_id": {"$exists": True}}))
    if old_matches:
        print(f"🔄 Migrating {len(old_matches)} legacy matches → tournament_id: vct-2026")
        col.update_many(
            {"tournament_id": {"$exists": False}, "match_id": {"$exists": True}},
            {"$set": {"tournament_id": "vct-2026"}}
        )

    # ถ้ามี tournament อยู่แล้ว ไม่ต้อง seed ซ้ำ
    if t_col.count_documents({"tournament_id": "vct-2026"}) > 0:
        print("⚠️  Default tournament already exists, skipping seed")
        return

    # สร้าง tournament document
    t_col.insert_one({
        "tournament_id": "vct-2026",
        "name": "VCT 2026",
        "date": "2026-01-01",
        "is_active": True,
        "teams": ["NRG", "FNC", "DRX", "PRX", "MIBR", "TH", "G2", "FS"]
    })

    # สร้าง matches โดยเพิ่ม tournament_id ใน match_id เพื่อไม่ให้ชน
    import copy
    matches = []
    for m in BRACKET_TEMPLATE:
        doc = copy.deepcopy(m)
        doc["tournament_id"] = "vct-2026"
        matches.append(doc)

    col.insert_many(matches)
    print(f"✅ Seeded VCT 2026 with {len(matches)} matches")


def create_tournament_bracket(tournament_id):
    """สร้าง bracket ใหม่สำหรับ tournament ที่ระบุ"""
    import copy
    col = get_mongo_collection("pickem_matches")
    if col is None:
        return False

    matches = []
    for m in BRACKET_TEMPLATE:
        doc = copy.deepcopy(m)
        doc["tournament_id"] = tournament_id
        matches.append(doc)

    col.insert_many(matches)
    print(f"✅ Created bracket for tournament: {tournament_id} ({len(matches)} matches)")
    return True


if __name__ == "__main__":
    seed_bracket()