from sqlalchemy import create_engine, Column, String, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import datetime

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class ChatSession(Base):
    __tablename__ = 'chat_session'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_active = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship('ChatMessage', back_populates='session', cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_message'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_session.id', ondelete='CASCADE'))
    is_user = Column(Boolean, nullable=False)
    message = Column(Text, nullable=False)
    llm_prompt = Column(Text)
    llm_model = Column(String(128))
    llm_answer = Column(Text)
    sources = Column(JSON)
    toxicity_input = Column(JSON)
    toxicity_output = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship('ChatSession', back_populates='messages')
    feedback = relationship('ChatFeedback', back_populates='message', cascade="all, delete-orphan")

class ChatFeedback(Base):
    __tablename__ = 'chat_feedback'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey('chat_message.id', ondelete='CASCADE'))
    rating = Column(Integer)
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    message = relationship('ChatMessage', back_populates='feedback')
