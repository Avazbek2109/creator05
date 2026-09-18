import logging
import os
from datetime import datetime, time
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Logging sozlamasi
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Tokenni muhit o'zgaruvchisidan olish (Render/GitHub Secrets uchun)
TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_TELEGRAM_BOT_TOKENINGIZNI_YOZING")

# Vaqt zonasi (O'zbekiston vaqti)
TIMEZONE = pytz.timezone("Asia/Tashkent")

# Foydalanuvchilar ma'lumotlarini saqlash (oddiy lug'at)
# Katta loyihalar uchun ma'lumotlar bazasi (DB) ishlatish tavsiya etiladi.
user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'i berilganda ishlaydi."""
    chat_id = update.effective_chat.id
    today = datetime.now(TIMEZONE).date()

    if chat_id not in user_data:
        user_data[chat_id] = today
        text = (
            f"Xush kelibsiz! Siz ro'yxatdan o'tdingiz.\n"
            f"Bugun sizning 1-kuningiz ({today.strftime('%d.%m.%Y')}).\n\n"
            f"Har kuni 09:00 da sizga kunlik hisobot yuborib turaman."
        )
    else:
        joined_date = user_data[chat_id]
        days_count = (today - joined_date).days + 1
        text = f"Siz allaqachon ro'yxatdan o'tgansiz!\nBugun sizning {days_count}-kuningiz."

    # Har kuni avtomatik xabar yuborish vazifasini sozlash
    schedule_daily_notification(context, chat_id)

    await update.message.reply_text(text)


async def send_daily_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Har kuni yuboriladigan xabar funksiyasi."""
    job = context.job
    chat_id = job.chat_id

    if chat_id in user_data:
        joined_date = user_data[chat_id]
        today = datetime.now(TIMEZONE).date()
        days_count = (today - joined_date).days + 1

        message = (
            f"Xayrli kun! ☀️\n\n"
            f"Bugun siz guruhga/loyihaga kelganingizga **{days_count}-kun** bo'ldi!\n"
            f"Kuningiz unumli o'tsin!"
        )
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")


def schedule_daily_notification(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Vazifani har kunlik vaqtga rejalashtirish."""
    job_name = str(chat_id)

    # Eski job bo'lsa o'chirish
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    # Har kuni 09:00 da xabar yuborish (vaqtni o'zgartirishingiz mumkin)
    notification_time = time(hour=9, minute=0, second=0, tzinfo=TIMEZONE)

    context.job_queue.run_daily(
        send_daily_message,
        time=notification_time,
        chat_id=chat_id,
        name=job_name
    )


def main() -> None:
    """Botni ishga tushirish."""
    application = Application.builder().token(TOKEN).build()

    # Buyruqlarni ro'yxatdan o'tkazish
    application.add_handler(CommandHandler("start", start))

    # Botni ishga tushirish
    application.run_polling()


if __name__ == "__main__":
    main()

