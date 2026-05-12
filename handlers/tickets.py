"""Покупка билетов: выбор маршрута, рейса, создание билета"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler
from database import Session, Route, Schedule, Ticket
from handlers.common import main_keyboard

# Состояния
ASK_ROUTE, ASK_SCHEDULE = 1, 2

async def buy_ticket(update: Update, context):
    """Начинает процесс покупки билета"""
    session = Session()
    routes = session.query(Route).all()
    session.close()

    if not routes:
        await update.message.reply_text(
            "❌ Извините, сейчас нет доступных маршрутов. ❌\n\n"
            "Команда для администратора: /add_test_data"
        )
        return ConversationHandler.END

    context.user_data['routes'] = routes

    text = "📋 *Доступные маршруты:* 📋\n\n"
    for i, r in enumerate(routes, 1):
        text += f"{i}. 🚢 {r.origin} → {r.destination}\n"
        text += f"   ⏱ {r.duration} минут | 💰 {r.base_price} руб.\n\n"
    text += "✏️ *Введите номер маршрута* (например, 1):"

    await update.message.reply_text(text, parse_mode='Markdown')
    return ASK_ROUTE

async def process_route(update: Update, context):
    """Обрабатывает выбор маршрута"""
    try:
        choice = int(update.message.text) - 1
        routes = context.user_data.get('routes', [])

        if choice < 0 or choice >= len(routes):
            raise ValueError

        route = routes[choice]
        context.user_data['selected_route_id'] = route.route_id

        session = Session()
        schedules = session.query(Schedule).filter(
            Schedule.route_id == route.route_id,
            Schedule.departure_time >= datetime.now(),
            Schedule.available_seats > 0
        ).limit(10).all()
        session.close()

        if not schedules:
            await update.message.reply_text(
                "❌ На выбранный маршрут нет свободных мест на ближайшие дни. ❌"
            )
            return ConversationHandler.END

        context.user_data['schedules'] = schedules

        keyboard = []
        for s in schedules:
            time_str = s.departure_time.strftime("%d.%m %H:%M")
            btn = InlineKeyboardButton(
                text=f"🕐 {time_str} | 🪑 {s.available_seats} мест",
                callback_data=f"schedule_{s.schedule_id}"
            )
            keyboard.append([btn])

        await update.message.reply_text(
            f"✅ Выбран маршрут: {route.origin} → {route.destination} ✅\n\n"
            f"💰 Цена билета: {route.base_price} руб.\n\n"
            f"🕐 *Выберите время отправления:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_SCHEDULE

    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите номер маршрута цифрой. ❌")
        return ASK_ROUTE

async def process_schedule(update: Update, context):
    """Обрабатывает выбор времени и покупает билет"""
    query = update.callback_query
    await query.answer()

    schedule_id = int(query.data.split('_')[1])
    user_id = query.from_user.id

    session = Session()

    try:
        schedule = session.query(Schedule).filter_by(schedule_id=schedule_id).first()
        if not schedule:
            await query.edit_message_text("❌ Рейс не найден")
            return ConversationHandler.END

        route = session.query(Route).filter_by(route_id=schedule.route_id).first()
        if not route:
            await query.edit_message_text("❌ Маршрут не найден")
            return ConversationHandler.END

        if schedule.available_seats <= 0:
            await query.edit_message_text("❌ Мест нет")
            return ConversationHandler.END

        # Сохраняем данные ДО закрытия сессии
        route_origin = route.origin
        route_destination = route.destination
        route_price = route.base_price
        departure_time_str = schedule.departure_time.strftime('%d.%m.%Y %H:%M')
        seat_number = schedule.available_seats

        # Создаём билет
        ticket = Ticket(
            user_id=user_id,
            schedule_id=schedule_id,
            seat_number=seat_number,
            status='paid',
            price=route_price
        )

        schedule.available_seats -= 1
        session.add(ticket)
        session.commit()
        session.close()

        await query.edit_message_text(
            f"✅ *БИЛЕТ УСПЕШНО КУПЛЕН!* ✅\n\n"
            f"🚢 *Маршрут:* {route_origin} → {route_destination}\n"
            f"🕐 *Дата и время:* {departure_time_str}\n"
            f"💺 *Место:* {seat_number}\n"
            f"💰 *Цена:* {route_price} руб.\n\n"
            f"🎫 Спасибо за покупку!",
            parse_mode='Markdown'
        )

        return ConversationHandler.END

    except Exception as e:
        print(f"Ошибка в process_schedule: {e}")
        session.rollback()
        await query.edit_message_text(f"❌ Ошибка при покупке: {str(e)[:100]}")
        return ConversationHandler.END
    finally:
        session.close()

async def my_tickets(update: Update, context):
    """Показывает все билеты пользователя"""
    user_id = update.effective_user.id
    session = Session()

    tickets = session.query(Ticket, Schedule, Route).join(
        Schedule, Ticket.schedule_id == Schedule.schedule_id
    ).join(
        Route, Schedule.route_id == Route.route_id
    ).filter(
        Ticket.user_id == user_id
    ).all()

    session.close()

    if not tickets:
        await update.message.reply_text(
            "📭 У вас пока нет билетов. 📭\n\n"
            "Чтобы купить билет, нажмите кнопку «🚢 Купить билет»."
        )
        return

    text = "🎫 *ВАШИ БИЛЕТЫ:* 🎫\n\n"
    for ticket, schedule, route in tickets:
        status_text = "✅ ОПЛАЧЕН" if ticket.status == 'paid' else "⏳ ОЖИДАЕТ ОПЛАТЫ"
        text += f"┌─────────────────────────┐\n"
        text += f"│ 🚢 {route.origin} → {route.destination}\n"
        text += f"│ 🕐 {schedule.departure_time.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"│ 💺 Место: {ticket.seat_number}\n"
        text += f"│ 💰 Цена: {ticket.price} руб.\n"
        text += f"│ 📌 Статус: {status_text}\n"
        text += f"└─────────────────────────┘\n\n"

    await update.message.reply_text(text, parse_mode='Markdown')