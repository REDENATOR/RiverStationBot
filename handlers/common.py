"""Общие функции: клавиатуры, отмена, кнопки"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

# ==========================================
# КЛАВИАТУРЫ
# ==========================================

def main_keyboard():
    """Главная клавиатура с кнопками внизу экрана"""
    buttons = [["🚢 Купить билет"], ["📋 Мои билеты"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def phone_keyboard():
    """Клавиатура для отправки номера телефона"""
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)

# ==========================================
# УНИВЕРСАЛЬНЫЙ ОТМЕНА
# ==========================================

async def cancel(update: Update, context):
    """
    Универсальный обработчик отмены для любого диалога.
    Очищает временные данные и возвращает в главное меню.
    """
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Действие отменено. ❌\n\nВы вернулись в главное меню.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END