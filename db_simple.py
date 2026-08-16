# db_simple.py
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise Exception("Переменная DATABASE_URL не найдена в .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String, nullable=True)
    username = Column(String, nullable=True)
    type = Column(String)  # private, group, supergroup, channel
    last_activity = Column(DateTime, default=datetime.now)

    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(BigInteger)
    text = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.now)
    file_path = Column(String, nullable=True)   # путь к скачанному файлу
    file_id = Column(String, nullable=True)     # Telegram file_id

    chat = relationship("Chat", back_populates="messages")

def init_db():
    Base.metadata.create_all(engine)