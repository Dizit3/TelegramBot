# Используем легковесный образ Python
FROM python:3.11-slim

# Установка системных зависимостей (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости Python
# Мы делаем это отдельным шагом для кэширования слоев Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Создаем папки для логов и временных файлов (на случай если они не привязаны как volume)
RUN mkdir -p logs temp

# Команда для запуска бота
CMD ["python", "main.py"]
