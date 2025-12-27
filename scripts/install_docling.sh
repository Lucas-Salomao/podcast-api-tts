#!/bin/bash
# Script to install Docling with CPU-only PyTorch
# This reduces the image size significantly by avoiding CUDA dependencies

set -e

echo "=========================================="
echo "Installing PyTorch CPU-only version..."
echo "=========================================="

# Install PyTorch CPU-only from official index
pip install --no-cache-dir \
    torch \
    torchvision \
    --index-url https://download.pytorch.org/whl/cpu

echo "=========================================="
echo "Installing Docling..."
echo "=========================================="

# Install Docling
pip install --no-cache-dir docling

echo "=========================================="
echo "Installation complete!"
echo "=========================================="

# Verify installation
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import docling; print('Docling imported successfully')"
