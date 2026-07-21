import logging
import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class TelegramCollector:
    def __init__(self):
        self.db = DatabaseManager()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.application = None
        self._loop = None
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            message = update.message
            if not message:
                return
            
            user = message.from_user
            self.db.save_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            chat = message.chat
            self.db.save_chat(
                chat_id=chat.id,
                chat_name=chat.title or chat.first_name or f"Chat_{chat.id}",
                chat_type=chat.type
            )
            
            media_type = 'text'
            file_id = None
            
            if message.photo:
                media_type = 'photo'
                file_id = message.photo[-1].file_id
            elif message.document:
                media_type = 'document'
                file_id = message.document.file_id
            elif message.video:
                media_type = 'video'
                file_id = message.video.file_id
            elif message.audio:
                media_type = 'audio'
                file_id = message.audio.file_id
            elif message.voice:
                media_type = 'voice'
                file_id = message.voice.file_id
            
            message_data = {
                'message_id': message.message_id,
                'chat_id': chat.id,
                'user_id': user.id,
                'text': message.text or message.caption or '',
                'media_type': media_type,
                'file_id': file_id,
                'reply_to': message.reply_to_message.message_id if message.reply_to_message else None,
                'created_at': message.date or datetime.utcnow()
            }
            
            self.db.save_message(message_data)
            logger.info(f"Saved message {message.message_id} from {user.first_name}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def run_collector(self):
        """Асинхронный запуск сборщика"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return
        
        self.application = Application.builder().token(self.token).build()
        self.application.add_handler(MessageHandler(filters.ALL, self.handle_message))
        
        logger.info("📊 Collector started")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Держим бота активным
        while True:
            await asyncio.sleep(1)
    
    def start_collector(self):
        """Запуск сборщика в отдельном потоке"""
        try:
            # Создаем новый event loop для этого потока
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Запускаем асинхронную функцию
            self._loop.run_until_complete(self.run_collector())
        except KeyboardInterrupt:
            logger.info("Collector stopped by user")
        except Exception as e:
            logger.error(f"Collector error: {e}")
        finally:
            if self.application:
                try:
                    if self._loop and not self._loop.is_closed():
                        self._loop.run_until_complete(self.application.stop())
                except:
                    pass
    
    def stop_collector(self):
        """Остановка сборщика"""
        if self.application and self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self.application.stop())
            except:
                pass
            logger.info("Collector stopped")
