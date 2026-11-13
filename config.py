import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

allowed_users_str = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(user_id.strip()) for user_id in allowed_users_str.split(",") if user_id.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения!")