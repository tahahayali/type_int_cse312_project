# from pymongo import MongoClient
# from datetime import datetime
#
# client = MongoClient("mongodb://mongo:27017/")
# db = client["tag_game"]
#
# users = db["users"]
# sessions = db["sessions"]
# login_attempts = db["loginAttempts"]
# stats = db["stats"]
#
# def update_user_time_as_it(username, total_seconds):
#     users.update_one(
#         {"username": username},
#         {"$set": {"time_as_it": total_seconds}}
#     )
#
# def unlock_achievement(username, achievement_name):
#     users.update_one(
#         {"username": username},
#         {"$set": {f"achievements.{achievement_name}": True}}
#     )
#
# def initialize_player_stats(username):
#     users.update_one(
#         {"username": username},
#         {"$setOnInsert": {
#             "time_as_it": 0,
#             "achievements": {
#                 "first_tag": False,
#                 "no_tag_win": False,
#                 "longest_chase": False
#             }
#         }}
#     )



from pymongo import MongoClient
from datetime import datetime
import os

MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
client = MongoClient("mongodb://mongo:27017/")
db = client["tag_game"]

users          = db["users"]
sessions       = db["sessions"]
login_attempts = db["loginAttempts"]
stats          = db["stats"]  # you may repurpose or drop this

# ──────────────────────────────────────────────────────────────────────────────
# Existing helper
def update_user_time_as_it(username, total_seconds):
    users.update_one(
        {"username": username},
        {"$set": {"time_as_it": total_seconds}}
    )

def unlock_achievement(username, achievement_name):
    users.update_one(
        {"username": username},
        {"$set": {f"achievements.{achievement_name}": True}}
    )

def initialize_player_stats(username):
    """Ensure every new user has the base stats fields."""
    users.update_one(
        {"username": username},
        {"$setOnInsert": {
            "time_as_it":   0,
            "achievements": {
                "first_tag":    False,
                "no_tag_win":   False,
                "longest_chase":False
            },
            # ───────── new fields ─────────
            "totalTags":    0,
            "totalTimeIt":  0
        }},
        upsert=True
    )
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────── your new, atomic increment helpers ─────────────────────────
def increment_user_tags(username, count=1):
    """Atomically bump the totalTags counter."""
    users.update_one(
        {"username": username},
        {"$inc": {"totalTags": count}}
    )

def increment_user_time(username, seconds):
    """Atomically bump the totalTimeIt counter."""
    users.update_one(
        {"username": username},
        {"$inc": {"totalTimeIt": seconds}}
    )
