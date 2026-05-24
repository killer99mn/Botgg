# -*- coding: utf-8 -*-
"""
ربات استخراج متن از PDF
تک‌فایلی – مناسب Termux – بدون نیاز به فایل اضافی
"""

import telebot
from telebot import types
import os
import PyPDF2

API_TOKEN = "8792321687:AAH3rPiUkkNvgZK1lOIKY6nSe79QrdTbk9g"   # ← توکن رباتت

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# پوشه ذخیره PDF
if not os.path.exists("pdfs"):
    os.makedirs("pdfs")


# ============================
#   شروع ربات
# ============================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "سلام مانی 👋\nیک فایل PDF بفرست تا متنش رو برات استخراج کنم."
    )


# ============================
#   دریافت PDF
# ============================

@bot.message_handler(content_types=["document"])
def get_pdf(message):
    file_info = bot.get_file(message.document.file_id)

    if not message.document.file_name.lower().endswith(".pdf"):
        bot.send_message(message.chat.id, "فقط فایل PDF بفرست ❌")
        return

    # دانلود PDF
    downloaded = bot.download_file(file_info.file_path)
    path = f"pdfs/{message.document.file_name}"

    with open(path, "wb") as f:
        f.write(downloaded)

    bot.send_message(message.chat.id, "فایل دریافت شد. در حال استخراج متن...")

    # استخراج متن
    try:
        reader = PyPDF2.PdfReader(path)
        text = ""

        for page in reader.pages:
            text += page.extract_text() + "\n"

        if len(text.strip()) == 0:
            bot.send_message(message.chat.id, "متنی داخل PDF پیدا نشد ❌")
            return

        # اگر متن خیلی طولانی بود، تکه‌تکه بفرست
        if len(text) > 4000:
            bot.send_message(message.chat.id, "متن طولانیه، دارم تکه‌تکه می‌فرستم...")
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                bot.send_message(message.chat.id, part)
        else:
            bot.send_message(message.chat.id, text)

    except Exception as e:
        bot.send_message(message.chat.id, f"خطا در خواندن PDF ❌\n{e}")


# ============================
#   اجرای ربات
# ============================

print("Bot is running...")
bot.infinity_polling()
