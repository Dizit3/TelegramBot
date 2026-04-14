from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any, Awaitable

@dataclass
class VideoInfo:
    """Модель данных для информации о видео."""
    file_path: str
    title: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None
    image_paths: Optional[list[str]] = None

class IVideoDownloader(ABC):
    """Интерфейс для загрузчика видео."""
    
    async def download(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[float], Awaitable[None]]] = None,
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> VideoInfo:
        """Загрузить видео по ссылке и вернуть информацию о нем."""
        pass

    @abstractmethod
    async def cleanup(self, file_path: str) -> None:
        """Удалить временный файл видео."""
        pass
