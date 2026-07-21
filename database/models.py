from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_admin = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    chat_name = Column(String(255))
    chat_type = Column(String(50))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    text = Column(Text)
    media_type = Column(String(50))
    file_id = Column(String(255))
    reply_to = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reaction(Base):
    __tablename__ = 'reactions'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    reaction_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
