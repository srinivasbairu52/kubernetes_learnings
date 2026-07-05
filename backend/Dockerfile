# Use a lightweight Python image
FROM python:3.13-slim

# Prevent Python from buffering output
ENV PYTHONUNBUFFERED=1

# Working directory inside the container
WORKDIR /app

# Copy dependency file first (better Docker layer caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source
COPY . .

# Flask listens on port 5000
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]