FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies:
# - curl: for healthcheck
# - gcc, python3-dev: for compiling Python extensions
# - portaudio19-dev: required for PyAudio
# - libgl1, libglib2.0-0: required for OpenCV (used by Docling)
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3-dev \
    portaudio19-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Force CPU-only mode for PyTorch
ENV CUDA_VISIBLE_DEVICES=""
ENV TORCH_DEVICE="cpu"

# Set cache directory for Hugging Face models (used by Docling)
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV DOCLING_CACHE_DIR=/app/.cache/docling

# Create cache directories
RUN mkdir -p /app/.cache/huggingface /app/.cache/docling

# Copy and install base dependencies first (better Docker caching)
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy and run the Docling installation script (PyTorch CPU + Docling)
COPY scripts/install_docling.sh ./scripts/
RUN chmod +x ./scripts/install_docling.sh && ./scripts/install_docling.sh

# Copy and run the model download script to pre-cache models
COPY scripts/download_models.py ./scripts/
RUN python scripts/download_models.py

# Copy the rest of the application
COPY . .

# Cloud Run sets the PORT environment variable.
# We default to 8080 if not set, but Cloud Run will inject it.
ENV PORT=8080

EXPOSE ${PORT}

HEALTHCHECK CMD curl --fail http://localhost:${PORT}/ || exit 1

# Use shell form to expand environment variable
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT}"