"""Главный файл запуска бота"""
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from database import init_db
from config import TOKEN

# Общие функции
from handlers.common import cancel, show_admin_menu, exit_admin_menu, cancel_with_button

# Регистрация
from handlers.registration import start, receive_phone, ASK_PHONE

# Билеты
from handlers.tickets import (
    buy_ticket, process_route, process_schedule, my_tickets,
    ASK_ROUTE, ASK_SCHEDULE
)

# Админские команды
from handlers.admin import (
    add_test_data_command, show_statistics, clear_all_data, confirm_clear_data
)

# Управление судами
from handlers.vessels import (
    add_vessel_start,
    get_vessel_name,
    get_vessel_capacity,
    delete_vessel_start,           # ← ДОБАВИТЬ
    process_delete_vessel,         # ← ДОБАВИТЬ
    cancel_delete_vessel,          # ← ДОБАВИТЬ
    ASK_VESSEL_NAME,
    ASK_VESSEL_CAPACITY,
    ASK_DELETE_VESSEL_NAME         # ← ДОБАВИТЬ
)

# Управление маршрутами
from handlers.route import (
    add_route_start, process_vessel_selection,
    get_route_origin, get_route_destination, get_route_duration, get_route_price,
    ASK_ROUTE_VESSEL, ASK_ROUTE_ORIGIN, ASK_ROUTE_DESTINATION, ASK_ROUTE_DURATION, ASK_ROUTE_PRICE
)

# Управление расписанием
from handlers.schedule import (
    add_schedule_start, process_route_selection,
    get_schedule_datetime, get_schedule_seats,
    ASK_SCHEDULE_ROUTE, ASK_SCHEDULE_DATETIME, ASK_SCHEDULE_SEATS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    print("\n" + "=" * 60)
    print("🚢 РЕЧНОЙ ВОКЗАЛ - TELEGRAM БОТ ДЛЯ ПРОДАЖИ БИЛЕТОВ 🚢")
    print("=" * 60 + "\n")

    init_db()

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

    # === 3. ДОБАВЛЕНИЕ СУДНА ===
    vessel_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Добавить судно$'), add_vessel_start)],
        states={
            ASK_VESSEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vessel_name)],
            ASK_VESSEL_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vessel_capacity)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(vessel_handler)
    # === 4. УДАЛЕНИЕ СУДНА (АДМИН) ===
    delete_vessel_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🗑 Удалить судно$'), delete_vessel_start)],
        states={
            ASK_DELETE_VESSEL_NAME: [CallbackQueryHandler(process_delete_vessel, pattern='^delete_vessel_')],
        },
        fallbacks=[CommandHandler('cancel', cancel_delete_vessel)]
    )
    application.add_handler(delete_vessel_handler)
    # === 5. ДОБАВЛЕНИЕ МАРШРУТА ===
    route_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🛣 Добавить маршрут$'), add_route_start)],
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

    # === 6. ДОБАВЛЕНИЕ РАСПИСАНИЯ ===
    schedule_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📅 Добавить рейс$'), add_schedule_start)],
        states={
            ASK_SCHEDULE_ROUTE: [CallbackQueryHandler(process_route_selection, pattern='^route_')],
            ASK_SCHEDULE_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_schedule_datetime)],
            ASK_SCHEDULE_SEATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_schedule_seats)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(schedule_handler)

    # === 7. АДМИН-КОМАНДЫ ===
    application.add_handler(CommandHandler('add_test_data', add_test_data_command))
    application.add_handler(MessageHandler(filters.Regex('^📊 Статистика$'), show_statistics))
    application.add_handler(MessageHandler(filters.Regex('^🗑 Очистить данные$'), clear_all_data))
    application.add_handler(CommandHandler('confirm_clear', confirm_clear_data))
    application.add_handler(MessageHandler(filters.Regex('^❌ Выйти из админ-меню$'), exit_admin_menu))
    application.add_handler(MessageHandler(filters.Regex('^👑 Админ-панель$'), show_admin_menu))
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои билеты$'), my_tickets))

    # === 8. ОБРАБОТЧИК КНОПКИ ОТМЕНЫ ===
    application.add_handler(MessageHandler(filters.Regex('^❌ Отмена$'), cancel_with_button))
    application.add_handler(MessageHandler(filters.Regex('^🏠 В главное меню$'), exit_admin_menu))

    print("🤖 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ! 🤖")
    print("\n📌 ДОСТУПНЫЕ КОМАНДЫ:")
    print("   /start - начать работу")
    print("   /add_test_data - добавить тестовые данные (админ)")
    print("\n⏹ Для остановки бота нажмите Ctrl+C\n")

    application.run_polling()



if __name__ == '__main__':
    main()