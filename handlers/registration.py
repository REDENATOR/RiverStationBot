"""Регистрация пользователей: /start и приём номера телефона"""
from telegram import Update
from telegram.ext import ConversationHandler
from database import Session, User
from handlers.common import phone_keyboard, main_keyboard, admin_keyboard
from config import ADMIN_ID

# Состояние для ожидания номера телефона
ASK_PHONE = 0


async def start(update: Update, context):
    """
    Обработчик команды /start.
    Регистрирует нового пользователя или приветствует существующего.
    Для администратора показывает админ-панель.
    """
    user = update.effective_user
    session = Session()

    # Проверяем, есть ли пользователь в базе данных
    existing = session.query(User).filter_by(user_id=user.id).first()

    if not existing:
        # === НОВЫЙ ПОЛЬЗОВАТЕЛЬ ===
        new_user = User(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name
        )
        session.add(new_user)
        session.commit()
        session.close()

        # Отправляем приветствие и просим номер телефона
        await update.message.reply_text(
            "👋 Добро пожаловать! 👋\n\n"
            "Я бот Речного вокзала. Я помогу вам купить билет на теплоход.\n\n"
            "📱 Пожалуйста, отправьте ваш номер телефона, нажав на кнопку ниже:",
            reply_markup=phone_keyboard()
        )
        return ASK_PHONE

    session.close()

    # === СУЩЕСТВУЮЩИЙ ПОЛЬЗОВАТЕЛЬ ===
    # Проверяем, является ли пользователь администратором
    if user.id == ADMIN_ID:
        reply_markup = admin_keyboard()
        welcome_text = (
            f"👑 *С возвращением, Администратор {user.full_name}!* 👑\n\n"
            "Вам доступна административная панель.\n\n"
            "📋 *Доступные действия:*\n"
            "• 🚢 Купить билет — покупка билета как обычный пользователь\n"
            "• 📋 Мои билеты — просмотр своих билетов\n"
            "• ➕ Добавить судно — добавление нового судна\n"
            "• 🛣 Добавить маршрут — создание нового маршрута\n"
            "• 📅 Добавить рейс — добавление нового рейса в расписание\n"
            "• 📊 Статистика — просмотр статистики работы бота\n"
            "• 🗑 Очистить данные — удаление всех данных из базы\n"
            "• ❌ Выйти из админ-меню — переключиться в обычный режим\n\n"
            "Выберите действие на кнопках ниже:"
        )
    else:
        reply_markup = main_keyboard()
        welcome_text = (
            f"🎉 *С возвращением, {user.full_name}!* 🎉\n\n"
            "Вы можете купить билет на теплоход или посмотреть свои билеты.\n\n"
            "📋 *Доступные действия:*\n"
            "• 🚢 Купить билет — выбрать маршрут и время\n"
            "• 📋 Мои билеты — просмотреть купленные билеты"
        )

    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END


async def receive_phone(update: Update, context):
    """
    Принимает номер телефона от пользователя и сохраняет в базу данных.
    Вызывается после того, как пользователь нажал кнопку "Отправить номер телефона".
    """
    # Получаем номер телефона из сообщения
    phone = update.message.contact.phone_number
    user_id = update.effective_user.id

    # Открываем сессию базы данных
    session = Session()

    # Находим пользователя по Telegram ID
    user = session.query(User).filter_by(user_id=user_id).first()

    if user:
        # Обновляем номер телефона
        user.phone = phone
        session.commit()

    session.close()

    # Проверяем, является ли пользователь администратором
    if user_id == ADMIN_ID:
        reply_markup = admin_keyboard()
        success_text = (
            "✅ *Регистрация администратора успешно завершена!* ✅\n\n"
            "Теперь вам доступна административная панель.\n"
            "Используйте кнопки меню для управления ботом."
        )
    else:
        reply_markup = main_keyboard()
        success_text = (
            "✅ *Регистрация успешно завершена!* ✅\n\n"
            "Теперь вы можете покупать билеты.\n"
            "Нажмите кнопку «🚢 Купить билет», чтобы начать."
        )

    await update.message.reply_text(
        success_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return ConversationHandler.END