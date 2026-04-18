import json
import os

from app.core import config

SETTINGS_FILE = os.path.join(config.BASE_DIR, "settings.json")


class UserSettings:
    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get_mode(self, user_id: int):
        """Возвращает режим пользователя: 'video' (слайдшоу) или 'images' (альбом)"""
        return self.settings.get(str(user_id), {}).get("mode", "video")

    def set_mode(self, user_id: int, mode: str):
        if str(user_id) not in self.settings:
            self.settings[str(user_id)] = {}
        self.settings[str(user_id)]["mode"] = mode
        self._save_settings()

    def toggle_mode(self, user_id: int) -> str:
        """Переключает режим пользователя (images <-> video) и возвращает новый."""
        current = self.get_mode(user_id)
        new_mode = "images" if current == "video" else "video"
        self.set_mode(user_id, new_mode)
        return new_mode


user_settings = UserSettings()
