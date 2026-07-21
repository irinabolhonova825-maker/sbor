import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, filters
from telegram.request import HTTPXRequest
from database.db_manager import DatabaseManager
import pandas as pd
import io

logger = logging.getLogger(__name__)

SELECT_CHAT, SELECT_PERIOD, CONFIRM_EXPORT = range(3)

class UnifiedBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        logger.info(f"Received /start from user {update.effective_user.id}")
        
        user_id = update.effective_user.id
        is_admin = self.db.is_admin(user_id)
        
        text = "👋 Привет! Я бот для сбора корпоративных переписок.\n\n"
        text += "📊 Доступные команды:\n"
        text += "/help - помощь\n"
        
        if is_admin:
            text += "/export - экспорт данных\n"
            text += "/stats - статистика\n"
        else:
            text += "\nℹ️ Вы обычный пользователь. Я собираю сообщения в чатах."
        
        await update.message.reply_text(text)
        logger.info(f"Sent start message to {user_id}")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        logger.info(f"Received /help from user {update.effective_user.id}")
        
        text = "📚 Помощь\n\n"
        text += "Я собираю сообщения из чатов для анализа.\n\n"
        text += "Команды:\n"
        text += "/start - Приветствие\n"
        text += "/help - Эта справка\n"
        
        user_id = update.effective_user.id
        if self.db.is_admin(user_id):
            text += "/export - Экспорт данных\n"
            text += "/stats - Статистика по чатам\n"
        
        await update.message.reply_text(text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        try:
            message = update.message
            if not message or not message.text:
                return
            
            # Игнорируем команды
            if message.text.startswith('/'):
                return
            
            logger.info(f"Received message from {message.from_user.id}: {message.text[:50]}...")
            
            user = message.from_user
            chat = message.chat
            
            # Сохраняем пользователя
            self.db.save_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Сохраняем чат
            self.db.save_chat(
                chat_id=chat.id,
                chat_name=chat.title or chat.first_name or f"Chat_{chat.id}",
                chat_type=chat.type
            )
            
            # Определяем тип медиа
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
            
            # Сохраняем сообщение
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
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /export"""
        logger.info(f"Received /export from user {update.effective_user.id}")
        
        user_id = update.effective_user.id
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав администратора.")
            return
        
        session = self.db.get_session()
        from database.models import Chat
        chats = session.query(Chat).filter_by(is_active=1).all()
        session.close()
        
        if not chats:
            await update.message.reply_text("❌ Нет доступных чатов.")
            return
        
        keyboard = []
        for chat in chats:
            keyboard.append([InlineKeyboardButton(
                chat.chat_name or f"Chat {chat.chat_id}",
                callback_data=f"chat_{chat.chat_id}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 Выберите чат для экспорта:", reply_markup=reply_markup)
        return SELECT_CHAT
    
    async def select_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор чата"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Отменено.")
            return ConversationHandler.END
        
        chat_id = int(query.data.split('_')[1])
        context.user_data['selected_chat_id'] = chat_id
        
        keyboard = [
            [InlineKeyboardButton("📅 За сегодня", callback_data="period_today")],
            [InlineKeyboardButton("📅 За неделю", callback_data="period_week")],
            [InlineKeyboardButton("📅 За месяц", callback_data="period_month")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text("📅 Выберите период:", reply_markup=reply_markup)
        return SELECT_PERIOD
    
    async def select_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор периода"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Отменено.")
            return ConversationHandler.END
        
        period = query.data.split('_')[1]
        end_date = datetime.utcnow()
        
        if period == "today":
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            await query.edit_message_text("❌ Неверный период.")
            return ConversationHandler.END
        
        context.user_data['start_date'] = start_date
        context.user_data['end_date'] = end_date
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="export_confirm")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
            "Подтвердите экспорт:",
            reply_markup=reply_markup
        )
        return CONFIRM_EXPORT
    
    async def confirm_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение экспорта"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("❌ Отменено.")
            return ConversationHandler.END
        
        chat_id = context.user_data['selected_chat_id']
        start_date = context.user_data['start_date']
        end_date = context.user_data['end_date']
        
        messages = self.db.get_messages_by_date(chat_id, start_date, end_date)
        
        if not messages:
            await query.edit_message_text("❌ Нет сообщений за выбранный период.")
            return ConversationHandler.END
        
        data = []
        for item in messages:
            msg = item['message']
            user = item['user']
            reactions = item['reactions']
            reaction_text = ', '.join([r.reaction_type for r in reactions]) if reactions else ''
            
            data.append({
                'Дата': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Пользователь': f"{user.first_name} {user.last_name or ''}".strip(),
                'Username': user.username or '',
                'Текст': msg.text or '',
                'Тип медиа': msg.media_type,
                'Реакции': reaction_text
            })
        
        df = pd.DataFrame(data)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Messages', index=False)
        
        output.seek(0)
        
        session = self.db.get_session()
        from database.models import Chat
        chat = session.query(Chat).filter_by(chat_id=chat_id).first()
        session.close()
        
        await query.edit_message_text("📤 Создание экспорта...")
        
        await update.effective_user.send_document(
            document=output,
            filename=f"export_{chat.chat_name}_{start_date.strftime('%Y%m%d')}.xlsx",
            caption=f"📊 Экспорт чата {chat.chat_name}\n"
                    f"📅 Сообщений: {len(data)}"
        )
        
        await query.edit_message_text("✅ Экспорт завершен!")
        return ConversationHandler.END
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика"""
        logger.info(f"Received /stats from user {update.effective_user.id}")
        
        user_id = update.effective_user.id
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав.")
            return
        
        session = self.db.get_session()
        from database.models import Chat, Message
        chats = session.query(Chat).filter_by(is_active=1).all()
        
        stats = "📊 Статистика по чатам\n\n"
        for chat in chats:
            msg_count = session.query(Message).filter_by(chat_id=chat.chat_id).count()
            user_count = session.query(Message.user_id).filter_by(chat_id=chat.chat_id).distinct().count()
            stats += f"**{chat.chat_name}**: {msg_count} сообщений, {user_count} пользователей\n"
        
        session.close()
        await update.message.reply_text(stats, parse_mode='Markdown')
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    def run(self):
        """Запуск бота"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return
        
        try:
            # Создаем request с таймаутами
            request = HTTPXRequest(
                connect_timeout=60.0,
                read_timeout=60.0,
                write_timeout=60.0,
                pool_timeout=60.0
            )
            
            # Создаем приложение
            self.application = Application.builder() \
                .token(self.token) \
                .request(request) \
                .build()
            
            # Регистрируем обработчики команд
            self.application.add_handler(CommandHandler('start', self.start))
            self.application.add_handler(CommandHandler('help', self.help_command))
            self.application.add_handler(CommandHandler('stats', self.stats_command))
            
            # Обработчик экспорта (с состояниями)
            export_handler = ConversationHandler(
                entry_points=[CommandHandler('export', self.export_command)],
                states={
                    SELECT_CHAT: [CallbackQueryHandler(self.select_chat)],
                    SELECT_PERIOD: [CallbackQueryHandler(self.select_period)],
                    CONFIRM_EXPORT: [CallbackQueryHandler(self.confirm_export)],
                },
                fallbacks=[CommandHandler('cancel', lambda u, c: u.message.reply_text("❌ Отменено."))],
            )
            self.application.add_handler(export_handler)
            
            # Обработчик всех сообщений (для сбора)
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Обработчик ошибок
            self.application.add_error_handler(self.error_handler)
            
            logger.info("🤖 Unified bot started successfully!")
            logger.info(f"📊 Bot token: {self.token[:10]}...")
            logger.info("📝 Bot is ready to receive messages!")
            
            # Запускаем бота
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                poll_interval=1.0,
                timeout=60
            )
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            import traceback
            traceback.print_exc()
