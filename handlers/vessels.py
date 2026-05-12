"""Управление судами: добавление новых судов (только админ)"""
from telegram import Update
from telegram.ext import ConversationHandler
from database import Session, Vessel
from config import ADMIN_ID

# Состояния для добавления судна
ASK_VESSEL_NAME, ASK_VESSEL_CAPACITY = 10, 11

async def add_vessel_start(update: Update, context):
    """Команда /add_vessel — начало добавления нового судна (только админ)"""
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
        "Примеры: «Метеор-200», «Восход», «Ракета-90»\n\n"
        "Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_VESSEL_NAME

async def get_vessel_name(update: Update, context):
    """Получает название судна"""
    vessel_name = update.message.text.strip()

    if len(vessel_name) < 2:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 2 символа).\n"
            "Введите название судна ещё раз:"
        )
        return ASK_VESSEL_NAME

    context.user_data['new_vessel_name'] = vessel_name

    await update.message.reply_text(
        f"✅ Название: *{vessel_name}*\n\n"
        "📊 Введите вместимость судна (количество пассажиров).\n"
        "Примеры: 40, 60, 100, 150\n\n"
        "Для отмены напишите /cancel",
        parse_mode='Markdown'
    )
    return ASK_VESSEL_CAPACITY

async def get_vessel_capacity(update: Update, context):
    """Получает вместимость и сохраняет судно"""
    try:
        user_input = update.message.text.strip()

        try:
            capacity = int(user_input)
        except ValueError:
            await update.message.reply_text(
                "❌ Введите число (количество мест):\nПример: 40, 60, 100"
            )
            return ASK_VESSEL_CAPACITY

        if capacity < 1 or capacity > 500:
            await update.message.reply_text(
                "❌ Вместимость должна быть от 1 до 500.\nВведите корректное значение:"
            )
            return ASK_VESSEL_CAPACITY

        vessel_name = context.user_data.get('new_vessel_name')
        if not vessel_name:
            await update.message.reply_text(
                "❌ Ошибка: не найдено название.\nНачните заново с /add_vessel"
            )
            return ConversationHandler.END

        session = Session()

        existing = session.query(Vessel).filter_by(name=vessel_name).first()
        if existing:
            await update.message.reply_text(
                f"❌ Судно «{vessel_name}» уже существует!\n"
                f"Вместимость: {existing.capacity} мест"
            )
            session.close()
            return ConversationHandler.END

        new_vessel = Vessel(name=vessel_name, capacity=capacity)
        session.add(new_vessel)
        session.commit()
        session.close()

        await update.message.reply_text(
            f"✅ *Судно успешно добавлено!*\n\n"
            f"🚢 {vessel_name}\n"
            f"👥 {capacity} мест",
            parse_mode='Markdown'
        )

        context.user_data.pop('new_vessel_name', None)
        return ConversationHandler.END

    except Exception as e:
        print(f"\n❌❌❌ ОШИБКА в get_vessel_capacity: {e} ❌❌❌\n")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ Произошла ошибка: {type(e).__name__}\n\n"
            f"Текст ошибки: {str(e)[:200]}\n\n"
            "Пожалуйста, попробуйте снова с /add_vessel"
        )
        return ConversationHandler.END