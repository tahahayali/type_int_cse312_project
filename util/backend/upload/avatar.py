import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
from util.backend.logger import logging
from datetime import datetime, timezone

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
AVATAR_DIR = os.path.join("static", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)

# Maximum allowed size (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB in bytes

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
        # Check file size
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)  # Reset stream position

        if file_length > MAX_FILE_SIZE:
            return jsonify({"error": "File too large. Max 5MB allowed."}), 400

        try:
            filename = secure_filename(username + ".png")  # Always save as .png
            filepath = os.path.join(AVATAR_DIR, filename)

            # Open and center-crop to square
            image = Image.open(file.stream).convert("RGBA")
            cropped = ImageOps.fit(image, (128, 128), Image.LANCZOS, centering=(0.5, 0.5))
            cropped.save(filepath, format='PNG')

            # Log it
            timestamp = datetime.now(timezone.utc).isoformat()
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            logging.info(f"[{timestamp}] {ip} UPLOAD avatar for '{username}' -> {filename}")

            return jsonify({"success": True, "avatar_url": f"/static/avatars/{filename}"})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Invalid file type"}), 400
