# Use an official Python image based on Ubuntu
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy all files into the container
COPY . /app
#COPY ./requirements.txt ./requirements.txt

# Install Python dependencies
#RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt && apt-get update

# Expose the Flask port
EXPOSE 8080

# Run the app
CMD ["python3", "server.py"]
