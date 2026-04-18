import os
import asyncio
import yt_dlp
import aiohttp
from loguru import logger
from typing import Optional, Callable, Awaitable
from app.core import config
from app.core.interfaces import IVideoDownloader, VideoInfo
from app.utils.file_manager import generate_temp_path
from app.services.tiktok_images import download_tiktok_images
from app.services.slideshow_builder import create_slideshow
from app.utils.user_settings import user_settings

class TikTokBlockError(Exception):
    """Исключение выбрасывается, когда TikTok блокирует доступ к видео."""
    pass

class TikTokDownloader(IVideoDownloader):
    """Реализация загрузчика TikTok с использованием yt-dlp."""
    
    def __init__(self, download_dir: str = config.TEMP_DIR):
        self.download_dir = download_dir

    async def _resolve_url(self, url: str) -> str:
        """Резолвим мобильные ссылки TikTok в полные URL."""
        if "vm.tiktok.com" not in url and "vt.tiktok.com" not in url:
            return url
            
        headers = {'User-Agent': config.YDL_USER_AGENT}
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    final_url = str(response.url)
                    if "tiktok.com/?_r=1" in final_url or final_url.strip("/") == "https://www.tiktok.com":
                        raise TikTokBlockError("TikTok блокирует доступ к этой ссылке. Попробуйте прислать полную ссылку.")
                        
                    final_url = final_url.split('?')[0]
                    return final_url
        except TikTokBlockError:
            raise
        except Exception as e:
            logger.warning(f"Ошибка при резолве URL {url}: {e}")
            return url

    def _get_ydl_opts(self, file_path: str) -> dict:
        """Возвращает настройки yt-dlp."""
        return {
            'outtmpl': file_path,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'user_agent': config.YDL_USER_AGENT,
            'referer': config.YDL_REFERER,
            'socket_timeout': 15,
            'timeout': 30,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

    async def download(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[float], Awaitable[None]]] = None,
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        user_id: Optional[int] = None
    ) -> VideoInfo:
        """Загрузка видео или фото в асинхронном режиме."""
        url = await self._resolve_url(url)
        
        # --- НОВОЕ: Пробуем сначала скачать фото-слайдшоу ---
        logger.debug(f"Проверка на наличие фото-слайдшоу: {url}")
        res = await download_tiktok_images(url, self.download_dir)
        
        if res:
            image_paths, audio_path = res
            logger.success(f"Обнаружен фото-пост: {len(image_paths)} фото")
            
            # Определяем режим пользователя
            mode = user_settings.get_mode(user_id) if user_id else "video"
            
            if mode == "video":
                if status_callback:
                    await status_callback("слайд-шоу (монтаж видео...)")
                
                # Собираем видео через ffmpeg
                video_path = await create_slideshow(image_paths, audio_path, self.download_dir)
                if video_path:
                    # Возвращаем как обычное видео
                    return VideoInfo(
                        file_path=video_path,
                        image_paths=image_paths, # Оставляем для cleanup
                        title="TikTok Slideshow"
                    )
                else:
                    logger.warning("Не удалось собрать слайдшоу, откатываемся к фото-альбому")

            # Режим 'images' или если монтаж видео не удался
            if status_callback:
                await status_callback("слайд-шоу (фото-альбом)")
            return VideoInfo(
                file_path="", 
                image_paths=image_paths,
                title="TikTok Slideshow"
            )
        
        if status_callback:
            await status_callback("видео")
        
        # --- Фолбэк на видео (через yt-dlp) ---
        loop = asyncio.get_event_loop()
        
        file_path = generate_temp_path(self.download_dir, "mp4")
        ydl_opts = self._get_ydl_opts(file_path)

        def _progress_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                if total:
                    percentage = (downloaded / total) * 100
                    asyncio.run_coroutine_threadsafe(progress_callback(percentage), loop)

        if progress_callback:
            ydl_opts['progress_hooks'] = [_progress_hook]

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    return info
                except Exception as e:
                    logger.error(f"Ошибка yt-dlp: {e}")
                    raise

        try:
            info = await loop.run_in_executor(None, _download)
        except Exception as e:
            logger.exception("Не удалось загрузить видео через yt-dlp")
            raise

        return VideoInfo(
            file_path=file_path,
            title=info.get('title'),
            duration=info.get('duration'),
            thumbnail_url=info.get('thumbnail')
        )

    async def cleanup(self, file_path: str, image_paths: Optional[list[str]] = None) -> None:
        """Удаление временных файлов."""
        # Удаляем видео
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем картинки
        if image_paths:
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
