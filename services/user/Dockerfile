FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    email-validator \
    kafka-python==2.0.2 \
    python-jose==3.3.0 \
    python-multipart \
    passlib[bcrypt]==1.7.4 \
    asyncpg==0.28.0 \
    psycopg2-binary==2.9.7 \
    bcrypt

# Copy application code
COPY . .

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]