"""
Database Models - SQLAlchemy ORM Models for Atlas Financial Assistant
"""
import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime,
    Boolean, JSON, Float, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database.connection import Base


class User(Base):
    """User profile and preferences."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    # Onboarding
    is_onboarded = Column(Boolean, default=False)
    onboarding_step = Column(String(50), default="welcome")  # welcome, role, interests, watchlist, briefing, complete

    # Profile
    role = Column(String(100), nullable=True)  # Investor, Analyst, Founder, Student, etc.
    interests = Column(JSON, default=list)  # ["AI", "semiconductors", "fintech"]
    watchlist = Column(JSON, default=list)  # ["AAPL", "MSFT", "GOOGL"]
    sectors = Column(JSON, default=list)  # ["Technology", "Healthcare"]

    # Preferences
    briefing_time = Column(String(10), default="08:00")  # Morning briefing time
    evening_briefing_time = Column(String(10), default="18:00")
    briefing_enabled = Column(Boolean, default=True)
    timezone = Column(String(50), default="Asia/Kolkata")
    preferred_detail_level = Column(String(20), default="concise")  # concise, detailed

    # Google Integration (OAuth tokens stored as JSON)
    google_tokens = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_active = Column(DateTime, default=datetime.datetime.utcnow)
    message_count = Column(Integer, default=0)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, name='{self.first_name}')>"


class Conversation(Base):
    """Conversation history for context and memory."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False, index=True)

    # Message
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, voice, document, image

    # Context
    intent = Column(String(100), nullable=True)  # stock_query, company_research, news, etc.
    entities = Column(JSON, default=dict)  # {"tickers": ["AAPL"], "topics": ["earnings"]}

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")

    __table_args__ = (
        Index("ix_conversations_user_created", "user_id", "created_at"),
    )


class Alert(Base):
    """Price alerts and notifications."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False)

    # Alert config
    alert_type = Column(String(50), nullable=False)  # price_above, price_below, percent_change, news
    ticker = Column(String(20), nullable=True)
    condition_value = Column(Float, nullable=True)  # Target price or percentage
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)

    # For event reminders (earnings, FOMC, etc.)
    remind_at = Column(DateTime, nullable=True)   # Exact time to send reminder
    event_date = Column(String(50), nullable=True) # The event date string

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="alerts")


class Document(Base):
    """Uploaded financial documents."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(BigInteger, nullable=False)

    # Document info
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, xlsx
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)

    # Extracted content
    extracted_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    key_insights = Column(JSON, default=list)

    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
