"""
Database Repository - Data access layer for all database operations.
"""
import datetime
from typing import Optional
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import async_session
from app.database.models import User, Conversation, Alert, Document


class UserRepository:
    """Handles all user-related database operations."""

    @staticmethod
    async def get_or_create_user(telegram_id: int, first_name: str = None,
                                  last_name: str = None, username: str = None) -> User:
        """Get existing user or create a new one."""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    telegram_id=telegram_id,
                    first_name=first_name,
                    last_name=last_name,
                    telegram_username=username,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

            return user

    @staticmethod
    async def update_user(telegram_id: int, **kwargs) -> Optional[User]:
        """Update user fields."""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.updated_at = datetime.datetime.utcnow()
                await session.commit()
                await session.refresh(user)
            return user

    @staticmethod
    async def get_user(telegram_id: int) -> Optional[User]:
        """Get user by telegram ID."""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def update_last_active(telegram_id: int):
        """Update user's last active timestamp."""
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    last_active=datetime.datetime.utcnow(),
                    message_count=User.message_count + 1
                )
            )
            await session.commit()

    @staticmethod
    async def get_all_users_with_briefing() -> list[User]:
        """Get all users with briefing enabled."""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(
                    User.briefing_enabled == True,
                    User.is_onboarded == True
                )
            )
            return result.scalars().all()


class ConversationRepository:
    """Handles conversation history storage and retrieval."""

    @staticmethod
    async def save_message(telegram_id: int, user_id: int, role: str, content: str,
                           message_type: str = "text", intent: str = None,
                           entities: dict = None):
        """Save a conversation message."""
        async with async_session() as session:
            msg = Conversation(
                user_id=user_id,
                telegram_id=telegram_id,
                role=role,
                content=content,
                message_type=message_type,
                intent=intent,
                entities=entities or {},
            )
            session.add(msg)
            await session.commit()

    @staticmethod
    async def get_recent_history(telegram_id: int, limit: int = 20) -> list[Conversation]:
        """Get recent conversation history for context."""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.telegram_id == telegram_id)
                .order_by(desc(Conversation.created_at))
                .limit(limit)
            )
            messages = result.scalars().all()
            return list(reversed(messages))  # Oldest first

    @staticmethod
    async def get_conversation_count(telegram_id: int) -> int:
        """Get total conversation count for a user."""
        async with async_session() as session:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.telegram_id == telegram_id)
            )
            return len(result.scalars().all())


class AlertRepository:
    """Handles price alert operations."""

    @staticmethod
    async def create_alert(telegram_id: int, user_id: int, alert_type: str,
                           ticker: str = None, condition_value: float = None,
                           description: str = None) -> Alert:
        """Create a new alert."""
        async with async_session() as session:
            alert = Alert(
                user_id=user_id,
                telegram_id=telegram_id,
                alert_type=alert_type,
                ticker=ticker,
                condition_value=condition_value,
                description=description,
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert

    @staticmethod
    async def get_active_alerts(telegram_id: int = None) -> list[Alert]:
        """Get active alerts, optionally filtered by user."""
        async with async_session() as session:
            query = select(Alert).where(Alert.is_active == True)
            if telegram_id:
                query = query.where(Alert.telegram_id == telegram_id)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def trigger_alert(alert_id: int):
        """Mark an alert as triggered."""
        async with async_session() as session:
            await session.execute(
                update(Alert)
                .where(Alert.id == alert_id)
                .values(
                    is_triggered=True,
                    is_active=False,
                    triggered_at=datetime.datetime.utcnow()
                )
            )
            await session.commit()


class DocumentRepository:
    """Handles document storage operations."""

    @staticmethod
    async def save_document(telegram_id: int, user_id: int, filename: str,
                            file_type: str, file_path: str, file_size: int = None,
                            extracted_text: str = None) -> Document:
        """Save a document record."""
        async with async_session() as session:
            doc = Document(
                user_id=user_id,
                telegram_id=telegram_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size=file_size,
                extracted_text=extracted_text,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc

    @staticmethod
    async def get_recent_documents(telegram_id: int, limit: int = 5) -> list[Document]:
        """Get recently uploaded documents."""
        async with async_session() as session:
            result = await session.execute(
                select(Document)
                .where(Document.telegram_id == telegram_id)
                .order_by(desc(Document.created_at))
                .limit(limit)
            )
            return result.scalars().all()
