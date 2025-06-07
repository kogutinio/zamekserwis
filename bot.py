import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from dotenv import load_dotenv
from database import Database

load_dotenv()

# Настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_ID = os.getenv('GROUP_ID')
DISPATCHER_IDS = [int(x) for x in os.getenv('DISPATCHER_IDS').split(',')]

# Состояния
ADDRESS, CONTACTS, TIME = range(3)

# Инициализация логгера
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

# Клавиатуры
def main_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("➕ Создать заказ", callback_data="create_order")
    ]])

def accept_keyboard(order_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Принять заказ", callback_data=f"accept_{order_id}")
    ]])

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔧 ZamekSerwis - Управление заказами",
        reply_markup=main_keyboard()
    )

async def create_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    if user_id not in DISPATCHER_IDS:
        await update.callback_query.answer("Только для диспетчеров!", show_alert=True)
        return ConversationHandler.END
        
    await update.callback_query.message.reply_text("📍 Введите адрес:")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("📞 Введите телефон клиента:")
    return CONTACTS

async def get_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contacts'] = update.message.text
    await update.message.reply_text("⏰ Введите время (например: 01.01.2025 14:30):")
    return TIME

async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = context.user_data['address']
    contacts = context.user_data['contacts']
    time = update.message.text
    
    # Сохраняем заказ в базу данных
    order_id = await db.add_order(address, contacts, time)
    
    # Отправляем в группу
    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=f"🚨 НОВЫЙ ЗАКАЗ #{order_id}\n\n"
             f"📍 Адрес: {address}\n"
             f"📞 Телефон: {contacts}\n"
             f"⏰ Время: {time}",
        reply_markup=accept_keyboard(order_id)
    )
    
    await update.message.reply_text(f"✅ Заказ #{order_id} создан!")
    return ConversationHandler.END

async def accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = int(query.data.split('_')[1])
    worker_id = query.from_user.id
    worker_name = query.from_user.full_name
    
    # Обновляем заказ в базе данных
    await db.assign_order(order_id, worker_id, worker_name)
    
    # Обновляем сообщение
    await query.edit_message_text(
        text=f"{query.message.text}\n\n"
             f"✅ Принял: {worker_name}",
        reply_markup=None
    )
    
    await query.answer(f"Вы приняли заказ #{order_id}!")

async def init_db():
    await db.connect()

def main():
    # Инициализация приложения
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Инициализация БД
    app.run_polling(init_db(), close_loop=False)
    
    # Обработчики
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_order, pattern="create_order")],
        states={
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contacts)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)]
        },
        fallbacks=[]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(accept_order, pattern=r"accept_\d+"))
    
    app.run_polling()

if __name__ == "__main__":
    main()
