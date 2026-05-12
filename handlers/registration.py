"""Регистрация пользователей: /start и приём номера телефона"""
from telegram import Update
from telegram.ext import ConversationHandler
from database import Session, User
from handlers.common import phone_keyboard, main_keyboard

# Состояния
ASK_PHONE = 0

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