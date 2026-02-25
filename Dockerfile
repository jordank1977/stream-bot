FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot.py .

# Create data directory for persistent cache
RUN mkdir /data

# Run the application
CMD ["python", "bot.py"]
