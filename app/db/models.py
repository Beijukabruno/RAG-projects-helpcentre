import datetime
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain_url = Column(Text)
    enabled = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default="active")
    config_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    membership_role = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChatSession(Base):
    __tablename__ = "chat_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(64), nullable=False, index=True)
    audience = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_session.id", ondelete="CASCADE"))
    project_id = Column(String(64), nullable=False, index=True)
    audience = Column(String(32), nullable=False, index=True)
    is_user = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    llm_prompt = Column(Text)
    llm_model = Column(String(128))
    llm_answer = Column(Text)
    sources = Column(JSON)
    toxicity_input = Column(JSON)
    toxicity_output = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")
    feedback = relationship("ChatFeedback", back_populates="message", cascade="all, delete-orphan")


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_message.id", ondelete="CASCADE"))
    project_id = Column(String(64), nullable=False, index=True)
    audience = Column(String(32), nullable=False, index=True)
    rating = Column(Integer)
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    message = relationship("ChatMessage", back_populates="feedback")
