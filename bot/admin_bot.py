from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
import os
import asyncio
from dotenv import load_dotenv
from database.db_manager import DatabaseManager
import pandas as pd
from datetime import datetime, timedelta
import io
import logging

load_dotenv()
logger = logging.getLogger(__name__)

SELECT_CHAT, SELECT_PERIOD, CONFIRM_EXPORT = range(3)

class AdminBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.application = None
        self._loop = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return
        
        await update.message.reply_text(
            "👋 Добро пожаловать в систему сбора переписок!\n\n"
            "📊 Доступные команды:\n"
            "/export - экспорт данных из чата\n"
            "/stats - статистика по чатам\n"
            "/help - помощь"
        )
    
    async def export_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 Помощь\n\n"
            "/start - Приветствие\n"
            "/export - Экспорт данных из чата\n"
            "/stats - Статистика по чатам\n"
            "/help - Эта справка"
        )
    
    async def run_admin(self):
        """Асинхронный запуск админ-бота"""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set!")
            return
        
        self.application = Application.builder().token(self.token).build()
        
        export_handler = ConversationHandler(
            entry_points=[CommandHandler('export', self.export_command)],
            states={
                SELECT_CHAT: [CallbackQueryHandler(self.select_chat)],
                SELECT_PERIOD: [CallbackQueryHandler(self.select_period)],
                CONFIRM_EXPORT: [CallbackQueryHandler(self.confirm_export)],
            },
            fallbacks=[CommandHandler('cancel', lambda u, c: u.message.reply_text("❌ Отменено."))],
        )
        
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(export_handler)
        self.application.add_handler(CommandHandler('stats', self.stats_command))
        self.application.add_handler(CommandHandler('help', self.help_command))
        
        logger.info("👔 Admin bot started")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Держим бота активным
        while True:
            await asyncio.sleep(1)
    
    def start_admin(self):
        """Запуск админ-бота в отдельном потоке"""
        try:
            # Создаем новый event loop для этого потока
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Запускаем асинхронную функцию
            self._loop.run_until_complete(self.run_admin())
        except KeyboardInterrupt:
            logger.info("Admin bot stopped by user")
        except Exception as e:
            logger.error(f"Admin bot error: {e}")
        finally:
            if self.application:
                try:
                    if self._loop and not self._loop.is_closed():
                        self._loop.run_until_complete(self.application.stop())
                except:
                    pass
    
    def stop_admin(self):
        """Остановка админ-бота"""
        if self.application and self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self.application.stop())
            except:
                pass
            logger.info("Admin bot stopped")
