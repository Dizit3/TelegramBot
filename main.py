import asyncio
import sys
import logging
from loguru import logger
from aiogram.types import Message

from app.bot.bot_instance import bot, dp
from app.bot.handlers import tiktok, fallback
from app.utils.lock_manager import acquire_lock, release_lock

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

async def main() -> None:
    # Настройка loguru
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    logger.add("logs/bot.log", rotation="10 MB", retention="10 days", level="DEBUG")

    logger.info("Инициализация запуска бота...")
    
    # 1. Проверка на запущенную копию (с жестким убийством старой)
    acquire_lock()
    
    try:
        logger.info("Очистка старых сессий Telegram...")
        # 2. Удаляем вебхук и сбрасываем старые сообщения ПЕРЕД регистрацией роутеров
        await bot.delete_webhook(drop_pending_updates=True)
        
        # 3. Регистрация роутеров
        # 3. Регистрация роутеров в строгом порядке
        logger.debug("Подключение роутеров...")
        dp.include_router(tiktok.router)
        dp.include_router(fallback.router)  # Фолбэк должен быть последним
        
        logger.success("BOT_READY: TikTok Downloader Bot успешно запущен!")
        
        # 4. Запуск polling
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Работа бота была прервана (CancelledError).")
    except Exception as e:
        logger.exception(f"Критическая ошибка при работе бота: {e}")
    finally:
        # Освобождаем блокировку при выключении
        logger.info("Завершение работы, освобождение блокировки...")
        release_lock()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (KeyboardInterrupt).")
        sys.exit(0)
