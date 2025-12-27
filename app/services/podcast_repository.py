"""
Repository for Podcast database operations.
"""

import uuid
import logging
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Podcast
from app.db.database import async_session_maker

logger = logging.getLogger(__name__)


class PodcastRepository:
    """Repository for CRUD operations on podcasts."""
    
    async def create(
        self,
        user_id: str,
        title: str,
        theme: str,
        duration_minutes: int,
        audio_url: str,
        audio_path: str,
    ) -> Podcast:
        """
        Create a new podcast record.
        
        Args:
            user_id: WSO2 user ID
            title: Podcast title
            theme: Original theme/topic
            duration_minutes: Duration in minutes
            audio_url: Public URL (may not work for private buckets)
            audio_path: Path in bucket for signed URL generation
            
        Returns:
            Created Podcast instance
        """
        async with async_session_maker() as session:
            podcast = Podcast(
                user_id=user_id,
                title=title,
                theme=theme,
                duration_minutes=duration_minutes,
                audio_url=audio_url,
                audio_path=audio_path,
            )
            session.add(podcast)
            await session.commit()
            await session.refresh(podcast)
            
            logger.info(f"[REPO] Created podcast {podcast.id} for user {user_id}")
            return podcast
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Podcast]:
        """
        List podcasts for a specific user, ordered by creation date (newest first).
        
        Args:
            user_id: WSO2 user ID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Podcast instances
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(Podcast)
                .where(Podcast.user_id == user_id)
                .order_by(Podcast.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            podcasts = result.scalars().all()
            logger.debug(f"[REPO] Found {len(podcasts)} podcasts for user {user_id}")
            return list(podcasts)
    
    async def get_by_id(self, podcast_id: uuid.UUID) -> Optional[Podcast]:
        """
        Get a podcast by its ID.
        
        Args:
            podcast_id: Podcast UUID
            
        Returns:
            Podcast instance or None if not found
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(Podcast).where(Podcast.id == podcast_id)
            )
            podcast = result.scalar_one_or_none()
            return podcast
    
    async def delete(self, podcast_id: uuid.UUID, user_id: str) -> bool:
        """
        Delete a podcast by ID (only if owned by user).
        
        Args:
            podcast_id: Podcast UUID
            user_id: Owner's user ID (for authorization)
            
        Returns:
            True if deleted, False if not found or not authorized
        """
        async with async_session_maker() as session:
            result = await session.execute(
                delete(Podcast)
                .where(Podcast.id == podcast_id)
                .where(Podcast.user_id == user_id)
            )
            await session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"[REPO] Deleted podcast {podcast_id}")
            else:
                logger.warning(f"[REPO] Podcast {podcast_id} not found or not authorized")
            
            return deleted
    
    async def count_by_user(self, user_id: str) -> int:
        """
        Count total podcasts for a user.
        
        Args:
            user_id: WSO2 user ID
            
        Returns:
            Number of podcasts
        """
        async with async_session_maker() as session:
            from sqlalchemy import func
            result = await session.execute(
                select(func.count(Podcast.id)).where(Podcast.user_id == user_id)
            )
            return result.scalar() or 0


# Singleton instance
podcast_repository = PodcastRepository()
