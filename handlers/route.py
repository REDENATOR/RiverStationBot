"""Управление маршрутами: добавление новых маршрутов (только админ)"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Vessel, Route
from config import ADMIN_ID
from handlers.common import admin_keyboard, cancel_keyboard, cancel_with_button


# Состояния для добавления маршрута
ASK_ROUTE_VESSEL, ASK_ROUTE_ORIGIN, ASK_ROUTE_DESTINATION, ASK_ROUTE_DURATION, ASK_ROUTE_PRICE = range(12, 17)


def get_vessels_keyboard():
    """Создаёт inline-клавиатуру со списком всех судов"""
    session = Session()
    vessels = session.query(Vessel).all()
    session.close()

    if not vessels:
        return None

    keyboard = []
    for vessel in vessels:
        button = InlineKeyboardButton(
            text=f"🚢 {vessel.name} ({vessel.capacity} мест)",
            callback_data=f"vessel_{vessel.vessel_id}_{vessel.name}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)


async def add_route_start(update: Update, context):
    """Команда /add_route — начало добавления нового маршрута (только админ)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может добавлять новые маршруты."
        )
        return ConversationHandler.END

    session = Session()
    vessels_count = session.query(Vessel).count()
    session.close()

    if vessels_count == 0:
        await update.message.reply_text(
            "❌ Нет доступных судов!\n\n"
            "Сначала добавьте судно кнопкой «➕ Добавить судно»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    keyboard = get_vessels_keyboard()
    if keyboard is None:
        await update.message.reply_text(
            "❌ Нет доступных судов!\n\n"
            "Сначала добавьте судно кнопкой «➕ Добавить судно»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    session = Session()
    vessels = session.query(Vessel).all()
    session.close()
    context.user_data['available_vessels'] = {v.name: v.vessel_id for v in vessels}

    await update.message.reply_text(
        "🚢 *Добавление нового маршрута* 🚢\n\n"
        "📋 *Выберите судно* из списка ниже, нажав на кнопку:\n\n"
        "Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return ASK_ROUTE_VESSEL


async def process_vessel_selection(update: Update, context):
    """Обрабатывает нажатие на кнопку с выбором судна"""
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split('_')
    vessel_id = int(data_parts[1])
    vessel_name = '_'.join(data_parts[2:])

    context.user_data['route_vessel_id'] = vessel_id
    context.user_data['route_vessel_name'] = vessel_name

    session = Session()
    vessel = session.query(Vessel).filter_by(vessel_id=vessel_id).first()
    session.close()
    context.user_data['route_vessel_capacity'] = vessel.capacity if vessel else 0

    await query.edit_message_text(
        f"✅ *Выбрано судно:* {vessel_name} (вместимость: {vessel.capacity if vessel else '?'} мест)\n\n"
        f"📍 *Введите пункт отправления* (откуда идёт маршрут).\n"
        f"Примеры: *Речной вокзал*, *Причал №5*, *Саратов*\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_ROUTE_ORIGIN


async def get_route_origin(update: Update, context):
    """Получает пункт отправления маршрута"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    route_origin = update.message.text.strip()

    if len(route_origin) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите пункт отправления ещё раз:",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_ORIGIN

    context.user_data['route_origin'] = route_origin

    await update.message.reply_text(
        f"✅ Пункт отправления: *{route_origin}*\n\n"
        f"📍 *Введите пункт назначения* (куда идёт маршрут).\n"
        f"Примеры: *Зеленогорск*, *Солнечный берег*, *Москва*\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_ROUTE_DESTINATION


async def get_route_destination(update: Update, context):
    """Получает пункт назначения маршрута"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    route_destination = update.message.text.strip()

    if len(route_destination) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите пункт назначения ещё раз:",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_DESTINATION

    context.user_data['route_destination'] = route_destination

    await update.message.reply_text(
        f"✅ Пункт назначения: *{route_destination}*\n\n"
        f"⏱ *Введите длительность маршрута* в минутах.\n"
        f"Примеры: 45, 60, 120\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_ROUTE_DURATION


async def get_route_duration(update: Update, context):
    """Получает длительность маршрута в минутах"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    try:
        duration = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (количество минут).\n"
            "Примеры: 45, 60, 120",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_DURATION

    if duration < 1 or duration > 1440:
        await update.message.reply_text(
            "❌ Длительность должна быть от 1 до 1440 минут.\n"
            "Введите корректное значение:",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_DURATION

    context.user_data['route_duration'] = duration

    await update.message.reply_text(
        f"✅ Длительность: *{duration}* минут\n\n"
        f"💰 *Введите цену билета* в рублях.\n"
        f"Примеры: 450, 300, 1000\n\n"
        f"Для отмены нажмите кнопку «❌ Отмена»",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_ROUTE_PRICE


async def get_route_price(update: Update, context):
    """Получает цену билета и сохраняет маршрут в базу данных"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    try:
        price = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (цену в рублях).\n"
            "Примеры: 450, 300, 1000",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_PRICE

    if price < 1 or price > 100000:
        await update.message.reply_text(
            "❌ Цена должна быть от 1 до 100 000 рублей.\n"
            "Введите корректное значение:",
            reply_markup=cancel_keyboard()
        )
        return ASK_ROUTE_PRICE

    vessel_id = context.user_data.get('route_vessel_id')
    vessel_name = context.user_data.get('route_vessel_name')
    origin = context.user_data.get('route_origin')
    destination = context.user_data.get('route_destination')
    duration = context.user_data.get('route_duration')

    if not all([vessel_id, origin, destination, duration]):
        await update.message.reply_text(
            "❌ Ошибка: потеряны данные. Начните заново.",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    session = Session()

    existing = session.query(Route).filter_by(
        vessel_id=vessel_id,
        origin=origin,
        destination=destination
    ).first()

    if existing:
        await update.message.reply_text(
            f"❌ Маршрут '{origin} → {destination}' на судне '{vessel_name}' уже существует!\n\n"
            f"📋 Существующий маршрут:\n"
            f"   • Длительность: {existing.duration} мин\n"
            f"   • Цена: {existing.base_price} руб.",
            reply_markup=admin_keyboard()
        )
        session.close()
        return ConversationHandler.END

    new_route = Route(
        vessel_id=vessel_id,
        origin=origin,
        destination=destination,
        duration=duration,
        base_price=price
    )

    session.add(new_route)
    session.commit()
    session.close()

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ *МАРШРУТ УСПЕШНО ДОБАВЛЕН!* ✅\n\n"
        f"🚢 Судно: {vessel_name}\n"
        f"📍 {origin} → {destination}\n"
        f"⏱ Длительность: {duration} минут\n"
        f"💰 Цена: {price} руб.\n\n"
        f"Теперь вы можете создать расписание кнопкой «📅 Добавить рейс»",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

    return ConversationHandler.END