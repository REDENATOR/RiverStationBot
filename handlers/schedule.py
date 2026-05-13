"""Управление расписанием: добавление новых рейсов (только админ)"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Route, Schedule
from config import ADMIN_ID

# Состояния для добавления расписания
ASK_SCHEDULE_ROUTE, ASK_SCHEDULE_DATETIME, ASK_SCHEDULE_SEATS = range(17, 20)


# ==========================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КНОПОК С МАРШРУТАМИ
# ==========================================

def get_routes_keyboard():
    """
    Создаёт inline-клавиатуру со списком всех маршрутов.
    Каждая кнопка при нажатии отправляет callback_data вида "route_{route_id}"
    """
    session = Session()
    routes = session.query(Route).all()
    session.close()

    if not routes:
        return None

    keyboard = []
    for route in routes:
        # Создаём кнопку с информацией о маршруте
        button = InlineKeyboardButton(
            text=f"🚢 {route.origin} → {route.destination} ({route.base_price} руб.)",
            callback_data=f"route_{route.route_id}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)


def get_routes_list_text():
    """Возвращает строку со списком всех маршрутов (для текстового сообщения)"""
    session = Session()
    routes = session.query(Route).all()
    session.close()

    if not routes:
        return "❌ В базе пока нет маршрутов. Сначала добавьте маршрут командой /add_route"

    text = "📋 *Доступные маршруты:*\n\n"
    for r in routes:
        text += f"🚢 ID: {r.route_id}\n"
        text += f"📍 {r.origin} → {r.destination}\n"
        text += f"⏱ Длительность: {r.duration} минут\n"
        text += f"💰 Цена: {r.base_price} руб.\n\n"
    return text


# ==========================================
# НАЧАЛО ДОБАВЛЕНИЯ РАСПИСАНИЯ
# ==========================================

async def add_schedule_start(update: Update, context):
    """
    Команда /add_schedule — начало добавления нового рейса.
    Доступно только администратору.
    """
    user_id = update.effective_user.id

    # Проверка прав администратора
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может добавлять новые рейсы."
        )
        return ConversationHandler.END

    # Проверяем, есть ли вообще маршруты в базе данных
    session = Session()
    routes_count = session.query(Route).count()
    session.close()

    if routes_count == 0:
        await update.message.reply_text(
            "❌ Нет доступных маршрутов!\n\n"
            "Сначала добавьте маршрут командой /add_route,\n"
            "а потом создавайте расписание."
        )
        return ConversationHandler.END

    # Создаём клавиатуру с кнопками маршрутов
    keyboard = get_routes_keyboard()

    if keyboard is None:
        await update.message.reply_text(
            "❌ Нет доступных маршрутов!\n\n"
            "Сначала добавьте маршрут командой /add_route"
        )
        return ConversationHandler.END

    # Сохраняем список маршрутов в context.user_data для проверки позже
    session = Session()
    routes = session.query(Route).all()
    session.close()
    context.user_data['available_routes'] = {r.route_id: f"{r.origin} → {r.destination}" for r in routes}

    # Отправляем сообщение с кнопками
    await update.message.reply_text(
        "📅 *Добавление нового рейса* 📅\n\n"
        "📋 *Выберите маршрут* из списка ниже, нажав на кнопку:\n\n"
        "Для отмены напишите /cancel",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return ASK_SCHEDULE_ROUTE


# ==========================================
# ШАГ 1: ОБРАБОТКА ВЫБОРА МАРШРУТА (НАЖАТИЕ НА КНОПКУ)
# ==========================================

async def process_route_selection(update: Update, context):
    """
    Обрабатывает нажатие на кнопку с выбором маршрута.
    """
    query = update.callback_query
    await query.answer()

    # Разбираем callback_data вида "route_123"
    route_id = int(query.data.split('_')[1])

    # Получаем название маршрута из сохранённого словаря
    routes_dict = context.user_data.get('available_routes', {})
    route_name = routes_dict.get(route_id, "Неизвестный маршрут")

    # Сохраняем ID маршрута
    context.user_data['selected_route_id'] = route_id
    context.user_data['selected_route_name'] = route_name

    # Редактируем сообщение, убирая кнопки
    await query.edit_message_text(
        f"✅ Выбран маршрут: *{route_name}*\n\n"
        f"📅 *Введите дату и время отправления* в формате:\n"
        f"`ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
        f"Примеры:\n"
        f"• `25.12.2025 10:00`\n"
        f"• `01.01.2026 15:30`\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_SCHEDULE_DATETIME


# ==========================================
# ШАГ 2: ПОЛУЧЕНИЕ ДАТЫ И ВРЕМЕНИ
# ==========================================

async def get_schedule_datetime(update: Update, context):
    """Получает дату и время отправления рейса"""
    datetime_str = update.message.text.strip()

    # Проверяем формат даты
    try:
        # Пробуем распарсить введённую строку
        departure_time = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты и времени!\n\n"
            "Используйте формат: `ДД.ММ.ГГГГ ЧЧ:ММ`\n\n"
            "Примеры:\n"
            "• `25.12.2025 10:00`\n"
            "• `01.01.2026 15:30`\n\n"
            "Попробуйте ещё раз:",
            parse_mode='Markdown'
        )
        return ASK_SCHEDULE_DATETIME

    # Проверяем, что дата не в прошлом
    if departure_time < datetime.now():
        await update.message.reply_text(
            "❌ Нельзя создать рейс в прошлом!\n\n"
            "Дата и время должны быть в будущем.\n\n"
            "Введите корректную дату и время:"
        )
        return ASK_SCHEDULE_DATETIME

    # Сохраняем дату и время
    context.user_data['departure_time'] = departure_time

    await update.message.reply_text(
        f"✅ Дата и время: *{departure_time.strftime('%d.%m.%Y %H:%M')}*\n\n"
        f"🪑 *Введите количество свободных мест* на рейсе.\n"
        f"Примеры: 40, 60, 100\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_SCHEDULE_SEATS


# ==========================================
# ШАГ 3: ПОЛУЧЕНИЕ КОЛИЧЕСТВА МЕСТ И СОХРАНЕНИЕ РЕЙСА
# ==========================================

async def get_schedule_seats(update: Update, context):
    """Получает количество мест и сохраняет рейс в базу данных"""
    try:
        available_seats = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (количество мест).\n"
            "Примеры: 40, 60, 100\n\n"
            "Попробуйте ещё раз:"
        )
        return ASK_SCHEDULE_SEATS

    if available_seats < 1:
        await update.message.reply_text(
            "❌ Количество мест должно быть не менее 1.\n"
            "Введите корректное значение:"
        )
        return ASK_SCHEDULE_SEATS

    if available_seats > 500:
        await update.message.reply_text(
            "❌ Количество мест не может превышать 500.\n"
            "Введите корректное значение:"
        )
        return ASK_SCHEDULE_SEATS

    # Получаем все сохранённые данные из context.user_data
    route_id = context.user_data.get('selected_route_id')
    route_name = context.user_data.get('selected_route_name')
    departure_time = context.user_data.get('departure_time')

    # Проверяем, что все данные есть
    if not all([route_id, departure_time]):
        await update.message.reply_text(
            "❌ Ошибка: потеряны данные. Начните заново с /add_schedule"
        )
        return ConversationHandler.END

    # === СОЗДАЁМ НОВЫЙ РЕЙС ===
    session = Session()

    # Проверка на дубликат (такой же маршрут в то же время)
    existing = session.query(Schedule).filter_by(
        route_id=route_id,
        departure_time=departure_time
    ).first()

    if existing:
        await update.message.reply_text(
            f"❌ Рейс на маршрут '{route_name}' в {departure_time.strftime('%d.%m.%Y %H:%M')} уже существует!\n\n"
            f"📋 Существующий рейс:\n"
            f"   • Свободных мест: {existing.available_seats}\n\n"
            f"Используйте другое время."
        )
        session.close()
        return ConversationHandler.END

    # Создаём новый рейс
    new_schedule = Schedule(
        route_id=route_id,
        departure_time=departure_time,
        available_seats=available_seats
    )

    session.add(new_schedule)
    session.commit()
    session.close()

    # Очищаем временные данные
    context.user_data.clear()

    # Отправляем подтверждение
    await update.message.reply_text(
        f"✅ *РЕЙС УСПЕШНО ДОБАВЛЕН!* ✅\n\n"
        f"🚢 Маршрут: {route_name}\n"
        f"📅 Дата и время: {departure_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"🪑 Свободных мест: {available_seats}\n\n"
        f"Теперь пользователи могут купить билеты на этот рейс!"
    )

    return ConversationHandler.END