import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from app.core import config

if not config.BOT_TOKEN:
    logger.critical("BOT_TOKEN не установлен в переменных окружения!")
    sys.exit(1)

dp = Dispatcher()
bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
