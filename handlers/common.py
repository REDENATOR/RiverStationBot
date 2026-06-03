"""Общие функции: клавиатуры, отмена, кнопки"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler
from config import ADMIN_ID

# ==========================================
# КЛАВИАТУРЫ
# ==========================================

def main_keyboard():
    """Главная клавиатура для обычных пользователей"""
    buttons = [["🚢 Купить билет"], ["📋 Мои билеты"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def admin_keyboard():
    """
    Административная клавиатура.
    Показывается только администратору.
    """
    buttons = [
        ["🚢 Купить билет", "📋 Мои билеты"],
        ["➕ Добавить судно", "🗑 Удалить судно"],  # ← ЭТА СТРОЧКА ДОБАВЛЕНА
        ["🛣 Добавить маршрут", "📅 Добавить рейс"],
        ["📊 Статистика", "🗑 Очистить данные"],
        ["❌ Выйти из админ-меню"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def phone_keyboard():
    """Клавиатура для отправки номера телефона"""
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    button = KeyboardButton("❌ Отмена")
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True)


def back_to_menu_keyboard():
    """Клавиатура с кнопкой возврата в меню"""
    button = KeyboardButton("🏠 В главное меню")
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True)


# ==========================================
# УНИВЕРСАЛЬНЫЙ ОТМЕНА
# ==========================================

async def cancel(update: Update, context):
    """
    Универсальный обработчик отмены для любого диалога.
    Очищает временные данные и возвращает в главное меню.
    """
    context.user_data.clear()

    # Проверяем, является ли пользователь администратором
    user_id = update.effective_user.id
    reply_markup = admin_keyboard() if user_id == ADMIN_ID else main_keyboard()

    await update.message.reply_text(
        "❌ Действие отменено. ❌\n\nВы вернулись в главное меню.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def cancel_with_button(update: Update, context):
    """
    Обработчик отмены по кнопке "❌ Отмена".
    """
    return await cancel(update, context)


# ==========================================
# ПЕРЕКЛЮЧЕНИЕ МЕЖДУ МЕНЮ
# ==========================================

async def show_admin_menu(update: Update, context):
    """Показывает админ-меню (доступно только администратору)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет доступа к админ-панели.",
            reply_markup=main_keyboard()
        )
        return

    await update.message.reply_text(
        "👑 *Административная панель* 👑\n\n"
        "Доступные действия:\n"
        "• ➕ Добавить судно\n"
        "• 🛣 Добавить маршрут\n"
        "• 📅 Добавить рейс\n"
        "• 📊 Статистика\n"
        "• 🗑 Очистить данные\n\n"
        "Выберите действие на кнопках ниже:",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )


async def exit_admin_menu(update: Update, context):
    """Выход из админ-меню в обычное меню пользователя"""
    await update.message.reply_text(
        "👋 Вы вышли из административной панели.\n\n"
        "Теперь вы в обычном пользовательском меню.",
        reply_markup=main_keyboard()
    )