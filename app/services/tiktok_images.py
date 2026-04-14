import os
import httpx
from typing import Callable, Optional
from loguru import logger

async def download_tiktok_images(
    url: str,
    save_dir: str,
    log: Optional[Callable[[str], None]] = None,
) -> list[str] | None:
    """
    Скачивает изображения из TikTok фото-поста через tikwm.com API.
    Адаптировано для использования в боте.
    """
    TIKWM_API = "https://www.tikwm.com/api/"
    
    # Используем логгер проекта, если функция лога не передана
    def write_log(msg: str):
        if log:
            log(msg)
        else:
            logger.info(msg)

    # --- Шаг 1: Запрос к tikwm API ---
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(TIKWM_API, data={"url": url, "hd": "1"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        write_log(f"[ERROR] tikwm API request failed: {e}")
        return None

    # --- Шаг 2: Проверка ответа ---
    if data.get("code") != 0:
        write_log(f"[ERROR] tikwm API error: {data.get('msg')}")
        return None

    post_data = data.get("data", {})
    image_urls: list[str] = post_data.get("images", [])

    if not image_urls:
        write_log("[WARN] tikwm: no images in response (not a photo post?)")
        return None

    write_log(f"tikwm: found {len(image_urls)} image(s), downloading...")

    # --- Шаг 3: Скачивание каждого изображения ---
    downloaded: list[str] = []
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for i, img_url in enumerate(image_urls):
            try:
                r = await client.get(img_url)
                r.raise_for_status()

                ct = r.headers.get("content-type", "")
                if "jpeg" in ct or "jpg" in ct:
                    ext = "jpg"
                elif "png" in ct:
                    ext = "png"
                elif "webp" in ct:
                    ext = "webp"
                else:
                    ext = "jpg"

                fpath = os.path.join(save_dir, f"tt_img_{i + 1:03d}.{ext}")
                with open(fpath, "wb") as f:
                    f.write(r.content)
                downloaded.append(fpath)

            except Exception as e:
                write_log(f"[WARN] Failed to download image {i + 1}: {e}")

    if not downloaded:
        write_log("[ERROR] No TikTok images downloaded")
        return None

    write_log(f"TikTok images downloaded: {len(downloaded)} file(s)")
    return downloaded
