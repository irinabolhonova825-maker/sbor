import os
import csv
import io
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from db_simple import SessionLocal, Chat, Message, init_db
from utils.logger import logger

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")

# Список администраторов (Telegram ID)
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ---------- ОБРАБОТЧИКИ КОМАНД ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text("Привет! Я бот для сбора сообщений.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    text = (
        "🤖 *Доступные команды:*\n\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/export ГГГГ-ММ-ДД ГГГГ-ММ-ДД [chat_id] — экспорт сообщений за период\n"
        "/stats — статистика (только для администраторов)\n"
        "/status — то же, что /stats\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика по чатам и сообщениям (только для админов)"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав на эту команду.")
        return

    session = SessionLocal()
    try:
        chats_count = session.query(Chat).count()
        messages_count = session.query(Message).count()
        users_count = session.query(Message.user_id).distinct().count()
    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении статистики: {e}")
        logger.error(f"Stats error: {e}", exc_info=True)
        return
    finally:
        session.close()

    text = (
        "📊 *Статистика*\n\n"
        f"📝 Всего сообщений: `{messages_count}`\n"
        f"💬 Всего чатов: `{chats_count}`\n"
        f"👤 Уникальных пользователей: `{users_count}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт сообщений за указанный период в CSV"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Формат: /export ГГГГ-ММ-ДД ГГГГ-ММ-ДД [chat_id (опционально)]")
        return

    try:
        start_date = datetime.strptime(args[0], "%Y-%m-%d")
        end_date = datetime.strptime(args[1], "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return

    session = SessionLocal()
    try:
        # Фильтр: с начала start_date до конца end_date (включительно)
        query = session.query(Message).filter(
            Message.date >= start_date,
            Message.date < end_date + timedelta(days=1)
        )

        # Фильтр по чату, если передан третий аргумент
        if len(args) >= 3:
            try:
                chat_id = int(args[2])
                query = query.filter(Message.chat_id == chat_id)
            except ValueError:
                chat = session.query(Chat).filter(Chat.username == args[2]).first()
                if chat:
                    query = query.filter(Message.chat_id == chat.chat_id)
                else:
                    await update.message.reply_text("Чат не найден.")
                    return

        messages = query.all()
        if not messages:
            await update.message.reply_text("Нет сообщений за указанный период.")
            return

        # Генерация CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Дата", "User ID", "Текст", "Файл"])
        for msg in messages:
            writer.writerow([
                msg.id,
                msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                msg.user_id,
                msg.text or "",
                msg.file_path or ""
            ])

        # Отправка файла через BytesIO (исправлено)
        csv_content = output.getvalue()
        csv_bytes = ('\ufeff' + csv_content).encode('utf-8')
        await update.message.reply_document(
            document=io.BytesIO(csv_bytes),
            filename="export.csv",
            caption=f"Экспорт с {start_date.date()} по {end_date.date()}"
)
        logger.info(f"Экспорт выполнен: {len(messages)} записей")

    except Exception as e:
        await update.message.reply_text(f"Ошибка при экспорте: {e}")
        logger.error(f"Export error: {e}", exc_info=True)
    finally:
        session.close()

# ---------- ОБРАБОТЧИК СООБЩЕНИЙ ----------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет входящее сообщение, обновляет чат, скачивает файлы"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message

    session = SessionLocal()
    try:
        # --- Обновляем или создаём чат ---
        db_chat = session.query(Chat).filter_by(chat_id=chat.id).first()
        if not db_chat:
            db_chat = Chat(
                chat_id=chat.id,
                title=chat.title or user.full_name,
                username=chat.username,
                type=chat.type
            )
            session.add(db_chat)
        else:
            db_chat.title = chat.title or db_chat.title
            db_chat.username = chat.username or db_chat.username
            db_chat.last_activity = datetime.now()

        # --- Сохраняем сообщение (дата уже datetime) ---
        new_msg = Message(
            chat_id=chat.id,
            user_id=user.id,
            text=message.text or message.caption or "",
            date=message.date  # исправлено: теперь напрямую
        )

        # --- Скачивание файлов (если есть) ---
        file_path = None
        file_id = None

        if message.document:
            file_obj = message.document
            file_id = file_obj.file_id
            file_name = file_obj.file_name or f"file_{file_id}.bin"
            file_path = os.path.join("media", file_name)
            try:
                file = await message.document.get_file()
                await file.download_to_drive(file_path)
                logger.info(f"Файл скачан: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка скачивания документа: {e}")
                file_path = None

        elif message.photo:
            photo = message.photo[-1]  # самое качественное
            file_id = photo.file_id
            file_path = os.path.join("media", f"photo_{file_id}.jpg")
            try:
                file = await photo.get_file()
                await file.download_to_drive(file_path)
                logger.info(f"Фото скачано: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка скачивания фото: {e}")
                file_path = None

        # Можно добавить обработку видео, аудио, голосовых и т.д. по аналогии

        new_msg.file_path = file_path
        new_msg.file_id = file_id

        session.add(new_msg)
        session.commit()
        logger.info(f"Сообщение сохранено от {user.full_name} (id={user.id}) в чате {chat.title}")

        # (Опционально) ответить, чтобы подтвердить приём – раскомментируйте, если нужно
        # await update.message.reply_text("Сообщение сохранено!")

    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения: {e}", exc_info=True)
    finally:
        session.close()

# ---------- ЗАПУСК ----------

def main():
    # Создаём таблицы, если их нет
    init_db()

    # Создаём приложение
    app = Application.builder() \
    .token(TOKEN) \
    .connect_timeout(60.0) \
    .read_timeout(60.0) \
    .write_timeout(60.0) \
    .pool_timeout(60.0) \
    .build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("status", stats_command))  # алиас
    app.add_handler(CommandHandler("export", export_command))

    # Регистрируем обработчик всех текстовых, фото, документов
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.CAPTION,
        handle_message
    ))

    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()