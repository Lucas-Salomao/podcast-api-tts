"""
Database models for the podcast application.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class Podcast(Base):
    """
    Podcast model for storing generated podcast metadata.
    
    The audio file is stored in GCS bucket, this table stores the metadata
    and the URL to access the audio.
    """
    __tablename__ = "podcasts"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # User identification (from WSO2 SSO)
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    
    # Podcast metadata
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    theme: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )
    
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # GCS storage URL
    audio_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    # Audio file path in bucket (for signed URL generation)
    audio_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    # Composite index for efficient user queries
    __table_args__ = (
        Index("idx_podcasts_user_created", "user_id", "created_at", postgresql_using="btree"),
    )
    
    def __repr__(self) -> str:
        return f"<Podcast(id={self.id}, title='{self.title[:30]}...', user_id='{self.user_id}')>"
