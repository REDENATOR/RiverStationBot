# ==========================================
# TELEGRAM БОТ ДЛЯ ПРОДАЖИ БИЛЕТОВ НА РЕЧНОМ ВОКЗАЛЕ
# Версия для python-telegram-bot 20.x
# ==========================================

import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from database import Session, User, Route, Schedule, Ticket, init_db, add_test_data
from config import TOKEN, ADMIN_ID

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Состояния для разговора
ASK_PHONE, ASK_ROUTE, ASK_SCHEDULE = range(3)


# ==========================================
# КЛАВИАТУРЫ
# ==========================================

def main_keyboard():
    buttons = [["🚢 Купить билет"], ["📋 Мои билеты"]]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def phone_keyboard():
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    return ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)


# ==========================================
# ОБРАБОТЧИКИ
# ==========================================

async def start(update: Update, context):
    """Обработчик команды /start"""
    user = update.effective_user
    session = Session()

    existing = session.query(User).filter_by(user_id=user.id).first()

    if not existing:
        new_user = User(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name
        )
        session.add(new_user)
        session.commit()
        session.close()

        await update.message.reply_text(
            "👋 Добро пожаловать! 👋\n\n"
            "Я бот Речного вокзала. Я помогу вам купить билет на теплоход.\n\n"
            "📱 Пожалуйста, отправьте ваш номер телефона, нажав на кнопку ниже:",
            reply_markup=phone_keyboard()
        )
        return ASK_PHONE

    session.close()
    await update.message.reply_text(
        f"🎉 С возвращением, {user.full_name}! 🎉\n\n"
        "Вы можете купить билет на теплоход или посмотреть свои билеты.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


async def receive_phone(update: Update, context):
    """Принимает номер телефона"""
    phone = update.message.contact.phone_number
    user_id = update.effective_user.id

    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.phone = phone
        session.commit()
    session.close()

    await update.message.reply_text(
        "✅ Спасибо! Регистрация успешно завершена. ✅\n\n"
        "Теперь вы можете покупать билеты.\n"
        "Нажмите кнопку «🚢 Купить билет», чтобы начать.",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


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
    """Обрабатывает выбор времени рейса"""
    query = update.callback_query
    await query.answer()

    schedule_id = int(query.data.split('_')[1])
    user_id = query.from_user.id

    session = Session()
    schedule = session.query(Schedule).filter_by(schedule_id=schedule_id).first()

    if not schedule:
        await query.edit_message_text("❌ Рейс не найден. ❌")
        session.close()
        return ConversationHandler.END

    route = session.query(Route).filter_by(route_id=schedule.route_id).first()

    if schedule.available_seats <= 0:
        await query.edit_message_text(
            "❌ К сожалению, на этот рейс все места уже проданы. ❌"
        )
        session.close()
        return ConversationHandler.END

    ticket = Ticket(
        user_id=user_id,
        schedule_id=schedule_id,
        seat_number=schedule.available_seats,
        status='paid',
        price=route.base_price
    )

    schedule.available_seats -= 1
    session.add(ticket)
    session.commit()
    session.close()

    message_text = (
        f"✅ *БИЛЕТ УСПЕШНО КУПЛЕН!* ✅\n\n"
        f"🚢 *Маршрут:* {route.origin} → {route.destination}\n"
        f"🕐 *Дата и время:* {schedule.departure_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"💺 *Место:* {ticket.seat_number}\n"
        f"💰 *Цена:* {ticket.price} руб.\n\n"
        f"🎫 Спасибо за покупку! Счастливого пути!"
    )

    await query.edit_message_text(message_text, parse_mode='Markdown')
    return ConversationHandler.END


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


async def cancel(update: Update, context):
    """Отмена действия"""
    await update.message.reply_text(
        "❌ Действие отменено. ❌",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END


# ==========================================
# ЗАПУСК БОТА
# ==========================================

def main():
    print("\n" + "=" * 60)
    print("🚢 РЕЧНОЙ ВОКЗАЛ - TELEGRAM БОТ ДЛЯ ПРОДАЖИ БИЛЕТОВ 🚢")
    print("=" * 60 + "\n")

    init_db()

    # СОЗДАЁМ ПРИЛОЖЕНИЕ (НОВЫЙ СПОСОБ ДЛЯ ВЕРСИИ 20.x)
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_PHONE: [MessageHandler(filters.CONTACT, receive_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    buy_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🚢 Купить билет$'), buy_ticket)],
        states={
            ASK_ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_route)],
            ASK_SCHEDULE: [CallbackQueryHandler(process_schedule, pattern='^schedule_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(buy_handler)

    application.add_handler(CommandHandler('add_test_data', add_test_data_command))
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои билеты$'), my_tickets))

    print("🤖 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ! 🤖")
    print("\n📌 ИНСТРУКЦИЯ:")
    print("   1. Найдите своего бота в Telegram")
    print("   2. Нажмите /start для регистрации")
    print("   3. Напишите /add_test_data для добавления тестовых рейсов")
    print("   4. Нажмите «🚢 Купить билет» для покупки")
    print("\n⏹ Для остановки бота нажмите Ctrl+C\n")

    # ЗАПУСК (НОВЫЙ СПОСОБ)
    application.run_polling()


if __name__ == '__main__':
    main()