# Base Image must match the Cython compilation version (Python 3.12)
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy dependency list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the compiled .so binaries and launcher run.py
COPY . .

# Expose port 8080 for Reseller API server
EXPOSE 8080

# Disable stdout buffering to see logs instantly
ENV PYTHONUNBUFFERED=1

# Start the bot using launcher
CMD ["python", "run.py"]
