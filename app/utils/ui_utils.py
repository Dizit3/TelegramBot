def create_progress_bar(percentage: float, length: int = 10) -> str:
    """Создает визуальный прогресс-бар."""
    filled_length = int(length * percentage // 100)
    bar = "▓" * filled_length + "░" * (length - filled_length)
    return f"[{bar}] {int(percentage)}%"
