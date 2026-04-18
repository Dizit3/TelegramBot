import os
import httpx
from typing import Callable, Optional
from loguru import logger

async def download_tiktok_images(
    url: str,
    save_dir: str,
    log: Optional[Callable[[str], None]] = None,
) -> tuple[list[str], Optional[str]] | None:
    """
    Скачивает изображения и аудио из TikTok фото-поста через tikwm.com API.
    Возвращает (список_путей_к_фото, путь_к_аудио) или None.
    """
    TIKWM_API = "https://www.tikwm.com/api/"
    
    def write_log(msg: str):
        if log:
            log(msg)
        else:
            logger.info(msg)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(TIKWM_API, data={"url": url, "hd": "1"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        write_log(f"[ERROR] tikwm API request failed: {e}")
        return None

    if data.get("code") != 0:
        write_log(f"[ERROR] tikwm API error: {data.get('msg')}")
        return None

    post_data = data.get("data", {})
    logger.debug(f"Tikwm API data: {post_data}")
    
    image_urls: list[str] = post_data.get("images", [])
    
    # Безопасное извлечение ссылки на музыку
    audio_url = None
    music_data = post_data.get("music")
    music_info = post_data.get("music_info")
    
    # Сначала пробуем 'play', потом 'play_url' в обоих объектах
    if isinstance(music_info, dict):
        audio_url = music_info.get("play") or music_info.get("play_url")
    
    if not audio_url and isinstance(music_data, dict):
        audio_url = music_data.get("play") or music_data.get("play_url")
    
    if not audio_url:
        write_log("[WARN] tikwm: Audio URL not found in API response")

    if not image_urls:
        write_log("[WARN] tikwm: no images in response")
        return None

    write_log(f"tikwm: found {len(image_urls)} images and audio, downloading...")

    downloaded_images: list[str] = []
    audio_path: Optional[str] = None

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Скачиваем картинки
        for i, img_url in enumerate(image_urls):
            try:
                r = await client.get(img_url)
                r.raise_for_status()
                ct = r.headers.get("content-type", "")
                ext = "jpg"
                if "png" in ct: ext = "png"
                elif "webp" in ct: ext = "webp"
                
                fpath = os.path.join(save_dir, f"tt_img_{i + 1:03d}.{ext}")
                with open(fpath, "wb") as f:
                    f.write(r.content)
                downloaded_images.append(fpath)
            except Exception as e:
                write_log(f"[WARN] Failed to download image {i + 1}: {e}")

        # Скачиваем аудио
        if audio_url:
            try:
                r = await client.get(audio_url)
                r.raise_for_status()
                audio_path = os.path.join(save_dir, "tt_audio.mp3")
                with open(audio_path, "wb") as f:
                    f.write(r.content)
            except Exception as e:
                write_log(f"[WARN] Failed to download audio: {e}")

    if not downloaded_images:
        return None

    return downloaded_images, audio_path
