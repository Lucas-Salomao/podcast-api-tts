"""
GCP Cloud Storage service for audio file management.
"""

import os
import uuid
import logging
from datetime import timedelta
from google.cloud import storage

logger = logging.getLogger(__name__)


class StorageService:
    """Service for uploading and managing audio files in GCS."""
    
    def __init__(self):
        self._client = None
        self._bucket = None
        self._bucket_name = os.getenv("BUCKET_AUDIOS", "")
    
    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCS client."""
        if self._client is None:
            self._client = storage.Client()
            logger.info("[STORAGE] GCS client initialized")
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Get the configured bucket."""
        if self._bucket is None:
            if not self._bucket_name:
                raise ValueError("BUCKET_AUDIOS environment variable not set")
            self._bucket = self.client.bucket(self._bucket_name)
            logger.info(f"[STORAGE] Using bucket: {self._bucket_name}")
        return self._bucket
    
    def upload_audio(self, audio_bytes: bytes, user_id: str, filename: str = None) -> tuple[str, str]:
        """
        Upload audio file to GCS bucket.
        
        Args:
            audio_bytes: The audio data in bytes
            user_id: User ID for organizing files
            filename: Optional custom filename
            
        Returns:
            Tuple of (public_url, blob_path) for storage
        """
        if filename is None:
            filename = f"{uuid.uuid4()}.wav"
        
        # Organize by user_id/filename
        blob_path = f"podcasts/{user_id}/{filename}"
        
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(
            audio_bytes,
            content_type="audio/wav",
        )
        
        logger.info(f"[STORAGE] Uploaded audio to gs://{self._bucket_name}/{blob_path}")
        
        # Return both the public URL and the path for signed URL generation
        public_url = f"https://storage.googleapis.com/{self._bucket_name}/{blob_path}"
        
        return public_url, blob_path
    
    def get_signed_url(self, blob_path: str, expiration_hours: int = 1) -> str:
        """
        Generate a signed URL for private bucket access.
        Uses IAM signing for Cloud Run compatibility.
        
        Args:
            blob_path: Path to the blob in the bucket
            expiration_hours: How long the URL should be valid
            
        Returns:
            Signed URL for accessing the audio file
        """
        import google.auth
        from google.auth import compute_engine
        from google.auth.transport import requests
        
        blob = self.bucket.blob(blob_path)
        
        # Get credentials and request object for IAM signing
        auth_request = requests.Request()
        credentials, project = google.auth.default()
        
        # Refresh credentials to get the service account email
        credentials.refresh(auth_request)
        
        # Get service account email from metadata
        service_account_email = getattr(credentials, 'service_account_email', None)
        
        if service_account_email:
            # Use IAM signing (works on Cloud Run)
            signing_credentials = compute_engine.IDTokenCredentials(
                auth_request,
                target_audience="",
                service_account_email=service_account_email,
            )
            
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiration_hours),
                method="GET",
                service_account_email=service_account_email,
                access_token=credentials.token,
            )
        else:
            # Fallback for local development with service account key
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiration_hours),
                method="GET",
            )
        
        logger.debug(f"[STORAGE] Generated signed URL for {blob_path}")
        return url
    
    def delete_audio(self, blob_path: str) -> bool:
        """
        Delete an audio file from GCS.
        
        Args:
            blob_path: Path to the blob to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            blob = self.bucket.blob(blob_path)
            blob.delete()
            logger.info(f"[STORAGE] Deleted audio: {blob_path}")
            return True
        except Exception as e:
            logger.warning(f"[STORAGE] Failed to delete {blob_path}: {e}")
            return False


# Singleton instance
storage_service = StorageService()
