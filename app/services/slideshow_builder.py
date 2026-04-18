import os
import asyncio
import math
from typing import Optional, List
from loguru import logger
from app.utils.file_manager import generate_temp_path

async def get_audio_duration(audio_path: str) -> float:
    """Определяет длительность аудиофайла с помощью ffprobe."""
    if not audio_path or not os.path.exists(audio_path):
        return 0.0
    
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audio_path
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return float(stdout.decode().strip())
    except Exception as e:
        logger.error(f"Error getting audio duration: {e}")
    
    return 0.0

async def create_slideshow(
    image_paths: List[str],
    audio_path: Optional[str],
    output_dir: str
) -> str | None:
    """
    Создает видео-слайдшоу через -filter_complex. 
    Рассчитывает длительность слайдов (3-5 сек) и зацикливает их под длину аудио.
    Совместимо со старыми версиями ffmpeg.
    """
    if not image_paths:
        return None

    output_path = generate_temp_path(output_dir, "mp4")
    fps = 25
    
    # 1. Получаем длительность аудио и рассчитываем тайминги
    audio_duration = await get_audio_duration(audio_path)
    if audio_duration == 0:
        audio_duration = 3.0 * len(image_paths) # Дефолт если нет звука
        
    num_original_photos = len(image_paths)
    
    # Расчет времени на один слайд (3-5 сек)
    ideal_slide_dur = audio_duration / num_original_photos
    slide_dur = min(5.0, max(3.0, ideal_slide_dur))
    
    cycle_dur = num_original_photos * slide_dur
    
    # Ограничение "макс 2 круга": не более 10 секунд на каждое уникальное фото в сумме
    max_loops_dur = num_original_photos * 10.0
    
    # Определяем финальную длину видео:
    # Берем аудио, но не длиннее 60 сек и не длиннее "лимита кругов"
    # При этом видео не может быть короче одного минимального цикла (3 сек на фото)
    final_video_dur = max(num_original_photos * 3.0, min(60.0, audio_duration, max_loops_dur))
    
    # Регулируем slide_dur так, чтобы он вписывался в итоговое время или был в пределах 3-5 сек
    if final_video_dur > cycle_dur and final_video_dur <= audio_duration:
        # Если мы растягиваем до аудио
        slide_dur = min(5.0, max(3.0, final_video_dur / num_original_photos))
        cycle_dur = num_original_photos * slide_dur
    
    # Пересчитываем количество циклов для видео
    num_v_cycles = math.ceil(final_video_dur / cycle_dur)
    final_image_list = image_paths * num_v_cycles
    
    logger.info(f"Slideshow: audio={audio_duration}s, max_loop_limit={max_loops_dur}s, slide={slide_dur}s, total={final_video_dur}s")
    
    # Сколько раз нужно повторить аудио (для старых ffmpeg, где нет -stream_loop)
    num_a_repeats = 1
    if audio_path and audio_duration > 0:
        num_a_repeats = math.ceil(final_video_dur / audio_duration)

    try:
        # ПЕРВАЯ ЧАСТЬ: Формируем входы
        cmd = ["ffmpeg", "-y"]
        
        # Добавляем фото
        for path in final_image_list:
            cmd.extend(["-loop", "1", "-t", str(slide_dur), "-i", path])
        
        # Добавляем аудио нужное количество раз
        has_audio = audio_path and os.path.exists(audio_path)
        if has_audio:
            for _ in range(num_a_repeats):
                cmd.extend(["-i", audio_path])
        
        first_img_idx = 0
        first_audio_idx = len(final_image_list)

        # ВТОРАЯ ЧАСТЬ: Формируем -filter_complex
        filter_parts = []
        
        # Обработка видео (масштабирование)
        num_total_v_frames = len(final_image_list)
        for i in range(num_total_v_frames):
            out_label = "[v_out]" if num_total_v_frames == 1 else f"[v{i}]"
            part = (
                f"[{i}:v]scale=720:1280:force_original_aspect_ratio=decrease,"
                f"pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}{out_label}"
            )
            filter_parts.append(part)
        
        # Склейка видео
        if num_total_v_frames > 1:
            concat_v_in = "".join([f"[v{i}]" for i in range(num_total_v_frames)])
            filter_parts.append(f"{concat_v_in}concat=n={num_total_v_frames}:v=1:a=0[v_out]")
        
        # Склейка аудио (если его больше одного)
        if has_audio:
            if num_a_repeats > 1:
                concat_a_in = "".join([f"[{first_audio_idx + j}:a]" for j in range(num_a_repeats)])
                filter_parts.append(f"{concat_a_in}concat=n={num_a_repeats}:v=0:a=1[a_out]")
            else:
                filter_parts.append(f"[{first_audio_idx}:a]anull[a_out]")
        
        cmd.extend(["-filter_complex", ";".join(filter_parts)])

        # ТРЕТЬЯ ЧАСТЬ: Мапинг и финализация
        cmd.extend(["-map", "[v_out]"])
        if has_audio:
            cmd.extend(["-map", "[a_out]", "-c:a", "aac", "-strict", "-2"])
        
        cmd.extend(["-t", str(final_video_dur)])
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", output_path
        ])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None
            
        logger.success(f"Слайдшоу создано: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Ошибка при сборке слайдшоу: {e}")
        return None
