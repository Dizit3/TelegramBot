from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class VideoInfo:
    """Модель данных для информации о видео."""
    file_path: str
    title: Optional[str] = None
    duration: Optional[int] = None
    thumbnail_url: Optional[str] = None

class IVideoDownloader(ABC):
    """Интерфейс для загрузчика видео."""
    
    @abstractmethod
    async def download(self, url: str) -> VideoInfo:
        """Загрузить видео по ссылке и вернуть информацию о нем."""
        pass

    @abstractmethod
    async def cleanup(self, file_path: str) -> None:
        """Удалить временный файл видео."""
        pass
