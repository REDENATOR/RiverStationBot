"""Управление расписанием: добавление новых рейсов (только админ)"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Route, Schedule
from config import ADMIN_ID
from handlers.common import admin_keyboard, cancel_keyboard, cancel_with_button


ASK_SCHEDULE_ROUTE, ASK_SCHEDULE_DATETIME, ASK_SCHEDULE_SEATS = range(17, 20)


def get_routes_keyboard():
    """Создаёт inline-клавиатуру со списком всех маршрутов"""
    session = Session()
    routes = session.query(Route).all()
    session.close()

    if not routes:
        return None

    keyboard = []
    for route in routes:
        button = InlineKeyboardButton(
            text=f"🚢 {route.origin} → {route.destination} ({route.base_price} руб.)",
            callback_data=f"route_{route.route_id}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)


async def add_schedule_start(update: Update, context):
    """Команда /add_schedule — начало добавления нового рейса (только админ)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может добавлять новые рейсы."
        )
        return ConversationHandler.END

    session = Session()
    routes_count = session.query(Route).count()
    session.close()

    if routes_count == 0:
        await update.message.reply_text(
            "❌ Нет доступных маршрутов!\n\n"
            "Сначала добавьте маршрут кнопкой «🛣 Добавить маршрут»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    keyboard = get_routes_keyboard()
    if keyboard is None:
        await update.message.reply_text(
            "❌ Нет доступных маршрутов!\n\n"
            "Сначала добавьте маршрут кнопкой «🛣 Добавить маршрут»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    session = Session()
    routes = session.query(Route).all()
    session.close()
    context.user_data['available_routes'] = {r.route_id: f"{r.origin} → {r.destination}" for r in routes}

    await update.message.reply_text(
        "📅 *Добавление нового рейса* 📅\n\n"
        "📋 *Выберите маршрут* из списка ниже, нажав на кнопку:\n\n"
        "Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return ASK_SCHEDULE_ROUTE


async def process_route_selection(update: Update, context):
    """Обрабатывает нажатие на кнопку с выбором маршрута"""
    query = update.callback_query
    await query.answer()

    route_id = int(query.data.split('_')[1])
    routes_dict = context.user_data.get('available_routes', {})
    route_name = routes_dict.get(route_id, "Неизвестный маршрут")

    context.user_data['selected_route_id'] = route_id
    context.user_data['selected_route_name'] = route_name

    await query.edit_message_text(
        f"✅ Выбран маршрут: *{route_name}*\n\n"
        f"📅 *Введите дату и время отправления* в формате:\n"
        f"`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
        f"Примеры:\n"
        f"• `25.12.2025 10:00`\n"
        f"• `01.01.2026 15:30`\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_SCHEDULE_DATETIME


async def get_schedule_datetime(update: Update, context):
    """Получает дату и время отправления рейса"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    datetime_str = update.message.text.strip()

    try:
        departure_time = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты и времени!\n\n"
            "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "Примеры:\n"
            "• `25.12.2025 10:00`\n"
            "• `01.01.2026 15:30`",
            parse_mode='Markdown',
            reply_markup=cancel_keyboard()
        )
        return ASK_SCHEDULE_DATETIME

    if departure_time < datetime.now():
        await update.message.reply_text(
            "❌ Нельзя создать рейс в прошлом!\n\n"
            "Дата и время должны быть в будущем.\n\n"
            "Введите корректную дату и время:",
            reply_markup=cancel_keyboard()
        )
        return ASK_SCHEDULE_DATETIME

    context.user_data['departure_time'] = departure_time

    await update.message.reply_text(
        f"✅ Дата и время: *{departure_time.strftime('%d.%m.%Y %H:%M')}*\n\n"
        f"🪑 *Введите количество свободных мест* на рейсе.\n"
        f"Примеры: 40, 60, 100\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_SCHEDULE_SEATS


async def get_schedule_seats(update: Update, context):
    """Получает количество мест и сохраняет рейс в базу данных"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    try:
        available_seats = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (количество мест).\n"
            "Примеры: 40, 60, 100",
            reply_markup=cancel_keyboard()
        )
        return ASK_SCHEDULE_SEATS

    if available_seats < 1 or available_seats > 500:
        await update.message.reply_text(
            "❌ Количество мест должно быть от 1 до 500.\n"
            "Введите корректное значение:",
            reply_markup=cancel_keyboard()
        )
        return ASK_SCHEDULE_SEATS

    route_id = context.user_data.get('selected_route_id')
    route_name = context.user_data.get('selected_route_name')
    departure_time = context.user_data.get('departure_time')

    if not all([route_id, departure_time]):
        await update.message.reply_text(
            "❌ Ошибка: потеряны данные. Начните заново.",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    session = Session()

    existing = session.query(Schedule).filter_by(
        route_id=route_id,
        departure_time=departure_time
    ).first()

    if existing:
        await update.message.reply_text(
            f"❌ Рейс на маршрут '{route_name}' в {departure_time.strftime('%d.%m.%Y %H:%M')} уже существует!",
            reply_markup=admin_keyboard()
        )
        session.close()
        return ConversationHandler.END

    new_schedule = Schedule(
        route_id=route_id,
        departure_time=departure_time,
        available_seats=available_seats
    )

    session.add(new_schedule)
    session.commit()
    session.close()

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *РЕЙС УСПЕШНО ДОБАВЛЕН!* ✅\n\n"
        f"🚢 Маршрут: {route_name}\n"
        f"📅 Дата и время: {departure_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🪑 Свободных мест: {available_seats}",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

    return ConversationHandler.END