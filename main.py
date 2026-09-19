import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, time
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Render serveri uxlab qolmasligi uchun HTTP server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot 24/7 ishlamoqda!")

def start_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN", "")
TIMEZONE = pytz.timezone("Asia/Tashkent")

DAILY_EARNING = 270000  # Kunlik ish haqi summasi

# Foydalanuvchilar ma'lumoti
user_data = {}

def get_user_info(chat_id: int):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "days": 0,
            "daily_total": 0,    # Kunlik 270k dan yig'ilgan summa
            "extra_total": 0,    # 100k, 500k va boshqa kiritilgan summalar
            "history_count": 0
        }
    return user_data[chat_id]

# Yangi klaviaturani yaratish
def get_keyboard():
    keyboard = [
        [KeyboardButton("✅ Ha (270,000 so'm)"), KeyboardButton("❌ Yo'q")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("🔄 Tozalash")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = get_user_info(chat_id)

    schedule_daily_notification(context, chat_id)

    total = user["daily_total"] + user["extra_total"]
    text = (
        f"Xush kelibsiz! 👋\n\n"
        f"Har kuni soat 09:00 da ishga kelganingizni so'rab turaman.\n\n"
        f"💡 **Qo'shimcha:** Chatga `100` deb yozsangiz **100,000 so'm**, `500` deb yozsangiz **500,000 so'm** hisobingizga qo'shiladi.\n\n"
        f"📊 **Hozirgi hisobingiz:**\n"
        f"▪️ Kelgan kunlaringiz: **{user['days']} kun**\n"
        f"▪️ Jami jamg'arma: **{total:,} so'm**\n\n"
        f"Pastdagi tugmalardan foydalanishingiz mumkin:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_keyboard())

async def send_daily_ask(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.chat_id
    
    message = (
        "Xayrli tong! ☀️\n\n"
        "**Bugun ishga keldingizmi?**\n\n"
        "Javob berish uchun pastdagi tugmalarni bosing yoki `h` / `y` deb yuboring."
    )
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown", reply_markup=get_keyboard())

def schedule_daily_notification(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    job_name = str(chat_id)
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    # Har kuni soat 09:00 da so'rash
    notification_time = time(hour=9, minute=0, second=0, tzinfo=TIMEZONE)
    context.job_queue.run_daily(
        send_daily_ask,
        time=notification_time,
        chat_id=chat_id,
        name=job_name
    )

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    raw_text = update.message.text.strip()
    text = raw_text.lower()
    user = get_user_info(chat_id)

    # Hozirgi vaqt va sana (Toshkent vaqti bilan)
    now = datetime.now(TIMEZONE)
    current_time_str = now.strftime("%d.%m.%Y %H:%M")

    # HA javobi (Tugma yoki 'h' harfi)
    if text in ["✅ ha (270,000 so'm)", "h", "ha"]:
        user["days"] += 1
        user["daily_total"] += DAILY_EARNING
        user["history_count"] += 1
        total = user["daily_total"] + user["extra_total"]

        msg = (
            f"✅ **Qabul qilindi!**\n\n"
            f"📅 **Sana va vaqt:** `{current_time_str}`\n"
            f"📌 **Holat:** Ishdasiz (+{DAILY_EARNING:,} so'm qo'shildi)\n\n"
            f"📊 Jami kelgan kunlar: **{user['days']} kun**\n"
            f"💰 Jami jamg'arma: **{total:,} so'm**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # YO'Q javobi (Tugma yoki 'y' harfi)
    elif text in ["❌ yo'q", "y", "yo'q", "yoq"]:
        user["history_count"] += 1
        total = user["daily_total"] + user["extra_total"]

        msg = (
            f"❌ **Qabul qilindi.**\n\n"
            f"📅 **Sana va vaqt:** `{current_time_str}`\n"
            f"📌 **Holat:** Kelmadingiz deb belgilandi\n\n"
            f"📊 Jami kelgan kunlar: **{user['days']} kun**\n"
            f"💰 Jami jamg'arma: **{total:,} so'm**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # STATISTIKA tugmasi
    elif text == "📊 statistika":
        total = user["daily_total"] + user["extra_total"]
        msg = (
            f"📊 **Umumiy statistika:**\n\n"
            f"📅 Ishga kelgan kunlar: **{user['days']} kun**\n"
            f"💵 Kunlik ish haqi yig'indisi: **{user['daily_total']:,} so'm**\n"
            f"➕ Qo'shimcha kiritilgan summa: **{user['extra_total']:,} so'm**\n"
            f"----------------------------------------\n"
            f"💰 **Jami umumiy balans:** **{total:,} so'm**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # TOZALASH (RESET) tugmasi
    elif text in ["🔄 tozalash", "/reset"]:
        user["days"] = 0
        user["daily_total"] = 0
        user["extra_total"] = 0
        user["history_count"] = 0
        msg = "🔄 **Barcha kunlar, statistikalar va to'plangan summalaringiz tozalandi! (0 so'm)**"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    else:
        # Sonlarni tekshirish (100 -> 100,000, 500 -> 500,000)
        cleaned_text = raw_text.replace(" ", "").replace(",", "")
        if cleaned_text.isdigit():
            val = int(cleaned_text)
            added_amount = val
            
            if val == 100:
                added_amount = 100000
            elif val == 500:
                added_amount = 500000

            user["extra_total"] += added_amount
            user["history_count"] += 1
            total = user["daily_total"] + user["extra_total"]

            msg = (
                f"💵 **Qo'shimcha summa qo'shildi!**\n\n"
                f"📅 **Sana va vaqt:** `{current_time_str}`\n"
                f"➕ Qo'shildi: **+{added_amount:,} so'm**\n\n"
                f"💰 **Jami umumiy balans:** **{total:,} so'm**"
            )
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())
        else:
            await update.message.reply_text(
                "Iltimos, pastdagi tugmalardan foydalaning, **h** / **y** deb yozing yoki summani son ko'rinishida kiriting (masalan: `100`, `500`).",
                reply_markup=get_keyboard()
            )

async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = get_user_info(chat_id)
    user["days"] = 0
    user["daily_total"] = 0
    user["extra_total"] = 0
    user["history_count"] = 0
    await update.message.reply_text(
        "🔄 **Barcha kunlar va to'plangan summalaringiz tozalandi! (0 so'm)**",
        parse_mode="Markdown",
        reply_markup=get_keyboard()
    )

def main() -> None:
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    threading.Thread(target=start_health_check_server, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))

    application.run_polling()

if __name__ == "__main__":
    main()
