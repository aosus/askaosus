FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libolm-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Copy source code
COPY src/ ./src/
COPY system_prompt.md .

# Create non-root user
RUN useradd -m -u 1000 askaosus && \
    chown -R askaosus:askaosus /app

# Switch to non-root user
USER askaosus

# Expose no ports (Matrix bot doesn't need to listen)

# Run the bot
CMD ["python", "-m", "src.main"]
