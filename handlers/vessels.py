"""Управление судами: добавление и удаление судов (только админ)"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Vessel, Route, Schedule, Ticket
from config import ADMIN_ID
from handlers.common import admin_keyboard, cancel_keyboard, cancel_with_button


# Состояния для добавления судна
ASK_VESSEL_NAME, ASK_VESSEL_CAPACITY = 10, 11

# Состояния для удаления судна
ASK_DELETE_VESSEL_NAME = 20


# ==========================================
# ДОБАВЛЕНИЕ СУДНА
# ==========================================

async def add_vessel_start(update: Update, context):
    """
    Команда /add_vessel — начало добавления нового судна (только админ).
    """
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может добавлять новые суда."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🚢 *Добавление нового судна* 🚢\n\n"
        "Введите название судна.\n"
        "Примеры: *Метеор-200*, *Восход*, *Ракета-90*\n\n"
        "Для отмены нажмите кнопку ниже:",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_VESSEL_NAME


async def get_vessel_name(update: Update, context):
    """Получает название судна"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    vessel_name = update.message.text.strip()

    if len(vessel_name) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите название судна ещё раз:",
            reply_markup=cancel_keyboard()
        )
        return ASK_VESSEL_NAME

    context.user_data['new_vessel_name'] = vessel_name

    await update.message.reply_text(
        f"✅ Название: *{vessel_name}*\n\n"
        "📊 Введите вместимость судна (количество пассажиров).\n"
        "Примеры: 40, 60, 100, 150\n\n"
        "Для отмены нажмите кнопку ниже:",
        parse_mode='Markdown',
        reply_markup=cancel_keyboard()
    )
    return ASK_VESSEL_CAPACITY


async def get_vessel_capacity(update: Update, context):
    """Получает вместимость и сохраняет судно"""
    if update.message.text == "❌ Отмена":
        return await cancel_with_button(update, context)

    try:
        capacity = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Введите число (количество мест).\n"
            "Примеры: 40, 60, 100",
            reply_markup=cancel_keyboard()
        )
        return ASK_VESSEL_CAPACITY

    if capacity < 1 or capacity > 500:
        await update.message.reply_text(
            "❌ Вместимость должна быть от 1 до 500.\n"
            "Введите корректное значение:",
            reply_markup=cancel_keyboard()
        )
        return ASK_VESSEL_CAPACITY

    vessel_name = context.user_data.get('new_vessel_name')
    if not vessel_name:
        await update.message.reply_text(
            "❌ Ошибка: не найдено название.\n"
            "Начните заново с кнопки «➕ Добавить судно»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    session = Session()

    # Проверка на дубликат
    existing = session.query(Vessel).filter_by(name=vessel_name).first()
    if existing:
        await update.message.reply_text(
            f"❌ Судно «{vessel_name}» уже существует!\n"
            f"Вместимость: {existing.capacity} мест",
            reply_markup=admin_keyboard()
        )
        session.close()
        return ConversationHandler.END

    # Создаём новое судно
    new_vessel = Vessel(name=vessel_name, capacity=capacity)
    session.add(new_vessel)
    session.commit()
    session.close()

    await update.message.reply_text(
        f"✅ *Судно успешно добавлено!*\n\n"
        f"🚢 {vessel_name}\n"
        f"👥 {capacity} мест",
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

    context.user_data.pop('new_vessel_name', None)
    return ConversationHandler.END


# ==========================================
# УДАЛЕНИЕ СУДНА
# ==========================================

def get_vessels_for_deletion_keyboard():
    """
    Создаёт inline-клавиатуру со списком всех судов для удаления.
    Каждая кнопка при нажатии отправляет callback_data вида "delete_vessel_{vessel_id}_{vessel_name}"
    """
    session = Session()
    vessels = session.query(Vessel).all()
    session.close()

    if not vessels:
        return None

    keyboard = []
    for vessel in vessels:
        # Проверяем, есть ли связанные маршруты
        session = Session()
        routes_count = session.query(Route).filter_by(vessel_id=vessel.vessel_id).count()
        session.close()

        # Добавляем предупреждение, если есть связанные маршруты
        warning = " ⚠️" if routes_count > 0 else ""

        button = InlineKeyboardButton(
            text=f"❌ {vessel.name} ({vessel.capacity} мест){warning}",
            callback_data=f"delete_vessel_{vessel.vessel_id}_{vessel.name}"
        )
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)


async def delete_vessel_start(update: Update, context):
    """
    Команда /delete_vessel — начало удаления судна (только админ).
    Показывает список всех судов для выбора.
    """
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n"
            "Только администратор может удалять суда."
        )
        return ConversationHandler.END

    # Проверяем, есть ли суда
    session = Session()
    vessels_count = session.query(Vessel).count()
    session.close()

    if vessels_count == 0:
        await update.message.reply_text(
            "❌ Нет доступных судов для удаления!\n\n"
            "Сначала добавьте судно кнопкой «➕ Добавить судно»",
            reply_markup=admin_keyboard()
        )
        return ConversationHandler.END

    # Создаём клавиатуру с судами для удаления
    keyboard = get_vessels_for_deletion_keyboard()

    await update.message.reply_text(
        "🗑 *Удаление судна* 🗑\n\n"
        "⚠️ *ВНИМАНИЕ!* При удалении судна:\n"
        "• Будут удалены ВСЕ связанные маршруты\n"
        "• Будут удалены ВСЕ рейсы этих маршрутов\n"
        "• Будут удалены ВСЕ билеты на эти рейсы\n\n"
        "Это действие НЕОБРАТИМО!\n\n"
        "📋 *Выберите судно* для удаления из списка ниже:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return ASK_DELETE_VESSEL_NAME


async def process_delete_vessel(update: Update, context):
    """
    Обрабатывает нажатие на кнопку с выбором судна для удаления.
    Удаляет судно и все связанные данные.
    """
    query = update.callback_query
    await query.answer()

    # Разбираем callback_data
    # Формат: delete_vessel_{vessel_id}_{vessel_name}
    data_parts = query.data.split('_')
    vessel_id = int(data_parts[2])
    # Название может содержать подчёркивания, поэтому собираем всё после ID
    vessel_name = '_'.join(data_parts[3:])

    session = Session()

    # Получаем судно
    vessel = session.query(Vessel).filter_by(vessel_id=vessel_id).first()
    if not vessel:
        await query.edit_message_text(
            f"❌ Судно «{vessel_name}» не найдено!",
            reply_markup=admin_keyboard()
        )
        session.close()
        return ConversationHandler.END

    # Собираем статистику перед удалением
    routes = session.query(Route).filter_by(vessel_id=vessel_id).all()
    routes_count = len(routes)
    schedules_count = 0
    tickets_count = 0

    for route in routes:
        schedules = session.query(Schedule).filter_by(route_id=route.route_id).all()
        schedules_count += len(schedules)
        for schedule in schedules:
            tickets = session.query(Ticket).filter_by(schedule_id=schedule.schedule_id).count()
            tickets_count += tickets

    # Удаляем в правильном порядке (сначала зависимые данные)
    # 1. Удаляем билеты
    for route in routes:
        schedules = session.query(Schedule).filter_by(route_id=route.route_id).all()
        for schedule in schedules:
            session.query(Ticket).filter_by(schedule_id=schedule.schedule_id).delete()

    # 2. Удаляем расписание
    for route in routes:
        session.query(Schedule).filter_by(route_id=route.route_id).delete()

    # 3. Удаляем маршруты
    session.query(Route).filter_by(vessel_id=vessel_id).delete()

    # 4. Удаляем само судно
    session.delete(vessel)
    session.commit()

    # Получаем оставшиеся суда для обновления статистики
    remaining_vessels = session.query(Vessel).count()
    session.close()

    # Формируем сообщение об успешном удалении
    result_text = (
        f"✅ *Судно успешно удалено!* ✅\n\n"
        f"🗑 Удалено:\n"
        f"   • Судно: {vessel_name}\n"
        f"   • Маршрутов: {routes_count}\n"
        f"   • Рейсов: {schedules_count}\n"
        f"   • Билетов: {tickets_count}\n\n"
        f"📊 Осталось судов: {remaining_vessels}"
    )

    await query.edit_message_text(
        result_text,
        parse_mode='Markdown',
        reply_markup=admin_keyboard()
    )

    return ConversationHandler.END


async def cancel_delete_vessel(update: Update, context):
    """Отмена удаления судна"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Удаление судна отменено.",
        reply_markup=admin_keyboard()
    )
    return ConversationHandler.END