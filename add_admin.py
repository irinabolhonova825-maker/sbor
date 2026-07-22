import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL не найден в .env")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

from db_simple import User  # импортируем модель User

def add_admin(telegram_id, username="admin", first_name="Admin"):
    session = Session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        # Если пользователя нет – создаём
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            is_admin=1
        )
        session.add(user)
        session.commit()
        print(f"✅ Пользователь {telegram_id} создан и назначен администратором!")
    else:
        user.is_admin = 1
        session.commit()
        print(f"✅ Пользователь {telegram_id} теперь администратор!")
    session.close()

if __name__ == "__main__":
    # Замените 1266582465 на свой Telegram ID
    admin_id = 1266582465
    add_admin(admin_id)
