from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from .models import Base, User, Chat, Message, Reaction
import os

class DatabaseManager:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///telegram_aggregator.db')
        self.engine = create_engine(self.database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    def save_user(self, telegram_id, username, first_name, last_name):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    def get_user(self, telegram_id):
        session = self.get_session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        finally:
            session.close()
    
    def is_admin(self, telegram_id):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            return user and user.is_admin == 1
        finally:
            session.close()
    
    def add_admin(self, telegram_id):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.is_admin = 1
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def save_chat(self, chat_id, chat_name, chat_type):
        session = self.get_session()
        try:
            chat = session.query(Chat).filter_by(chat_id=chat_id).first()
            if not chat:
                chat = Chat(chat_id=chat_id, chat_name=chat_name, chat_type=chat_type)
                session.add(chat)
                session.commit()
            return chat
        finally:
            session.close()
    
    def save_message(self, message_data):
        session = self.get_session()
        try:
            existing = session.query(Message).filter_by(
                message_id=message_data['message_id'],
                chat_id=message_data['chat_id']
            ).first()
            
            if existing:
                return existing
            
            message = Message(**message_data)
            session.add(message)
            session.commit()
            return message
        finally:
            session.close()
    
    def get_messages_by_date(self, chat_id, start_date, end_date):
        session = self.get_session()
        try:
            messages = session.query(Message).filter(
                and_(
                    Message.chat_id == chat_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date
                )
            ).order_by(Message.created_at).all()
            
            result = []
            for msg in messages:
                user = session.query(User).filter_by(telegram_id=msg.user_id).first()
                reactions = session.query(Reaction).filter_by(message_id=msg.message_id).all()
                result.append({
                    'message': msg,
                    'user': user,
                    'reactions': reactions
                })
            return result
        finally:
            session.close()
    
    def save_reaction(self, message_id, user_id, reaction_type):
        session = self.get_session()
        try:
            existing = session.query(Reaction).filter_by(
                message_id=message_id,
                user_id=user_id,
                reaction_type=reaction_type
            ).first()
            
            if not existing:
                reaction = Reaction(
                    message_id=message_id,
                    user_id=user_id,
                    reaction_type=reaction_type
                )
                session.add(reaction)
                session.commit()
                return reaction
            return existing
        finally:
            session.close()
