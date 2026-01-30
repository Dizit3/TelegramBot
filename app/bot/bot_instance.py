import sys
from os import getenv
from dotenv import load_dotenv
from loguru import logger

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

load_dotenv()

TOKEN = getenv("BOT_TOKEN")

if not TOKEN:
    logger.critical("BOT_TOKEN не установлен в переменных окружения!")
    sys.exit(1)

dp = Dispatcher()
bot = Bot(
    token=TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
