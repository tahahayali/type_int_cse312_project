FROM python:3.8-slim

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install app dependencies
RUN pip install --no-cache-dir -r requirements.txt
# You already installed PyJWT in requirements.txt, no need to separately pip install here

# Copy the rest of the application code
COPY . .

# Expose port 8080 for Flask / Gunicorn
EXPOSE 8080

# We will let docker-compose.yml control the startup command (gunicorn with eventlet)
# So NO CMD here
