import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, time
import pytz
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Render uxlab qolmasligi uchun HTTP server
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

# Foydalanuvchilar ma'lumoti va amaliyotlar tarixi
user_data = {}

def get_user_info(chat_id: int):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "days": 0,           # Ishga kelgan kunlar soni
            "daily_total": 0,   # Faqat 270k (Hisobot 1) jami summasi
            "extra_total": 0,   # Faqat qo'shimcha (Hisobot 2) jami summasi
            "history_1": [],    # Hisobot 1 uchun kiritilgan sanalar va summalar tarixi
            "history_2": []     # Hisobot 2 uchun kiritilgan sanalar va summalar tarixi
        }
    return user_data[chat_id]

# Menyu tugmalari
def get_keyboard():
    keyboard = [
        [KeyboardButton("✅ Ha (270,000 so'm)"), KeyboardButton("❌ Yo'q")],
        [KeyboardButton("📊 Hisobot 1"), KeyboardButton("📊 Hisobot 2")],
        [KeyboardButton("🔄 Tozalash 1"), KeyboardButton("🔄 Tozalash 2")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Bot chap tomondagi "Menu" tugmasiga buyruqlarni qo'shish
async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Botni qayta ishga tushirish"),
        BotCommand("reset", "Barcha ma'lumotlarni tozalash")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = get_user_info(chat_id)

    schedule_daily_notification(context, chat_id)

    text = (
        f"Xush kelibsiz! 👋\n\n"
        f"Har kuni soat 09:00 da ishga kelganingizni so'rab turaman.\n\n"
        f"💡 **Qo'shimcha kiritish qoidasi:**\n"
        f"• `10` -> **10,000 so'm**\n"
        f"• `200` -> **200,000 so'm**\n"
        f"• `500` -> **500,000 so'm**\n\n"
        f"📊 **Hisobot 1 balansi:** **{user['daily_total']:,} so'm**\n"
        f"📊 **Hisobot 2 balansi:** **{user['extra_total']:,} so'm**"
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

    # HA javobi (Hisobot 1)
    if text in ["✅ ha (270,000 so'm)", "h", "ha"]:
        user["days"] += 1
        user["daily_total"] += DAILY_EARNING
        user["history_1"].append(f"📅 {current_time_str} — +{DAILY_EARNING:,} so'm")

        msg = (
            f"✅ **Qabul qilindi!**\n\n"
            f"📅 **Sana va vaqt:** `{current_time_str}`\n"
            f"📌 **Holat:** Ishdasiz (+{DAILY_EARNING:,} so'm qo'shildi)\n\n"
            f"📊 **Hisobot 1 (Kunlik):** {user['days']} kun / {user['daily_total']:,} so'm\n"
            f"💰 **Jami umumiy balans:** {user['daily_total']:,} so'm"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # YO'Q javobi
    elif text in ["❌ yo'q", "y", "yo'q", "yoq"]:
        msg = (
            f"❌ **Qabul qilindi.**\n\n"
            f"📅 **Sana va vaqt:** `{current_time_str}`\n"
            f"📌 **Holat:** Kelmadingiz deb belgilandi\n\n"
            f"📊 **Hisobot 1 (Kunlik):** {user['days']} kun / {user['daily_total']:,} so'm\n"
            f"💰 **Jami umumiy balans:** {user['daily_total']:,} so'm"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # HISOBOT 1 (Kunlik ish haqi ro'yxati va sanalari)
    elif text == "📊 hisobot 1":
        history_text = "\n".join(user["history_1"]) if user["history_1"] else "Hali ma'lumot kiritilmagan."
        msg = (
            f"📊 **Hisobot 1 (Kunlik ish haqi tarixi):**\n\n"
            f"{history_text}\n\n"
            f"------------------------------\n"
            f"📅 Jami kelingan kunlar: **{user['days']} kun**\n"
            f"💵 Jami kunlik ish haqi: **{user['daily_total']:,} so'm**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # HISOBOT 2 (Qo'shimcha kiritilgan summalar va sanalari)
    elif text == "📊 hisobot 2":
        history_text = "\n".join(user["history_2"]) if user["history_2"] else "Hali ma'lumot kiritilmagan."
        msg = (
            f"📊 **Hisobot 2 (Qo'shimcha kiritilganlar tarixi):**\n\n"
            f"{history_text}\n\n"
            f"------------------------------\n"
            f"➕ Jami qo'shimcha yig'indi: **{user['extra_total']:,} so'm**"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # TOZALASH 1 (Faqat Hisobot 1 ma'lumotlarini nollash)
    elif text == "🔄 tozalash 1":
        user["days"] = 0
        user["daily_total"] = 0
        user["history_1"] = []
        msg = "🔄 **Hisobot 1 (Kunlik hisoblar) tozalandi!**"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    # TOZALASH 2 (Faqat Hisobot 2 ma'lumotlarini nollash)
    elif text == "🔄 tozalash 2":
        user["extra_total"] = 0
        user["history_2"] = []
        msg = "🔄 **Hisobot 2 (Qo'shimcha summalar) tozalandi!**"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())

    else:
        # Sonlarni hisoblash (Hisobot 2 ga sana va vaqti bilan saqlash)
        cleaned_text = raw_text.replace(" ", "").replace(",", "")
        if cleaned_text.isdigit():
            val = int(cleaned_text)
            
            if val < 10000:
                added_amount = val * 1000
            else:
                added_amount = val

            user["extra_total"] += added_amount
            user["history_2"].append(f"📅 {current_time_str} — +{added_amount:,} so'm")

            msg = (
                f"💵 **Qo'shimcha summa qo'shildi!**\n\n"
                f"📅 **Sana va vaqt:** `{current_time_str}`\n"
                f"➕ Qo'shildi: **+{added_amount:,} so'm**\n\n"
                f"📊 **Hisobot 2 yig'indisi:** **{user['extra_total']:,} so'm**"
            )
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_keyboard())
        else:
            await update.message.reply_text(
                "Iltimos, pastdagi tugmalardan foydalaning, **h** / **y** deb yozing yoki summani son ko'rinishida kiriting (masalan: `10`, `200`, `500`).",
                reply_markup=get_keyboard()
            )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = get_user_info(chat_id)
    user["days"] = 0
    user["daily_total"] = 0
    user["extra_total"] = 0
    user["history_1"] = []
    user["history_2"] = []
    await update.message.reply_text("🔄 Barcha ma'lumotlar va tarixlar tozalandi!", reply_markup=get_keyboard())

def main() -> None:
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    threading.Thread(target=start_health_check_server, daemon=True).start()

    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))

    application.run_polling()

if __name__ == "__main__":
    main()
