from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://mongo:27017/")
db = client["tag_game"]

users = db["users"]
sessions = db["sessions"]
login_attempts = db["loginAttempts"]
stats = db["stats"]