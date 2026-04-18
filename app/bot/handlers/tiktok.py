import hashlib
import re
import time
from typing import Optional

from aiogram import F, Router, html
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from loguru import logger

from app.core import config
from app.core.interfaces import IVideoDownloader
from app.services.downloader import TikTokBlockError, TikTokDownloader
from app.utils.ui_utils import create_progress_bar
from app.utils.user_settings import user_settings

router = Router()
downloader: IVideoDownloader = TikTokDownloader()

TIKTOK_RE = re.compile(r"(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[A-Za-z0-9_&?=/.\-@]+)")

# Кэш для хранения URL ссылок, чтобы кнопки могли их перекачивать
URL_CACHE: dict[str, str] = {}


def get_url_id(url: str) -> str:
    """Генерирует короткий ID для URL и сохраняет его в кэше."""
    url_id = hashlib.md5(url.encode()).hexdigest()[:8]
    URL_CACHE[url_id] = url
    # Ограничиваем размер кэша
    if len(URL_CACHE) > config.URL_CACHE_SIZE:
        if URL_CACHE:
            first_key = next(iter(URL_CACHE))
            del URL_CACHE[first_key]
    return url_id


def get_mode_keyboard(url: str, current_mode: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для переключения режима."""
    url_id = get_url_id(url)
    label = (
        "🔄 Всегда присылать как ВИДЕО"
        if current_mode == "images"
        else "🔄 Всегда присылать как ФОТО"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=f"toggle_mode:{url_id}")]]
    )
    return keyboard


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Обработчик команды /start."""
    await message.answer(
        f"Привет, {message.from_user.full_name}! Пришли мне ссылку на TikTok, и я скачаю видео для тебя."
    )


@router.message(F.text)
async def tiktok_handler(
    message: Message, manual_url: Optional[str] = None, forced_user_id: Optional[int] = None
) -> None:
    """Основной обработчик ссылок TikTok."""
    # Ищем ссылку в тексте или используем manual_url
    if manual_url:
        url = manual_url
    else:
        match = TIKTOK_RE.search(message.text)
        if not match:
            return
        url = match.group(0)

    target_user_id = forced_user_id or message.from_user.id

    logger.info(f"tiktok_handler: Ссылка найдена: {url} (user: {target_user_id})")
    status_msg = await message.answer("⏳ Анализирую контент TikTok...")

    try:
        logger.debug(f"Начало обработки: {url}")

        last_update_time = 0.0
        last_percentage = -1

        async def update_status(content_type: str) -> None:
            try:
                await status_msg.edit_text(f"⏳ Загружаю {content_type} из TikTok...")
            except Exception:
                pass

        async def progress_cb(percentage: float) -> None:
            nonlocal last_update_time, last_percentage
            current_time = time.time()
            if current_time - last_update_time < 1.5:
                return

            if int(percentage) == last_percentage:
                return

            last_update_time = current_time
            last_percentage = int(percentage)
            bar = create_progress_bar(percentage)
            try:
                await status_msg.edit_text(f"⏳ Загрузка: {bar}")
            except Exception:
                pass

        video_info = await downloader.download(
            url,
            progress_callback=progress_cb,
            status_callback=update_status,
            user_id=target_user_id,
        )

        current_mode = user_settings.get_mode(target_user_id)
        keyboard = get_mode_keyboard(url, current_mode) if video_info.image_paths else None

        if not video_info.file_path and video_info.image_paths:
            logger.info(f"Отправка слайд-шоу: {len(video_info.image_paths)} фото")
            media_group = [
                InputMediaPhoto(media=FSInputFile(path)) for path in video_info.image_paths
            ]
            if media_group:
                media_group[0].caption = (
                    html.quote(video_info.title) if video_info.title else "Вот ваше слайд-шоу!"
                )

            await message.bot.send_media_group(chat_id=message.chat.id, media=media_group)
            if keyboard:
                await message.answer(
                    "Используйте кнопку ниже, чтобы изменить формат:", reply_markup=keyboard
                )
        else:
            logger.info(f"Видео успешно загружено: {video_info.file_path}")
            await message.answer_video(
                video=FSInputFile(video_info.file_path),
                caption=html.quote(video_info.title) if video_info.title else "Вот ваше видео!",
                reply_markup=keyboard,
            )

        await downloader.cleanup(video_info.file_path, image_paths=video_info.image_paths)
        await status_msg.delete()

    except TikTokBlockError as e:
        logger.warning(f"TikTok заблокировал запрос от {target_user_id}: {url}")
        await status_msg.edit_text(f"⚠️ {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке TikTok {url}: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при загрузке: {str(e)}")


@router.callback_query(F.data.startswith("toggle_mode:"))
async def switch_mode_callback(callback: CallbackQuery) -> None:
    """Обработчик переключения режима (Видео/Фото)."""
    url_id = callback.data.split(":")[1]
    url = URL_CACHE.get(url_id)

    if not url:
        await callback.answer("⚠️ Ссылка устарела, отправьте её заново.", show_alert=True)
        return

    new_mode = user_settings.toggle_mode(callback.from_user.id)
    await callback.answer(f"✅ Режим изменен на {'ВИДЕО' if new_mode == 'video' else 'ФОТО'}")

    await tiktok_handler(callback.message, manual_url=url, forced_user_id=callback.from_user.id)
