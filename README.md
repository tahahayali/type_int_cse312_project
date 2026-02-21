# type_int_cse312_project
This project is our CSE-312 final project. We'll discuss what we want to do later



# DEPLOYED VERSION:

https://type-int.cse312.dev/




# Tag Royale (CSE 312 Final Project)

**Tag Royale** is a real-time multiplayer **tag** game built for **CSE 312**. Players join a shared arena; one player is **“IT”** (red) and everyone else tries to avoid getting tagged. The game runs live using **WebSockets (Socket.IO)**, with persistent **MongoDB** stats, achievements, and leaderboards.

**Deployed:** https://type-int.cse312.dev/  <!-- update if needed -->  
:contentReference[oaicite:1]{index=1}

---

## What We Built

### Core Gameplay
- Real-time multiplayer movement (server broadcasts player positions)
- Tag mechanic:
  - Only the current “IT” player can be tagged
  - When tagged, “IT” switches to the tagger
  - Cooldown protection prevents instant re-tagging (“grace period”)  
:contentReference[oaicite:2]{index=2}

### Accounts + Security
- Register/Login/Logout API
- Passwords hashed with **bcrypt**
- Sessions authenticated via **JWT stored in HttpOnly cookies**
- Server rejects Socket.IO connections without a valid auth token  
:contentReference[oaicite:3]{index=3}

### Persistence (MongoDB)
Stored per user:
- `totalTags`
- `totalTimeIt`
- longest “IT streak” leaderboard
- achievements + unlock dates  
:contentReference[oaicite:4]{index=4}

### Achievements
- **First Tag**: tag another player once
- **10-Minute Survivor**: total time as IT reaches 10 minutes
- **Ultimate Survivor**: total time as IT reaches 1 hour  
:contentReference[oaicite:5]{index=5}

### Pages / UI
- Home / login / register screen
- Game page (with controls + leaderboard panel)
- Achievements page
- Global leaderboard page
- My stats page
- Upload avatar page  
:contentReference[oaicite:6]{index=6}

### Avatars
- On registration, the server can generate a default avatar using DiceBear (seeded by username)
- Users can upload an image; server crops + resizes to a square and saves as PNG  
:contentReference[oaicite:7]{index=7}

---

## Tech Stack
- **Backend:** Python, Flask  
- **Realtime:** Flask-SocketIO + Eventlet  
- **Database:** MongoDB (pymongo)  
- **Auth:** bcrypt + JWT (PyJWT)  
- **Images:** Pillow  
- **Deploy/Run:** Docker + docker-compose + Gunicorn  
:contentReference[oaicite:8]{index=8}

---

## How It Works (High Level)

### Server
- Flask serves the HTML pages and static assets.
- Socket.IO manages real-time events:
  - `connect`: authenticate user, spawn player, send initial state
  - `move`: update position and broadcast
  - `tag`: validate + swap IT + update timers + update DB + broadcast
  - `disconnect`: finalize timers, write stats, reassign IT if needed  
:contentReference[oaicite:9]{index=9}

### Database
Mongo collections used:
- `users` (accounts, totals, achievements)
- `sessions` (active session tokens + socket id)
- `leaderboard` (longest streak as IT)  
:contentReference[oaicite:10]{index=10}

---

## Running Locally (Docker Recommended)

### 1) Prereqs
- Docker + Docker Compose

### 2) Start
```bash
docker compose up --build

