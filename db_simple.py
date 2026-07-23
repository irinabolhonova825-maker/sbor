import os
from sqlalchemy import create_engine, Column, Integer, String, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Используем SQLite для демонстрации (файл telegram_aggregator.db)
DATABASE_URL = 'sqlite:///telegram_aggregator.db'
print(f"✅ Используется SQLite: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_admin = Column(Integer, default=0)

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    user_id = Column(BigInteger)
    text = Column(Text)
    date = Column(String(50))

class Chat(Base):
    __tablename__ = 'chats'
    chat_id = Column(BigInteger, primary_key=True)
    chat_name = Column(String(255))
    chat_type = Column(String(50))

Base.metadata.create_all(engine)
print("✅ Таблицы созданы (SQLite)")

def get_session():
    return SessionLocal()

def save_user(telegram_id, username, first_name, last_name):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name)
        session.add(user)
        session.commit()
    session.close()

def save_message(message_id, chat_id, user_id, text, date=None):
    if date is None:
        date = datetime.now().isoformat()
    session = get_session()
    msg = Message(message_id=message_id, chat_id=chat_id, user_id=user_id, text=text, date=date)
    session.add(msg)
    session.commit()
    session.close()

def save_chat(chat_id, chat_name, chat_type):
    session = get_session()
    chat = session.query(Chat).filter_by(chat_id=chat_id).first()
    if not chat:
        chat = Chat(chat_id=chat_id, chat_name=chat_name, chat_type=chat_type)
        session.add(chat)
        session.commit()
    session.close()

def is_admin(telegram_id):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    session.close()
    return user and user.is_admin == 1

def get_stats():
    session = get_session()
    total = session.query(Message).count()
    chats = session.query(Message.chat_id).distinct().count()
    session.close()
    return total, chats

def export_messages(chat_id, days=7):
    from datetime import datetime, timedelta
    session = get_session()
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = session.query(Message).filter(Message.chat_id == chat_id, Message.date >= since).order_by(Message.date).all()
    session.close()
    return [(row.text, row.date, row.user_id) for row in rows]

def init_db():
    Base.metadata.create_all(engine)