"""Административные команды: добавление тестовых данных"""
from telegram import Update
from telegram.ext import ConversationHandler
from database import add_test_data
from config import ADMIN_ID

async def add_test_data_command(update: Update, context):
    """Добавляет тестовые данные (только админ)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды. ❌")
        return

    add_test_data()
    await update.message.reply_text(
        "✅ *ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО ДОБАВЛЕНЫ!* ✅\n\n"
        "📋 Добавлено:\n"
        "• 🚢 Судно «Метеор-120» (40 мест)\n"
        "• 🗺 Маршруты:\n"
        "   - Речной вокзал → Зеленогорск (450 руб.)\n"
        "   - Речной вокзал → Солнечный берег (300 руб.)\n"
        "• 🕐 Рейсы на завтра в 10:00, 11:00, 12:00, 14:00\n\n"
        "Теперь вы можете купить билет!",
        parse_mode='Markdown'
    )