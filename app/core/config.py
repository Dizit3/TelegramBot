import os

from dotenv import load_dotenv

load_dotenv()

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Ensure temp directory exists
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Downloader settings
YDL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
YDL_REFERER = "https://www.tiktok.com/"
YDL_TIMEOUT = 30
YDL_SOCKET_TIMEOUT = 15

# API Settings
TIKWM_API_URL = "https://www.tikwm.com/api/"
HTTP_TIMEOUT = 20.0
HTTP_DOWNLOAD_TIMEOUT = 30.0

# Slideshow Settings
SS_FPS = 10
SS_WIDTH = 480
SS_HEIGHT = 854
SS_DEFAULT_SLIDE_DUR = 3.0
SS_MIN_SLIDE_DUR = 3.0
SS_MAX_SLIDE_DUR = 5.0
SS_MAX_VIDEO_DUR = 60.0
SS_MAX_PHOTO_STAY = 10.0  # Максимальное время показа одного фото в сумме (2 круга)

# UI Settings
PROGRESS_BAR_LENGTH = 10
URL_CACHE_SIZE = 100
