"""Управление маршрутами: добавление новых маршрутов (только админ)"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Vessel, Route
from config import ADMIN_ID

# Состояния для добавления маршрута
ASK_ROUTE_VESSEL, ASK_ROUTE_ORIGIN, ASK_ROUTE_DESTINATION, ASK_ROUTE_DURATION, ASK_ROUTE_PRICE = range(12, 17)


# ==========================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ СОЗДАНИЯ КНОПОК С СУДАМИ
# ==========================================

def get_vessels_keyboard():
    """
    Создаёт inline-клавиатуру со списком всех судов.
    Каждая кнопка при нажатии отправляет callback_data вида "vessel_123"
    """
    session = Session()
    vessels = session.query(Vessel).all()
    session.close()

    if not vessels:
        return None

    keyboard = []
    for vessel in vessels:
        # Создаём кнопку с названием судна и его вместимостью
        button = InlineKeyboardButton(
            text=f"🚢 {vessel.name} ({vessel.capacity} мест)",
            callback_data=f"vessel_{vessel.vessel_id}_{vessel.name}"
        )
        keyboard.append([button])  # Каждая кнопка в отдельном ряду

    return InlineKeyboardMarkup(keyboard)


def get_vessels_list_text():
    """Возвращает строку со списком всех судов (для текстового сообщения)"""
    session = Session()
    vessels = session.query(Vessel).all()
    session.close()

    if not vessels:
        return "❌ В базе пока нет судов. Сначала добавьте судно командой /add_vessel"

    text = "📋 *Доступные суда:*\n"
    for v in vessels:
        text += f"   • {v.name} (вместимость: {v.capacity} мест)\n"
    return text


# ==========================================
# НАЧАЛО ДОБАВЛЕНИЯ МАРШРУТА
# ==========================================

async def add_route_start(update: Update, context):
    """
    Команда /add_route — начало добавления нового маршрута.
    Доступно только администратору.
    """
    user_id = update.effective_user.id

    # Проверка прав администратора
    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может добавлять новые маршруты."
        )
        return ConversationHandler.END

    # Проверяем, есть ли вообще суда в базе данных
    session = Session()
    vessels_count = session.query(Vessel).count()
    session.close()

    if vessels_count == 0:
        await update.message.reply_text(
            "❌ Нет доступных судов!\n\n"
            "Сначала добавьте судно командой /add_vessel,\n"
            "а потом создавайте маршруты."
        )
        return ConversationHandler.END

    # Создаём клавиатуру с кнопками судов
    keyboard = get_vessels_keyboard()

    if keyboard is None:
        await update.message.reply_text(
            "❌ Нет доступных судов!\n\n"
            "Сначала добавьте судно командой /add_vessel"
        )
        return ConversationHandler.END

    # Сохраняем список судов в context.user_data для проверки позже
    session = Session()
    vessels = session.query(Vessel).all()
    session.close()
    context.user_data['available_vessels'] = {v.name: v.vessel_id for v in vessels}

    # Отправляем сообщение с кнопками
    await update.message.reply_text(
        "🚢 *Добавление нового маршрута* 🚢\n\n"
        "📋 *Выберите судно* из списка ниже, нажав на кнопку:\n\n"
        "Для отмены напишите /cancel",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return ASK_ROUTE_VESSEL


# ==========================================
# ШАГ 1: ОБРАБОТКА ВЫБОРА СУДНА (НАЖАТИЕ НА КНОПКУ)
# ==========================================

async def process_vessel_selection(update: Update, context):
    """
    Обрабатывает нажатие на кнопку с выбором судна.
    Извлекает ID и название судна из callback_data.
    """
    query = update.callback_query
    await query.answer()  # Убираем "часики" загрузки

    # Разбираем callback_data вида "vessel_123_Метеор-120"
    data_parts = query.data.split('_')
    vessel_id = int(data_parts[1])
    vessel_name = '_'.join(data_parts[2:])  # На случай если в названии есть подчёркивания

    # Сохраняем данные судна
    context.user_data['route_vessel_id'] = vessel_id
    context.user_data['route_vessel_name'] = vessel_name

    # Получаем вместимость судна (для информации)
    session = Session()
    vessel = session.query(Vessel).filter_by(vessel_id=vessel_id).first()
    session.close()
    context.user_data['route_vessel_capacity'] = vessel.capacity if vessel else 0

    # Редактируем сообщение, убирая кнопки
    await query.edit_message_text(
        f"✅ *Выбрано судно:* {vessel_name} (вместимость: {vessel.capacity if vessel else '?'} мест)\n\n"
        f"📍 *Введите пункт отправления* (откуда идёт маршрут).\n"
        f"Примеры: «Речной вокзал», «Причал №5», «Саратов»\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )

    return ASK_ROUTE_ORIGIN


# ==========================================
# ШАГ 2: ПОЛУЧЕНИЕ ПУНКТА ОТПРАВЛЕНИЯ
# ==========================================

async def get_route_origin(update: Update, context):
    """Получает пункт отправления маршрута"""
    route_origin = update.message.text.strip()

    if len(route_origin) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите пункт отправления ещё раз:"
        )
        return ASK_ROUTE_ORIGIN

    context.user_data['route_origin'] = route_origin

    await update.message.reply_text(
        f"✅ Пункт отправления: *{route_origin}*\n\n"
        f"📍 *Введите пункт назначения* (куда идёт маршрут).\n"
        f"Примеры: «Зеленогорск», «Солнечный берег», «Москва»\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_ROUTE_DESTINATION


# ==========================================
# ШАГ 3: ПОЛУЧЕНИЕ ПУНКТА НАЗНАЧЕНИЯ
# ==========================================

async def get_route_destination(update: Update, context):
    """Получает пункт назначения маршрута"""
    route_destination = update.message.text.strip()

    if len(route_destination) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите пункт назначения ещё раз:"
        )
        return ASK_ROUTE_DESTINATION

    context.user_data['route_destination'] = route_destination

    await update.message.reply_text(
        f"✅ Пункт назначения: *{route_destination}*\n\n"
        f"⏱ *Введите длительность маршрута* в минутах.\n"
        f"Примеры: 45, 60, 120\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_ROUTE_DURATION


# ==========================================
# ШАГ 4: ПОЛУЧЕНИЕ ДЛИТЕЛЬНОСТИ
# ==========================================

async def get_route_duration(update: Update, context):
    """Получает длительность маршрута в минутах"""
    try:
        duration = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (количество минут).\n"
            "Примеры: 45, 60, 120\n\n"
            "Попробуйте ещё раз:"
        )
        return ASK_ROUTE_DURATION

    if duration < 1:
        await update.message.reply_text(
            "❌ Длительность должна быть не менее 1 минуты.\n"
            "Введите корректное значение:"
        )
        return ASK_ROUTE_DURATION

    if duration > 1440:  # максимум сутки
        await update.message.reply_text(
            "❌ Длительность не может превышать 1440 минут (24 часа).\n"
            "Введите корректное значение:"
        )
        return ASK_ROUTE_DURATION

    context.user_data['route_duration'] = duration

    await update.message.reply_text(
        f"✅ Длительность: *{duration}* минут\n\n"
        f"💰 *Введите цену билета* в рублях.\n"
        f"Примеры: 450, 300, 1000\n\n"
        f"Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_ROUTE_PRICE


# ==========================================
# ШАГ 5: ПОЛУЧЕНИЕ ЦЕНЫ И СОХРАНЕНИЕ МАРШРУТА
# ==========================================

async def get_route_price(update: Update, context):
    """Получает цену билета и сохраняет маршрут в базу данных"""
    try:
        price = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число (цену в рублях).\n"
            "Примеры: 450, 300, 1000\n\n"
            "Попробуйте ещё раз:"
        )
        return ASK_ROUTE_PRICE

    if price < 1:
        await update.message.reply_text(
            "❌ Цена должна быть не менее 1 рубля.\n"
            "Введите корректное значение:"
        )
        return ASK_ROUTE_PRICE

    if price > 100000:
        await update.message.reply_text(
            "❌ Цена не может превышать 100 000 рублей.\n"
            "Введите корректное значение:"
        )
        return ASK_ROUTE_PRICE

    # Получаем все сохранённые данные из context.user_data
    vessel_id = context.user_data.get('route_vessel_id')
    vessel_name = context.user_data.get('route_vessel_name')
    origin = context.user_data.get('route_origin')
    destination = context.user_data.get('route_destination')
    duration = context.user_data.get('route_duration')

    # Проверяем, что все данные есть
    if not all([vessel_id, origin, destination, duration]):
        await update.message.reply_text(
            "❌ Ошибка: потеряны данные. Начните заново с /add_route"
        )
        return ConversationHandler.END

    # === СОЗДАЁМ НОВЫЙ МАРШРУТ ===
    session = Session()

    # Проверка на дубликат
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
            f"   • Цена: {existing.base_price} руб.\n\n"
            f"Используйте другие данные."
        )
        session.close()
        return ConversationHandler.END

    # Создаём новый маршрут
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

    # Очищаем временные данные
    context.user_data.clear()

    # Отправляем подтверждение
    await update.message.reply_text(
        f"✅ МАРШРУТ УСПЕШНО ДОБАВЛЕН! ✅\n\n"
        f"🚢 Судно: {vessel_name}\n"
        f"📍 {origin} → {destination}\n"
        f"⏱ Длительность: {duration} минут\n"
        f"💰 Цена: {price} руб.\n\n"
        f"Теперь вы можете создать расписание для этого маршрута.\n"
        f"Используйте команду /add_schedule"
    )

    return ConversationHandler.END


