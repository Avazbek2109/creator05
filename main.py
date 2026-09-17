import logging
import os
from datetime import time
import pytz

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Foydalanuvchilar ma'lumotlarini saqlash uchun lug'at (Memory Database)
user_data_store = {}


def get_user_data(user_id: int):
    if user_id not in user_data_store:
        user_data_store[user_id] = {"income": 0, "expense": 0, "history": []}
    return user_data_store[user_id]


# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Har kuni soat 20:00 da eslatma yuborish uchun job rejalashtirish
    # O'zbekiston vaqti bilan (Asia/Tashkent)
    tz = pytz.timezone("Asia/Tashkent")
    reminder_time = time(hour=20, minute=0, second=0, tzinfo=tz)

    # Takrorlanib qolmasligi uchun eski joblarni o'chirish
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()

    # Yangi har kunlik eslatma qo'shish
    context.job_queue.run_daily(
        send_daily_reminder, time=reminder_time, chat_id=chat_id, name=str(chat_id)
    )

    msg = (
        "Assalomu alaykum! Kunlik hisob-kitob botiga xush kelibsiz.\n\n"
        "**Buyruqlar:**\n"
        "➕ Xarajat yoki daromad kiritish uchun son kiriting:\n"
        "   • +50000 (Daromad)\n"
        "   • -20000 (Xarajat)\n\n"
        "📊 /stat - Bugungi hisobot\n"
        "🔄 /reset - Hisobni nolga tushirish\n\n"
        "⏰ *Har kuni soat 20:00 da bot sizga hisobotni to'ldirishni eslatib turadi.*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# Har kunlik eslatma funksiyasi
async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    msg = (
        "🔔 **Kunlik eslatma!**\n\n"
        "Bugungi xarajat va daromadlaringizni kiritdingizmi?\n"
        "Kiritish uchun masalan: `-15000` yoki `+80000` ko'rinishida yuboring."
    )
    await context.bot.send_message(
        chat_id=job.chat_id, text=msg, parse_mode="Markdown"
    )


# Daromad va xarajatlarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    data = get_user_data(user_id)

    try:
        amount = float(text)
        if amount > 0:
            data["income"] += amount
            data["history"].append(f"🟢 Daromad: +{amount:,.0f} so'm")
            await update.message.reply_text(
                f"✅ Daromad qo'shildi: +{amount:,.0f} so'm"
            )
        elif amount < 0:
            abs_amount = abs(amount)
            data["expense"] += abs_amount
            data["history"].append(f"🔴 Xarajat: -{abs_amount:,.0f} so'm")
            await update.message.reply_text(
                f"✅ Xarajat qo'shildi: -{abs_amount:,.0f} so'm"
            )
        else:
            await update.message.reply_text("Nol qiymat kiritib bo'lmaydi.")
    except ValueError:
        await update.message.reply_text(
            "Iltimos, faqat raqam kiriting.\nMasalan: `+50000` yoki `-25000`",
            parse_mode="Markdown",
        )


# Stat - Hisobotni ko'rish
async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)

    income = data["income"]
    expense = data["expense"]
    balance = income - expense

    history_text = (
        "\n".join(data["history"][-5:]) if data["history"] else "Hali amallar yo'q."
    )

    msg = (
        f"📊 **Kunlik Hisobot:**\n\n"
        f"🟢 Jami daromad: {income:,.0f} so'm\n"
        f"🔴 Jami xarajat: {expense:,.0f} so'm\n"
        f"⚖️ Balans: {balance:,.0f} so'm\n\n"
        f"📜 **Oxirgi amallar:**\n{history_text}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# Reset - Hisobni tozalash
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_store[user_id] = {"income": 0, "expense": 0, "history": []}
    await update.message.reply_text("🔄 Hisob-kitoblaringiz nolga tushirildi.")


def main():
    # Telegram Bot Token (Environment Variable orqali olinadi)
    BOT_TOKEN = os.getenv("8939767443:AAGpkPJIJ5JN5VVd16ItK1I_4EClTnv2sr4")

    if not BOT_TOKEN:
        print("XATOLIK: BOT_TOKEN muhit o'zgaruvchisi topilmadi!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Botni ishga tushirish
    app.run_polling()


if __name__ == "__main__":
    main()
  
