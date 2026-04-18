from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from app.utils.user_settings import user_settings

router = Router()

def get_settings_keyboard(user_id: int):
    mode = user_settings.get_mode(user_id)
    
    # Кнопки с отметкой текущего режима
    video_text = "✅ Видео-слайдшоу" if mode == "video" else "Видео-слайдшоу"
    images_text = "✅ Альбом фото" if mode == "images" else "Альбом фото"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=video_text, callback_data="set_mode:video")],
        [InlineKeyboardButton(text=images_text, callback_data="set_mode:images")]
    ])
    return keyboard

@router.message(Command("mode"))
async def mode_command_handler(message: Message):
    await message.answer(
        "Выберите, в каком виде вы хотите получать фото-посты из TikTok:",
        reply_markup=get_settings_keyboard(message.from_user.id)
    )

@router.callback_query(F.data.startswith("set_mode:"))
async def set_mode_callback(callback: CallbackQuery):
    mode = callback.data.split(":")[1]
    user_settings.set_mode(callback.from_user.id, mode)
    
    mode_str = "Видео-слайдшоу" if mode == "video" else "Альбом фото"
    await callback.answer(f"Режим изменен на: {mode_str}")
    
    # Обновляем сообщение с кнопками
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_settings_keyboard(callback.from_user.id)
        )
    except Exception:
        pass
