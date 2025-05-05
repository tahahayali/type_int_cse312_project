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
    """
    Unlock an achievement for a user and record the unlock date.
    Returns True if this was a new unlock, False if already unlocked.
    """
    # Check if achievement is already unlocked
    user = users.find_one(
        {"username": username, f"achievements.{achievement_name}.unlocked": True}
    )

    if user:
        print(f"Achievement {achievement_name} already unlocked for {username}")
        return False  # Already unlocked

    # Unlock the achievement with timestamp
    now = datetime.now()
    print(f"Unlocking achievement {achievement_name} for {username}")
    result = users.update_one(
        {"username": username},
        {"$set": {
            f"achievements.{achievement_name}.unlocked": True,
            f"achievements.{achievement_name}.unlockDate": now
        }}
    )

    print(f"Unlock result for {username}.{achievement_name}: modified count = {result.modified_count}")
    return result.modified_count > 0  # True if newly unlocked

def initialize_player_stats(username):
    """Ensure every new user has the base stats fields."""
    users.update_one(
        {"username": username},
        {"$setOnInsert": {
            "time_as_it": 0,
            "achievements": {
                "first_tag": {
                    "unlocked": False,
                    "name": "First Tag",
                    "description": "Tag another player for the first time"
                },
                "survivor_10min": {
                    "unlocked": False,
                    "name": "10-Minute Survivor",
                    "description": "Stay as 'it' for 10 minutes total"
                },
                "survivor_1hour": {
                    "unlocked": False,
                    "name": "Ultimate Survivor",
                    "description": "Stay as 'it' for 1 hour total"
                }
            },
            # ───────── new fields ─────────
            "totalTags": 0,
            "totalTimeIt": 0
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
    """
    Atomically bump the totalTimeIt counter and check for time-based achievements.
    Returns a list of newly unlocked achievements, if any.
    """
    print(f"Incrementing time for {username} by {seconds} seconds")

    # Update the time counter
    users.update_one(
        {"username": username},
        {"$inc": {"totalTimeIt": seconds}}
    )

    # Get the updated user data
    user = users.find_one({"username": username})
    if not user:
        print(f"User {username} not found")
        return []

    total_time = user.get("totalTimeIt", 0)
    print(f"User {username} total time: {total_time} seconds")
    unlocked = []

    # Check for time-based achievements
    if total_time >= 10:  # 10 minutes (600 seconds)
        print(f"User {username} qualifies for 10-minute achievement")
        if unlock_achievement(username, "survivor_10min"):
            print(f"Unlocked 10-minute achievement for {username}")
            unlocked.append("survivor_10min")

    if total_time >= 30:  # 1 hour (3600 seconds)
        print(f"User {username} qualifies for 1-hour achievement")
        if unlock_achievement(username, "survivor_1hour"):
            print(f"Unlocked 1-hour achievement for {username}")
            unlocked.append("survivor_1hour")

    print(f"Achievements unlocked for {username}: {unlocked}")
    return unlocked

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

def get_user_achievements(username):
    """
    Get all achievements for a user
    """
    user = users.find_one({"username": username}, {"_id": 0, "achievements": 1})
    if user and "achievements" in user:
        return user["achievements"]
    return {}