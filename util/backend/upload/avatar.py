import os
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image
from util.backend.logger import logging
from datetime import datetime, timezone

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
AVATAR_DIR = os.path.join("static", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['avatar']
    username = request.form.get('username')

    if not username:
        return jsonify({"error": "Missing username"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(username + ".png")  # Always save as .png
            filepath = os.path.join(AVATAR_DIR, filename)

            image = Image.open(file.stream).convert("RGB")
            image = image.resize((128, 128))
            image.save(filepath)

            # Log it
            timestamp = datetime.now(timezone.utc).isoformat()
            ip = request.remote_addr
            logging.info(f"[{timestamp}] {ip} UPLOAD avatar for '{username}' -> {filename}")

            return jsonify({"success": True, "avatar_url": f"/static/avatars/{filename}"})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Invalid file type"}), 400
