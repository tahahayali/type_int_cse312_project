FROM python:3.8

# Set working directory
WORKDIR /app

# Copy requirements file first
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Flask port
EXPOSE 8080

# Run the application
CMD ["python", "server.py"]