"""
Script to pre-download Docling models during Docker build.
This ensures models are cached and ready when the container starts.
"""

import os
import sys
import logging

# Force CPU for model download
os.environ["CUDA_VISIBLE_DEVICES"] = ""

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def download_models():
    """Download and cache all Docling models."""
    logger.info("Starting Docling model download...")
    
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        
        # Configure for CPU
        accelerator_options = AcceleratorOptions(
            num_threads=4,
            device="cpu",
        )
        
        pdf_pipeline_options = PdfPipelineOptions(
            accelerator_options=accelerator_options,
        )
        
        logger.info("Initializing DocumentConverter (this will download models)...")
        
        # Initialize converter - this triggers model downloads
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pdf_pipeline_options
                )
            }
        )
        
        logger.info("DocumentConverter initialized successfully!")
        logger.info("All models downloaded and cached.")
        
        # Optionally, do a test conversion to ensure everything works
        logger.info("Models ready for production use.")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download models: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_models()
    sys.exit(0 if success else 1)
