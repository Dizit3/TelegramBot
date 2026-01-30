import os
import asyncio
import yt_dlp
import aiohttp
from loguru import logger
from app.core.interfaces import IVideoDownloader, VideoInfo
from app.utils.file_manager import generate_temp_path

class TikTokBlockError(Exception):
    """Исключение выбрасывается, когда TikTok блокирует доступ к видео."""
    pass

class TikTokDownloader(IVideoDownloader):
    """Реализация загрузчика TikTok с использованием yt-dlp."""
    
    def __init__(self, download_dir: str = "temp"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    async def _resolve_url(self, url: str) -> str:
        """Резолвим мобильные ссылки TikTok в полные URL."""
        if "vm.tiktok.com" not in url and "vt.tiktok.com" not in url:
            return url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, allow_redirects=True) as response:
                    final_url = str(response.url)
                    # Если TikTok перенаправил на главную или на страницу с ?_r=1, значит он нас заблокировал
                    if "tiktok.com/?_r=1" in final_url or final_url.strip("/") == "https://www.tiktok.com":
                        logger.warning(f"TikTok заблокировал резолв ссылки {url}. Финальный URL: {final_url}")
                        raise TikTokBlockError("TikTok блокирует доступ к этой ссылке. Попробуйте прислать полную ссылку на видео из браузера.")
                        
                    # Избавляемся от параметров запроса
                    final_url = final_url.split('?')[0]
                    logger.debug(f"URL резолвнут: {url} -> {final_url}")
                    return final_url
        except TikTokBlockError:
            raise
        except Exception as e:
            logger.warning(f"Ошибка при резолве URL {url}: {e}")
            return url

    async def download(self, url: str) -> VideoInfo:
        """Загрузка видео в асинхронном режиме."""
        url = await self._resolve_url(url)
        loop = asyncio.get_event_loop()
        
        # Генерация уникального пути для сохранения
        file_path = generate_temp_path(self.download_dir, "mp4")
        
        ydl_opts = {
            'outtmpl': file_path,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.tiktok.com/',
            'socket_timeout': 15,
            'timeout': 30,
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        # Запускаем блокирующую операцию yt-dlp в отдельном потоке
        def _download():
            logger.debug(f"Запуск yt-dlp для URL: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    logger.info(f"Информация о видео извлечена: {info.get('title')}")
                    return info
                except Exception as e:
                    logger.error(f"Ошибка yt-dlp: {e}")
                    raise

        try:
            info = await loop.run_in_executor(None, _download)
            logger.success(f"Загрузка завершена: {file_path}")
        except Exception as e:
            logger.exception("Не удалось загрузить видео через yt-dlp")
            raise
        return VideoInfo(
            file_path=file_path,
            title=info.get('title'),
            duration=info.get('duration'),
            thumbnail_url=info.get('thumbnail')
        )

    async def cleanup(self, file_path: str) -> None:
        """Удаление временного файла."""
        if os.path.exists(file_path):
            os.remove(file_path)
