"""Главный файл запуска бота"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from database import init_db
from config import TOKEN

from handlers.common import cancel, main_keyboard
from handlers.registration import start, receive_phone, ASK_PHONE
from handlers.tickets import buy_ticket, process_route, process_schedule, my_tickets, ASK_ROUTE, ASK_SCHEDULE
from handlers.admin import add_test_data_command
from handlers.vessels import add_vessel_start, get_vessel_name, get_vessel_capacity, ASK_VESSEL_NAME, ASK_VESSEL_CAPACITY
from handlers.route import (
    add_route_start,
    process_vessel_selection,
    get_route_origin,
    get_route_destination,
    get_route_duration,
    get_route_price,
    ASK_ROUTE_VESSEL,
    ASK_ROUTE_ORIGIN,
    ASK_ROUTE_DESTINATION,
    ASK_ROUTE_DURATION,
    ASK_ROUTE_PRICE
)
from handlers.schedule import (
    add_schedule_start,
    process_route_selection,
    get_schedule_datetime,
    get_schedule_seats,
    ASK_SCHEDULE_ROUTE,
    ASK_SCHEDULE_DATETIME,
    ASK_SCHEDULE_SEATS
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    print("\n" + "=" * 60)
    print("🚢 РЕЧНОЙ ВОКЗАЛ - TELEGRAM БОТ ДЛЯ ПРОДАЖИ БИЛЕТОВ 🚢")
    print("=" * 60 + "\n")

    init_db()

    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # === 1. РЕГИСТРАЦИЯ ===
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={ASK_PHONE: [MessageHandler(filters.CONTACT, receive_phone)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(reg_handler)

    # === 2. ПОКУПКА БИЛЕТА ===
    buy_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🚢 Купить билет$'), buy_ticket)],
        states={
            ASK_ROUTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_route)],
            ASK_SCHEDULE: [CallbackQueryHandler(process_schedule, pattern='^schedule_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(buy_handler)

    # === 3. ДОБАВЛЕНИЕ СУДНА (АДМИН) ===
    vessel_handler = ConversationHandler(
        entry_points=[CommandHandler('add_vessel', add_vessel_start)],
        states={
            ASK_VESSEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vessel_name)],
            ASK_VESSEL_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vessel_capacity)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(vessel_handler)

    # === 4. ДОБАВЛЕНИЕ МАРШРУТА (АДМИН) ===
    route_handler = ConversationHandler(
        entry_points=[CommandHandler('add_route', add_route_start)],
        states={
            ASK_ROUTE_VESSEL: [CallbackQueryHandler(process_vessel_selection, pattern='^vessel_')],
            ASK_ROUTE_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_route_origin)],
            ASK_ROUTE_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_route_destination)],
            ASK_ROUTE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_route_duration)],
            ASK_ROUTE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_route_price)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(route_handler)

    # === 5. ДОБАВЛЕНИЕ РАСПИСАНИЯ (АДМИН) ===
    schedule_handler = ConversationHandler(
        entry_points=[CommandHandler('add_schedule', add_schedule_start)],
        states={
            ASK_SCHEDULE_ROUTE: [CallbackQueryHandler(process_route_selection, pattern='^route_')],
            ASK_SCHEDULE_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_schedule_datetime)],
            ASK_SCHEDULE_SEATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_schedule_seats)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(schedule_handler)

    # === 6. ПРОСТЫЕ КОМАНДЫ ===
    application.add_handler(CommandHandler('add_test_data', add_test_data_command))
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои билеты$'), my_tickets))

    print("🤖 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ! 🤖")
    print("\n📌 ДОСТУПНЫЕ КОМАНДЫ:")
    print("   /start - начать работу")
    print("   /add_test_data - добавить тестовые рейсы (админ)")
    print("   /add_vessel - добавить новое судно (админ)")
    print("   /add_route - добавить маршрут(админ)")
    print("   /cancel - отменить действие")
    print("\n⏹ Для остановки бота нажмите Ctrl+C\n")

    application.run_polling()


if __name__ == '__main__':
    main()