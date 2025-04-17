# Use an official Python image based on Ubuntu
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy all files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask port
EXPOSE 8080

# Run the app
CMD ["python3", "server.py"]
