from db import get_mongo_collection

def seed_bracket():
    col = get_mongo_collection("pickem_matches")

    if col is None:
        print("❌ MongoDB connection failed")
        return

    # ถ้ามีข้อมูลอยู่แล้ว ไม่ต้อง seed ซ้ำ
    if col.count_documents({}) > 0:
        print("⚠️  Matches already exist, skipping seed")
        return

    base_matches = [
        # ===== Upper Quarterfinals =====
        {
            "match_id": "UQF1",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": None, "team2_src": None,   # None = admin กรอกเอง
            "bo": "BO3", "status": "pending",
            "next_win": "USF1", "next_lose": "LR1_1"
        },
        {
            "match_id": "UQF2",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": None, "team2_src": None,
            "bo": "BO3", "status": "pending",
            "next_win": "USF1", "next_lose": "LR1_1"
        },
        {
            "match_id": "UQF3",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": None, "team2_src": None,
            "bo": "BO3", "status": "pending",
            "next_win": "USF2", "next_lose": "LR1_2"
        },
        {
            "match_id": "UQF4",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": None, "team2_src": None,
            "bo": "BO3", "status": "pending",
            "next_win": "USF2", "next_lose": "LR1_2"
        },

        # ===== Upper Semifinals =====
        # USF1: Winner UQF1 vs Winner UQF2
        {
            "match_id": "USF1",
            "round": "Upper Semifinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "UQF1"},
            "team2_src": {"type": "win", "from": "UQF2"},
            "bo": "BO3", "status": "pending",
            "next_win": "UF", "next_lose": "LR2_1"
        },
        # USF2: Winner UQF3 vs Winner UQF4
        {
            "match_id": "USF2",
            "round": "Upper Semifinals",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "UQF3"},
            "team2_src": {"type": "win", "from": "UQF4"},
            "bo": "BO3", "status": "pending",
            "next_win": "UF", "next_lose": "LR2_2"
        },

        # ===== Upper Final =====
        # UF: Winner USF1 vs Winner USF2
        {
            "match_id": "UF",
            "round": "Upper Final",
            "bracket": "upper",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "USF1"},
            "team2_src": {"type": "win", "from": "USF2"},
            "bo": "BO5", "status": "pending",
            "next_win": "GF", "next_lose": "LF"
        },

        # ===== Lower Round 1 =====
        # LR1_1: Loser UQF1 vs Loser UQF2
        {
            "match_id": "LR1_1",
            "round": "Lower Round 1",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "lose", "from": "UQF1"},
            "team2_src": {"type": "lose", "from": "UQF2"},
            "bo": "BO3", "status": "pending",
            "next_win": "LR2_1"
        },
        # LR1_2: Loser UQF3 vs Loser UQF4
        {
            "match_id": "LR1_2",
            "round": "Lower Round 1",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "lose", "from": "UQF3"},
            "team2_src": {"type": "lose", "from": "UQF4"},
            "bo": "BO3", "status": "pending",
            "next_win": "LR2_2"
        },

        # ===== Lower Round 2 =====
        # LR2_1: Winner LR1_1 vs Loser USF1
        {
            "match_id": "LR2_1",
            "round": "Lower Round 2",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "LR1_1"},
            "team2_src": {"type": "lose", "from": "USF1"},
            "bo": "BO3", "status": "pending",
            "next_win": "LR3"
        },
        # LR2_2: Winner LR1_2 vs Loser USF2
        {
            "match_id": "LR2_2",
            "round": "Lower Round 2",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "LR1_2"},
            "team2_src": {"type": "lose", "from": "USF2"},
            "bo": "BO3", "status": "pending",
            "next_win": "LR3"
        },

        # ===== Lower Round 3 =====
        # LR3: Winner LR2_1 vs Winner LR2_2
        {
            "match_id": "LR3",
            "round": "Lower Round 3",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "LR2_1"},
            "team2_src": {"type": "win", "from": "LR2_2"},
            "bo": "BO3", "status": "pending",
            "next_win": "LF"
        },

        # ===== Lower Final =====
        # LF: Loser UF vs Winner LR3
        {
            "match_id": "LF",
            "round": "Lower Final",
            "bracket": "lower",
            "team1": None, "team2": None,
            "team1_src": {"type": "lose", "from": "UF"},
            "team2_src": {"type": "win", "from": "LR3"},
            "bo": "BO5", "status": "pending",
            "next_win": "GF"
        },

        # ===== Grand Final =====
        # GF: Winner UF vs Winner LF
        {
            "match_id": "GF",
            "round": "Grand Final",
            "bracket": "grand",
            "team1": None, "team2": None,
            "team1_src": {"type": "win", "from": "UF"},
            "team2_src": {"type": "win", "from": "LF"},
            "bo": "BO5", "status": "pending"
        }
    ]

    col.insert_many(base_matches)
    print(f"✅ Seeded {len(base_matches)} matches into MongoDB")

if __name__ == "__main__":
    seed_bracket()