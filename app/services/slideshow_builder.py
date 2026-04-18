import os
import asyncio
from typing import Optional
from loguru import logger
from app.utils.file_manager import generate_temp_path

async def create_slideshow(
    image_paths: list[str],
    audio_path: Optional[str],
    output_dir: str,
    seconds_per_slide: float = 2.5
) -> str | None:
    """
    Создает видео-слайдшоу через -filter_complex. 
    Самый надежный метод для точного контроля длительности каждого кадра.
    """
    if not image_paths:
        return None

    output_path = generate_temp_path(output_dir, "mp4")
    fps = 25
    frames_per_slide = int(seconds_per_slide * fps)
    
    try:
        # 1. Формируем входы
        cmd = ["ffmpeg", "-y"]
        for path in image_paths:
            # -loop 1 позволяет "растягивать" одну картинку
            cmd.extend(["-loop", "1", "-t", str(seconds_per_slide), "-i", path])
        
        if audio_path and os.path.exists(audio_path):
            cmd.extend(["-i", audio_path])

        # 2. Формируем -filter_complex
        # Для каждого входа: scale -> pad -> setsar -> fps
        filter_parts = []
        for i in range(len(image_paths)):
            # Если это единственное фото, назовем выход сразу [v], иначе [v{i}]
            out_label = "[v]" if len(image_paths) == 1 else f"[v{i}]"
            part = (
                f"[{i}:v]scale=720:1280:force_original_aspect_ratio=decrease,"
                f"pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}{out_label}"
            )
            filter_parts.append(part)
        
        # Если фото больше одного, добавляем фильтр склейки (concat)
        if len(image_paths) > 1:
            full_filter = ";".join(filter_parts) + ";"
            concat_input = "".join([f"[v{i}]" for i in range(len(image_paths))])
            concat_filter = f"{concat_input}concat=n={len(image_paths)}:v=1:a=0[v]"
            full_filter += concat_filter
        else:
            full_filter = filter_parts[0]
        
        cmd.extend(["-filter_complex", full_filter])

        # 3. Мапинг и кодеки
        cmd.extend(["-map", "[v]"])
        
        if audio_path and os.path.exists(audio_path):
            # Аудио идет последним входом (индекс len(image_paths))
            cmd.extend(["-map", f"{len(image_paths)}:a:0", "-c:a", "aac", "-strict", "-2", "-shortest"])
        
        cmd.extend([
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", output_path
        ])

        logger.info(f"Запуск ffmpeg (complex filter): {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None
            
        logger.success(f"Слайдшоу создано через FilterComplex: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Ошибка при сборке слайдшоу: {e}")
        return None
