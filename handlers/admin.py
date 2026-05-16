"""Административные команды: добавление тестовых данных, статистика, очистка"""
from telegram import Update
from telegram.ext import ConversationHandler
from database import Session, User, Ticket, Vessel, Route, Schedule, add_test_data
from config import ADMIN_ID
from handlers.common import admin_keyboard


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
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )


async def show_statistics(update: Update, context):
    """Показывает статистику работы бота (только админ)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав.")
        return

    session = Session()

    # Собираем статистику
    users_count = session.query(User).count()
    tickets_count = session.query(Ticket).count()
    vessels_count = session.query(Vessel).count()
    routes_count = session.query(Route).count()
    schedules_count = session.query(Schedule).count()

    # Количество проданных билетов (paid)
    sold_tickets = session.query(Ticket).filter_by(status='paid').count()

    # Количество активных рейсов (свободные места > 0)
    active_schedules = session.query(Schedule).filter(Schedule.available_seats > 0).count()

    session.close()

    await update.message.reply_text(
        "📊 *СТАТИСТИКА БОТА* 📊\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"🎫 Всего билетов: {tickets_count}\n"
        f"💰 Продано билетов: {sold_tickets}\n"
        f"🚢 Судов: {vessels_count}\n"
        f"🗺 Маршрутов: {routes_count}\n"
        f"📅 Рейсов: {schedules_count}\n"
        f"🟢 Активных рейсов: {active_schedules}\n",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )


async def clear_all_data(update: Update, context):
    """Очищает все данные в базе (только админ)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав.")
        return

    # Запрашиваем подтверждение
    await update.message.reply_text(
        "⚠️ *ВНИМАНИЕ!* ⚠️\n\n"
        "Вы уверены, что хотите удалить ВСЕ данные?\n"
        "Это действие НЕОБРАТИМО!\n\n"
        "Для подтверждения отправьте:\n"
        "`/confirm_clear`\n\n"
        "Для отмены: /cancel",
        parse_mode='Markdown'
    )
    return  # Ждём подтверждения


async def confirm_clear_data(update: Update, context):
    """Подтверждение очистки всех данных"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав.")
        return

    session = Session()

    # Считаем количество записей до удаления
    counts = {
        'билетов': session.query(Ticket).count(),
        'рейсов': session.query(Schedule).count(),
        'маршрутов': session.query(Route).count(),
        'судов': session.query(Vessel).count(),
        'пользователей': session.query(User).count()
    }

    # Удаляем в правильном порядке (сначала зависимые)
    session.query(Ticket).delete()
    session.query(Schedule).delete()
    session.query(Route).delete()
    session.query(Vessel).delete()
    session.query(User).delete()

    session.commit()
    session.close()

    # Формируем отчёт
    report = "🗑 *ВСЕ ДАННЫЕ УДАЛЕНЫ!* 🗑\n\n"
    for name, count in counts.items():
        report += f"• {name}: {count} записей удалено\n"

    await update.message.reply_text(
        report,
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )