from aiogram import Router
from aiogram.types import Message
from loguru import logger

router = Router()


@router.message()
async def catch_all_handler(message: Message):
    logger.debug(f"ФОЛБЭК: Сообщение не обработано ни одним роутером: {message.text[:50]}...")
