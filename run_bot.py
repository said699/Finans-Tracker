import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from aiogram import Bot, Dispatcher
from apps.bot.handlers import dp
from django.conf import settings

async def main():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    print("Бот успешно запущен в режиме Polling и ожидает сообщения...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())