import re
from aiogram import Router, F, html
from aiogram.types import Message, FSInputFile
from aiogram.filters import CommandStart
from loguru import logger

from app.core.interfaces import IVideoDownloader
from app.services.downloader import TikTokDownloader, TikTokBlockError

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
    logger.info(f"Тtiktok_handler: Ссылка найдена: {url}")
    status_msg = await message.answer("⏳ Загружаю видео из TikTok...")
    
    try:
        logger.debug(f"Начало загрузки видео: {url}")
        video_info = await downloader.download(url)
        logger.info(f"Видео успешно загружено: {video_info.file_path}")
        
        await message.answer_video(
            video=FSInputFile(video_info.file_path),
            caption=html.quote(video_info.title) if video_info.title else "Вот ваше видео из TikTok!",
        )
        
        await downloader.cleanup(video_info.file_path)
        logger.debug(f"Временный файл удален: {video_info.file_path}")
        await status_msg.delete()
        
    except TikTokBlockError as e:
        logger.warning(f"TikTok заблокировал запрос от {message.from_user.id}: {url}")
        await status_msg.edit_text(f"⚠️ {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке TikTok {url}: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка при загрузке: {str(e)}")
