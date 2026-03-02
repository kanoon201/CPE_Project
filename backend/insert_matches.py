from db import get_mongo_collection

col = get_mongo_collection("pickem_matches")

col.delete_many({})  # Clear existing matches

matches = [
    {"match_id": "match_001", "team1": "NRG",  "team2": "FNC",  "status": "upcoming", "order": 1},
    {"match_id": "match_002", "team1": "DRX",  "team2": "PRX",  "status": "upcoming", "order": 2},
    {"match_id": "match_003", "team1": "MIBR", "team2": "TH",   "status": "upcoming", "order": 3},
    {"match_id": "match_004", "team1": "G2",   "team2": "FS",   "status": "upcoming", "order": 4},
    {"match_id": "match_005", "team1": "NRG",  "team2": "DRX",  "status": "upcoming", "order": 5},
]

col.insert_many(matches)
print("✅ Matches inserted!")