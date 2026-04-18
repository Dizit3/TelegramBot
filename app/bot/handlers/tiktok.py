import re
from aiogram import Router, F, html
from aiogram.types import Message, FSInputFile, InputMediaPhoto
from aiogram.filters import CommandStart
from loguru import logger

from app.core.interfaces import IVideoDownloader
from app.services.downloader import TikTokDownloader, TikTokBlockError
from app.utils.ui_utils import create_progress_bar
import time

router = Router()
downloader: IVideoDownloader = TikTokDownloader()

TIKTOK_RE = re.compile(r'(https?://(?:www\.|vm\.|vt\.)?tiktok\.com/[A-Za-z0-9_&?=/.\-@]+)')

@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Привет, {message.from_user.full_name}! Пришли мне ссылку на TikTok, и я скачаю видео для тебя.")

@router.message(F.text)
async def tiktok_handler(message: Message) -> None:
    # Ищем ссылку в тексте
    match = TIKTOK_RE.search(message.text)
    if not match:
        return

    url = match.group(0)
    logger.info(f"tiktok_handler: Ссылка найдена: {url}")
    status_msg = await message.answer("⏳ Анализирую контент TikTok...")
    
    try:
        logger.debug(f"Начало обработки: {url}")
        
        last_update_time = 0
        last_percentage = -1

        async def update_status(content_type: str):
            try:
                await status_msg.edit_text(f"⏳ Загружаю {content_type} из TikTok...")
            except Exception:
                pass

        async def progress_cb(percentage: float):
            nonlocal last_update_time, last_percentage
            # Обновляем не чаще раза в 1.5 сек и только если процент изменился существенно
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
                pass # Игнорируем ошибки редактирования (например, если сообщение удалено)

        video_info = await downloader.download(
            url, 
            progress_callback=progress_cb,
            status_callback=update_status,
            user_id=message.from_user.id
        )
        
        # Если file_path пустой, значит мы в режиме "Альбом фото" или видео не собралось
        if not video_info.file_path and video_info.image_paths:
            logger.info(f"Отправка слайд-шоу: {len(video_info.image_paths)} фото")
            media_group = [InputMediaPhoto(media=FSInputFile(path)) for path in video_info.image_paths]
            # Добавляем подпись к первому фото
            if media_group:
                media_group[0].caption = html.quote(video_info.title) if video_info.title else "Вот ваше слайд-шоу из TikTok!"
            
            await message.bot.send_media_group(chat_id=message.chat.id, media=media_group)
        else:
            logger.info(f"Видео успешно загружено: {video_info.file_path}")
            await message.answer_video(
                video=FSInputFile(video_info.file_path),
                caption=html.quote(video_info.title) if video_info.title else "Вот ваше видео из TikTok!",
            )
        
        await downloader.cleanup(video_info.file_path, image_paths=video_info.image_paths)
        logger.debug(f"Временные файлы удалены")
        await status_msg.delete()
        
    except TikTokBlockError as e:
        logger.warning(f"TikTok заблокировал запрос от {message.from_user.id}: {url}")
        await status_msg.edit_text(f"⚠️ {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке TikTok {url}: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при загрузке: {str(e)}")
