@echo off
title TikTok Telegram Bot
echo Starting TikTok Telegram Bot...

:: Проверяем, установлен ли Python через команду 'py'
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py main.py
) else (
    :: Если 'py' нет, пробуем 'python'
    python main.py
)

pause
