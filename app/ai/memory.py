"""
AI Memory - Conversation context and memory management.
"""
import logging
from typing import Optional
from app.database.repositories import ConversationRepository, UserRepository
from app.database.models import User

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation context for AI interactions."""

    @staticmethod
    async def get_context(telegram_id: int, limit: int = 20) -> str:
        """Get formatted conversation history for AI context."""
        messages = await ConversationRepository.get_recent_history(telegram_id, limit)

        if not messages:
            return "No previous conversation history."

        formatted = []
        for msg in messages:
            role_label = "User" if msg.role == "user" else "Atlas"
            # Truncate very long messages in history
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            formatted.append(f"{role_label}: {content}")

        return "\n".join(formatted)

    @staticmethod
    async def get_user_context(user: User) -> str:
        """Build user context string for AI prompts."""
        if not user:
            return "New user, no profile yet."

        parts = [f"User's name: {user.first_name or 'Unknown'}"]

        if user.role:
            parts.append(f"Role: {user.role}")
        if user.interests:
            parts.append(f"Interests: {', '.join(user.interests)}")
        if user.watchlist:
            parts.append(f"Watchlist: {', '.join(user.watchlist)}")
        if user.sectors:
            parts.append(f"Sectors: {', '.join(user.sectors)}")
        if user.preferred_detail_level:
            parts.append(f"Preferred detail level: {user.preferred_detail_level}")

        parts.append(f"Onboarded: {'Yes' if user.is_onboarded else 'No'}")
        parts.append(f"Message count: {user.message_count}")

        return "\n".join(parts)

    @staticmethod
    async def save_interaction(telegram_id: int, user_id: int,
                                user_message: str, assistant_response: str,
                                message_type: str = "text"):
        """Save both user message and assistant response to history."""
        await ConversationRepository.save_message(
            telegram_id=telegram_id,
            user_id=user_id,
            role="user",
            content=user_message,
            message_type=message_type,
        )
        await ConversationRepository.save_message(
            telegram_id=telegram_id,
            user_id=user_id,
            role="assistant",
            content=assistant_response,
            message_type="text",
        )
