from db import get_mongo_collection

def seed_bracket():
    col = get_mongo_collection("pickem_matches")

    if col is None:
        print("❌ MongoDB connection failed")
        return

    # ลบของเก่าทิ้งก่อน (กัน seed ซ้ำ)
    col.delete_many({})

    base_matches = [
        # ===== Upper Quarterfinals =====
        {
            "match_id": "UQF1",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "USF1",
            "next_lose": "LR1_1"
        },
        {
            "match_id": "UQF2",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "USF1",
            "next_lose": "LR1_1"
        },
        {
            "match_id": "UQF3",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "USF2",
            "next_lose": "LR1_2"
        },
        {
            "match_id": "UQF4",
            "round": "Upper Quarterfinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "USF2",
            "next_lose": "LR1_2"
        },

        # ===== Upper Semifinals =====
        {
            "match_id": "USF1",
            "round": "Upper Semifinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "UF",
            "next_lose": "LR2_1"
        },
        {
            "match_id": "USF2",
            "round": "Upper Semifinals",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "UF",
            "next_lose": "LR2_2"
        },

        # ===== Upper Final =====
        {
            "match_id": "UF",
            "round": "Upper Final",
            "bracket": "upper",
            "team1": None,
            "team2": None,
            "bo": "BO5",
            "status": "pending",
            "next_win": "GF",
            "next_lose": "LF"
        },

        # ===== Lower Round 1 =====
        {
            "match_id": "LR1_1",
            "round": "Lower Round 1",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "LR2_1"
        },
        {
            "match_id": "LR1_2",
            "round": "Lower Round 1",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "LR2_2"
        },

        # ===== Lower Round 2 =====
        {
            "match_id": "LR2_1",
            "round": "Lower Round 2",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "LR3"
        },
        {
            "match_id": "LR2_2",
            "round": "Lower Round 2",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "LR3"
        },

        # ===== Lower Round 3 =====
        {
            "match_id": "LR3",
            "round": "Lower Round 3",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO3",
            "status": "pending",
            "next_win": "LF"
        },

        # ===== Lower Final =====
        {
            "match_id": "LF",
            "round": "Lower Final",
            "bracket": "lower",
            "team1": None,
            "team2": None,
            "bo": "BO5",
            "status": "pending",
            "next_win": "GF"
        },

        # ===== Grand Final =====
        {
            "match_id": "GF",
            "round": "Grand Final",
            "bracket": "grand",
            "team1": None,
            "team2": None,
            "bo": "BO5",
            "status": "pending"
        }
    ]

    col.insert_many(base_matches)
    print(f"✅ Seeded {len(base_matches)} matches into MongoDB")

if __name__ == "__main__":
    seed_bracket()