# Base image
FROM python:3.11-slim

# Setup working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY docker/inference/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the inference server to the working directory
COPY docker/inference/server.py ./server.py

# Declare the volume mount point for models and logs
VOLUME ["/app/models", "/app/logs"]

# Expose Flask port
EXPOSE 8080

# Run the server
CMD ["python", "server.py"]
