"""
Document processing service using Docling library.
Extracts text content from PDF, DOCX, XLSX, PPTX and TXT files.
"""

import logging
import tempfile
import os
from pathlib import Path
from typing import List, Tuple

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.labels import DocItemLabel

logger = logging.getLogger(__name__)

# Check if CUDA is available, otherwise force CPU
try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    DEVICE = "cpu"

logger.info(f"[DOCUMENT] Using device: {DEVICE}")


class DocumentService:
    """Service for extracting text content from various document formats."""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.pptx', '.txt'}
    
    def __init__(self):
        """Initialize the document converter."""
        self._converter = None
    
    @property
    def converter(self) -> DocumentConverter:
        """Lazy initialization of the converter with CPU-only configuration."""
        if self._converter is None:
            logger.info("[DOCUMENT] Initializing Docling DocumentConverter...")
            
            # Configure accelerator for CPU (or CUDA if available)
            accelerator_options = AcceleratorOptions(
                num_threads=4,
                device=DEVICE,
            )
            
            # Configure PDF pipeline with CPU accelerator
            pdf_pipeline_options = PdfPipelineOptions(
                accelerator_options=accelerator_options,
            )
            
            # Create converter with configured options
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pdf_pipeline_options
                    )
                }
            )
            
            logger.info(f"[DOCUMENT] DocumentConverter initialized with device: {DEVICE}")
        return self._converter
    
    def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Extracts text content from a document file.
        
        Args:
            file_content: Raw bytes of the file
            filename: Original filename (used to determine format)
            
        Returns:
            Extracted text content as string
        """
        extension = Path(filename).suffix.lower()
        
        if extension not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"[DOCUMENT] Unsupported file type: {extension}")
            return ""
        
        # Handle plain text files directly
        if extension == '.txt':
            try:
                return file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return file_content.decode('latin-1')
                except Exception as e:
                    logger.error(f"[DOCUMENT] Failed to decode TXT file: {e}")
                    return ""
        
        # Use Docling for other formats (PDF, DOCX, XLSX, PPTX)
        try:
            # Create temporary file with proper extension
            with tempfile.NamedTemporaryFile(
                suffix=extension, 
                delete=False
            ) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name
            
            try:
                logger.info(f"[DOCUMENT] Converting {filename} using Docling...")
                result = self.converter.convert(tmp_path)
                
                # Export to Markdown for better formatting preservation
                text_content = result.document.export_to_markdown()
                
                logger.info(
                    f"[DOCUMENT] Extracted {len(text_content)} chars from {filename}"
                )
                return text_content
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
        except Exception as e:
            logger.exception(f"[DOCUMENT] Failed to extract from {filename}: {e}")
            return ""
    
    async def process_uploaded_files(
        self, 
        files: List[Tuple[str, bytes]]
    ) -> str:
        """
        Processes multiple uploaded files and combines their content.
        
        Args:
            files: List of (filename, content) tuples
            
        Returns:
            Combined text content from all files
        """
        combined_content = []
        
        for filename, content in files:
            logger.info(f"[DOCUMENT] Processing: {filename}")
            text = self.extract_text(content, filename)
            
            if text.strip():
                combined_content.append(
                    f"\n\n--- Conteúdo do documento: {filename} ---\n{text}"
                )
            else:
                logger.warning(f"[DOCUMENT] No content extracted from: {filename}")
        
        total_files = len(files)
        extracted_files = len(combined_content)
        logger.info(
            f"[DOCUMENT] Processed {extracted_files}/{total_files} files successfully"
        )
        
        return "\n".join(combined_content)


# Singleton instance for import
document_service = DocumentService()
