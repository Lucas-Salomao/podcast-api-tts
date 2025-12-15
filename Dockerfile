FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies:
# - curl: for healthcheck
# - gcc, python3-dev: for compiling Python extensions
# - portaudio19-dev: required for PyAudio
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets the PORT environment variable.
# We default to 8080 if not set, but Cloud Run will inject it.
ENV PORT=8080

EXPOSE ${PORT}

HEALTHCHECK CMD curl --fail http://localhost:${PORT}/ || exit 1

# Use shell form to expand environment variable
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT}"