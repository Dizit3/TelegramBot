import os
import uuid

def generate_temp_path(directory: str, extension: str) -> str:
    """Генерирует уникальный путь для временного файла."""
    filename = f"{uuid.uuid4()}.{extension}"
    return os.path.join(directory, filename)
