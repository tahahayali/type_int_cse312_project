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

client = MongoClient("mongodb://mongo:27017/")
db = client["tag_game"]

users          = db["users"]
sessions       = db["sessions"]
login_attempts = db["loginAttempts"]
stats          = db["stats"]  # you may repurpose or drop this
leaderboard    = db["leaderboard"]

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

def update_leaderboard(username, new_streak):
    """
    Update the leaderboard to store the user's longest streak.
    Only updates if new_streak is higher.
    """
    leaderboard.update_one(
        {"user": username},
        {"$max": {"longestStreak": new_streak}},
        upsert=True
    )

def get_leaderboard(limit=10):
    """
    Return a sorted list of top users by longestStreak.
    """
    return list(
        leaderboard.find({}, {"_id": 0}).sort("longestStreak", -1).limit(limit)
    )

def get_aggregated_leaderboard(limit=50):
    """
    Return leaderboard using MongoDB aggregation:
    - Top users with totalTags, totalTimeIt
    - Computed field: tagsPerMinute
    """
    pipeline = [
        {
            "$project": {
                "_id": 0,
                "username": 1,
                "totalTags": 1,
                "totalTimeIt": 1,
                "tagsPerMinute": {
                    "$cond": [
                        {"$eq": ["$totalTimeIt", 0]},
                        0,
                        {"$multiply": [{"$divide": ["$totalTags", "$totalTimeIt"]}, 60]}
                    ]
                }
            }
        },
        {"$sort": {"totalTimeIt": 1}},  # Sort by least time as "it"
        {"$limit": limit}
    ]

    return list(users.aggregate(pipeline))
