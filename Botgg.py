# -*- coding: utf-8 -*-
"""
Heist Game Telegram Bot - Single File
پروژه حرفه‌ای بازی سرقت با چند مرحله، آیتم، انرژی، شانس و پایان‌های مختلف
قابل اجرا روی Termux و مناسب برای آپلود در GitHub
"""

import telebot
from telebot import types
import os
import json
import random
import datetime

# ================== تنظیمات اصلی ==================

API_TOKEN = "8881223378:AAH8DYmddcFe4t76aWiUKOM3c5vHenQE8Zw"  # ← توکن رباتت رو اینجا بذار

DATA_DIR = "players"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")


# ================== توابع کمکی ==================

def player_file(user_id):
    return os.path.join(DATA_DIR, f"{user_id}.json")


def new_player(user):
    return {
        "id": user.id,
        "username": user.username,
        "name": user.first_name,
        "created_at": datetime.datetime.now().isoformat(),
        "state": "TUTORIAL",  # اول آموزش
        "mission": None,
        "money": 500,
        "energy": 100,
        "items": [],
        "path": None,
        "guard_status": None,
        "result": None
    }


def load_player(user):
    path = player_file(user.id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        p = new_player(user)
        save_player(p)
        return p


def save_player(p):
    path = player_file(p["id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


def reset_player(p):
    p["state"] = "CHOOSE_MISSION"
    p["mission"] = None
    p["money"] = 500
    p["energy"] = 100
    p["items"] = []
    p["path"] = None
    p["guard_status"] = None
    p["result"] = None
    save_player(p)


def make_main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎮 شروع / ادامه بازی", "ℹ️ راهنما")
    kb.add("📊 وضعیت من", "🔁 شروع دوباره")
    return kb


def send_tutorial(chat_id):
    text = (
        "📚 <b>آموزش بازی سرقت (Heist Game)</b>\n\n"
        "تو نقش یک دزد حرفه‌ای رو بازی می‌کنی که می‌خواد یک سرقت بزرگ انجام بده.\n\n"
        "مراحل بازی:\n"
        "1️⃣ انتخاب مأموریت (بانک، موزه، گاوصندوق خصوصی)\n"
        "2️⃣ خرید تجهیزات (دریل، قفل‌شکن، هک، ماسک و...)\n"
        "3️⃣ انتخاب مسیر نفوذ (پشت‌بام، تونل، در اصلی)\n"
        "4️⃣ برخورد با نگهبان‌ها (مخفی شدن، حمله، فرار، استفاده از آیتم)\n"
        "5️⃣ سرقت نهایی و باز کردن گاوصندوق\n\n"
        "هر تصمیم روی <b>شانس موفقیت</b>، <b>انرژی</b> و <b>پایان بازی</b> تأثیر می‌ذاره.\n"
        "اگر انرژی‌ات صفر بشه یا خیلی بد تصمیم بگیری، ممکنه گیر بیفتی! 😈\n\n"
        "برای شروع، روی «🎮 شروع / ادامه بازی» بزن."
    )
    bot.send_message(chat_id, text, reply_markup=make_main_menu())


def mission_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🏦 سرقت از بانک", "🏛 سرقت از موزه")
    kb.add("🔐 گاوصندوق خصوصی")
    kb.add("🔙 بازگشت به منو")
    return kb


def shop_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🛠 دریل صنعتی (300)", "🔓 قفل‌شکن (150)")
    kb.add("🎭 ماسک حرارتی (150)", "💻 دستگاه هک (200)")
    kb.add("💤 اسلحه بی‌حس‌کننده (200)")
    kb.add("✅ ادامه", "🔙 انصراف")
    return kb


def path_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🌉 پشت‌بام", "🕳 تونل فاضلاب", "🚪 در اصلی")
    kb.add("🔙 بازگشت به منو")
    return kb


def guard_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👀 مخفی شدن", "⚔️ حمله", "🏃 فرار")
    kb.add("🎭 استفاده از ماسک", "💤 استفاده از اسلحه بی‌حس‌کننده")
    return kb


def final_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🧰 تلاش برای باز کردن گاوصندوق", "💻 تلاش برای هک سیستم")
    kb.add("🚫 انصراف و فرار")
    return kb


def calc_success(base, p):
    bonus = 0
    if "دریل صنعتی" in p["items"]:
        bonus += 25
    if "قفل‌شکن" in p["items"]:
        bonus += 15
    if "دستگاه هک" in p["items"]:
        bonus += 20
    chance = max(5, min(95, base + bonus))
    roll = random.randint(1, 100)
    return roll <= chance, chance, roll


def change_energy(p, amount):
    p["energy"] += amount
    if p["energy"] < 0:
        p["energy"] = 0


def status_text(p):
    return (
        f"📊 <b>وضعیت فعلی تو:</b>\n"
        f"ماموریت: {p['mission'] or 'انتخاب نشده'}\n"
        f"پول: {p['money']}\n"
        f"انرژی: {p['energy']}\n"
        f"آیتم‌ها: {', '.join(p['items']) if p['items'] else 'هیچی'}\n"
        f"مرحله: {p['state']}"
    )


# ================== دستورات ==================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user
    p = load_player(user)

    bot.send_message(
        message.chat.id,
        f"سلام {user.first_name} 👋\n"
        "به بازی حرفه‌ای <b>سرقت بزرگ (Heist Game)</b> خوش اومدی.\n\n"
        "اول یک آموزش کوتاه بهت می‌دم تا قشنگ دستت بیاد چطوری بازی کنی.",
        reply_markup=make_main_menu()
    )

    p["state"] = "TUTORIAL"
    save_player(p)
    send_tutorial(message.chat.id)


@bot.message_handler(commands=["status"])
def cmd_status(message):
    user = message.from_user
    p = load_player(user)
    bot.send_message(message.chat.id, status_text(p), reply_markup=make_main_menu())


# ================== هندلر اصلی متن ==================

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    user = message.from_user
    text = message.text.strip()
    p = load_player(user)

    # منوی اصلی
    if text == "ℹ️ راهنما":
        send_tutorial(message.chat.id)
        return

    if text == "📊 وضعیت من":
        bot.send_message(message.chat.id, status_text(p), reply_markup=make_main_menu())
        return

    if text == "🔁 شروع دوباره":
        reset_player(p)
        bot.send_message(
            message.chat.id,
            "بازی از اول شروع شد. اول مأموریتت رو انتخاب کن.",
            reply_markup=mission_keyboard()
        )
        return

    if text == "🎮 شروع / ادامه بازی":
        if p["state"] in ["TUTORIAL", "CHOOSE_MISSION"]:
            p["state"] = "CHOOSE_MISSION"
            save_player(p)
            bot.send_message(
                message.chat.id,
                "اول از همه، <b>نوع سرقت</b> رو انتخاب کن:",
                reply_markup=mission_keyboard()
            )
        elif p["state"] == "SHOP":
            bot.send_message(
                message.chat.id,
                "در حال حاضر در مرحله خرید تجهیزات هستی.",
                reply_markup=shop_keyboard()
            )
        elif p["state"] == "CHOOSE_PATH":
            bot.send_message(
                message.chat.id,
                "الان باید مسیر نفوذ رو انتخاب کنی.",
                reply_markup=path_keyboard()
            )
        elif p["state"] == "GUARD":
            bot.send_message(
                message.chat.id,
                "درگیر نگهبان‌ها هستی! تصمیم بگیر چیکار می‌کنی.",
                reply_markup=guard_keyboard()
            )
        elif p["state"] == "FINAL":
            bot.send_message(
                message.chat.id,
                "الان در مرحله نهایی سرقت هستی.",
                reply_markup=final_keyboard()
            )
        else:
            bot.send_message(
                message.chat.id,
                "در حال حاضر در وضعیت نامشخصی هستی، برای اطمینان «🔁 شروع دوباره» رو بزن.",
                reply_markup=make_main_menu()
            )
        return

    # بازگشت به منو
    if text == "🔙 بازگشت به منو":
        bot.send_message(message.chat.id, "به منوی اصلی برگشتی.", reply_markup=make_main_menu())
        return

    # ================== مرحله انتخاب مأموریت ==================
    if p["state"] == "CHOOSE_MISSION":
        if text in ["🏦 سرقت از بانک", "🏛 سرقت از موزه", "🔐 گاوصندوق خصوصی"]:
            p["mission"] = text
            p["state"] = "SHOP"
            save_player(p)
            bot.send_message(
                message.chat.id,
                f"ماموریتت انتخاب شد: {text}\n\n"
                "حالا وقتشه تجهیزاتت رو آماده کنی.\n"
                "پول فعلی: <b>{}</b>\n"
                "هر آیتم روی شانس موفقیتت تأثیر می‌ذاره.\n"
                "هرچقدر حرفه‌ای‌تر آماده بشی، احتمال موفقیتت بیشتره 😉".format(p["money"]),
                reply_markup=shop_keyboard()
            )
            return
        else:
            bot.send_message(
                message.chat.id,
                "از بین گزینه‌ها یکی رو انتخاب کن.",
                reply_markup=mission_keyboard()
            )
            return

    # ================== مرحله خرید تجهیزات ==================
    if p["state"] == "SHOP":
        if text == "🔙 انصراف":
            p["state"] = "CHOOSE_MISSION"
            save_player(p)
            bot.send_message(
                message.chat.id,
                "به مرحله انتخاب مأموریت برگشتی.",
                reply_markup=mission_keyboard()
            )
            return

        if text == "✅ ادامه":
            p["state"] = "CHOOSE_PATH"
            save_player(p)
            bot.send_message(
                message.chat.id,
                "خوبه، حالا باید مسیر نفوذ رو انتخاب کنی.\n"
                "هر مسیر ریسک و مصرف انرژی خودش رو داره.",
                reply_markup=path_keyboard()
            )
            return

        # خرید آیتم‌ها
        items_shop = {
            "🛠 دریل صنعتی (300)": ("دریل صنعتی", 300),
            "🔓 قفل‌شکن (150)": ("قفل‌شکن", 150),
            "🎭 ماسک حرارتی (150)": ("ماسک حرارتی", 150),
            "💻 دستگاه هک (200)": ("دستگاه هک", 200),
            "💤 اسلحه بی‌حس‌کننده (200)": ("اسلحه بی‌حس‌کننده", 200),
        }

        if text in items_shop:
            item_name, price = items_shop[text]
            if item_name in p["items"]:
                bot.send_message(message.chat.id, "این آیتم رو قبلاً خریدی.")
                return
            if p["money"] < price:
                bot.send_message(message.chat.id, "پولت برای این آیتم کافی نیست ❌")
                return
            p["money"] -= price
            p["items"].append(item_name)
            save_player(p)
            bot.send_message(
                message.chat.id,
                f"✅ {item_name} خریداری شد.\n"
                f"پول باقی‌مانده: <b>{p['money']}</b>"
            )
            return

        bot.send_message(message.chat.id, "از بین گزینه‌های فروشگاه انتخاب کن.", reply_markup=shop_keyboard())
        return

    # ================== مرحله انتخاب مسیر ==================
    if p["state"] == "CHOOSE_PATH":
        if text not in ["🌉 پشت‌بام", "🕳 تونل فاضلاب", "🚪 در اصلی"]:
            bot.send_message(message.chat.id, "یکی از مسیرها رو انتخاب کن.", reply_markup=path_keyboard())
            return

        p["path"] = text

        if text == "🌉 پشت‌بام":
            change_energy(p, -15)
            desc = "از پشت‌بام وارد می‌شی. ریسک متوسط، مصرف انرژی کم."
        elif text == "🕳 تونل فاضلاب":
            change_energy(p, -30)
            desc = "از تونل فاضلاب می‌ری. ریسک کم، ولی انرژی زیادی مصرف می‌کنی."
        else:
            change_energy(p, -10)
            desc = "از در اصلی می‌ری. ریسک بالاست، ولی سریع‌تره."

        p["state"] = "GUARD"
        # وضعیت نگهبان
        p["guard_status"] = random.choice(["خواب", "گشت", "هشیار"])
        save_player(p)

        bot.send_message(
            message.chat.id,
            f"{desc}\n"
            f"انرژی فعلی: <b>{p['energy']}</b>\n\n"
            f"وضعیت نگهبان‌ها: <b>{p['guard_status']}</b>\n"
            "حالا باید تصمیم بگیری چیکار می‌کنی.",
            reply_markup=guard_keyboard()
        )
        return

    # ================== مرحله نگهبان ==================
    if p["state"] == "GUARD":
        action = text

        if action not in ["👀 مخفی شدن", "⚔️ حمله", "🏃 فرار", "🎭 استفاده از ماسک", "💤 استفاده از اسلحه بی‌حس‌کننده"]:
            bot.send_message(message.chat.id, "یکی از گزینه‌ها رو انتخاب کن.", reply_markup=guard_keyboard())
            return

        guard = p["guard_status"]

        # استفاده از آیتم‌ها
        if action == "🎭 استفاده از ماسک":
            if "ماسک حرارتی" not in p["items"]:
                bot.send_message(message.chat.id, "ماسک نداری که استفاده کنی!")
                return
            p["guard_status"] = "گیج"
            change_energy(p, -5)
            save_player(p)
            bot.send_message(
                message.chat.id,
                "ماسک رو زدی، نگهبان‌ها گیج شدن و سخت‌تر می‌تونن شناساییت کنن.\n"
                f"انرژی فعلی: <b>{p['energy']}</b>"
            )
            return

        if action == "💤 استفاده از اسلحه بی‌حس‌کننده":
            if "اسلحه بی‌حس‌کننده" not in p["items"]:
                bot.send_message(message.chat.id, "اسلحه بی‌حس‌کننده نداری!")
                return
            success, chance, roll = calc_success(70, p)
            change_energy(p, -10)
            if success:
                p["guard_status"] = "از کار افتاده"
                msg = (
                    f"شلیک کردی و نگهبان‌ها بی‌حس شدن ✅\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n"
                    "راه برای ادامه تقریباً امنه."
                )
            else:
                p["guard_status"] = "هشیار شدید"
                msg = (
                    f"شلیک موفق نبود و نگهبان‌ها هشیارتر شدن ❌\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n"
                    "کار برات سخت‌تر شد!"
                )
            save_player(p)
            bot.send_message(
                message.chat.id,
                msg + f"\nانرژی فعلی: <b>{p['energy']}</b>",
                reply_markup=guard_keyboard()
            )
            return

        # مخفی شدن / حمله / فرار
        base = 0
        if action == "👀 مخفی شدن":
            base = 60 if guard in ["خواب", "گیج"] else 40
            change_energy(p, -5)
        elif action == "⚔️ حمله":
            base = 50 if guard in ["خواب", "گیج"] else 35
            change_energy(p, -15)
        elif action == "🏃 فرار":
            base = 70
            change_energy(p, -20)

        success, chance, roll = calc_success(base, p)

        if not success and action == "🏃 فرار":
            p["result"] = "FAIL_ESCAPE"
            p["state"] = "END"
            save_player(p)
            bot.send_message(
                message.chat.id,
                f"سعی کردی فرار کنی ولی گیر افتادی ❌\n"
                f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                "پایان بد: دستگیر شدی و سرقت شکست خورد.",
                reply_markup=make_main_menu()
            )
            return

        if not success and action in ["👀 مخفی شدن", "⚔️ حمله"]:
            # اگر شکست بخوره، احتمال دستگیری
            arrest_chance = 40 if guard in ["هشیار", "هشیار شدید"] else 25
            arrest_roll = random.randint(1, 100)
            if arrest_roll <= arrest_chance:
                p["result"] = "ARRESTED"
                p["state"] = "END"
                save_player(p)
                bot.send_message(
                    message.chat.id,
                    f"حرکتت جواب نداد و نگهبان‌ها گرفتنت ❌\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n"
                    f"(شانس دستگیری: {arrest_chance}٪، عدد تاس: {arrest_roll})\n\n"
                    "پایان بد: دستگیر شدی.",
                    reply_markup=make_main_menu()
                )
                return
            else:
                bot.send_message(
                    message.chat.id,
                    f"حرکتت موفق نبود، ولی معجزه شد و فعلاً گیر نیفتادی 😅\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n"
                    "یک تصمیم دیگه بگیر.",
                    reply_markup=guard_keyboard()
                )
                save_player(p)
                return

        # موفقیت
        if success:
            p["state"] = "FINAL"
            save_player(p)
            bot.send_message(
                message.chat.id,
                f"حرکتت جواب داد ✅\n"
                f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                "حالا به گاوصندوق/هدف اصلی رسیدی.\n"
                "باید تصمیم بگیری چطور سرقت نهایی رو انجام بدی.",
                reply_markup=final_keyboard()
            )
            return

    # ================== مرحله نهایی ==================
    if p["state"] == "FINAL":
        if text not in ["🧰 تلاش برای باز کردن گاوصندوق", "💻 تلاش برای هک سیستم", "🚫 انصراف و فرار"]:
            bot.send_message(message.chat.id, "یکی از گزینه‌های مرحله نهایی رو انتخاب کن.", reply_markup=final_keyboard())
            return

        if text == "🚫 انصراف و فرار":
            p["result"] = "ESCAPE_EMPTY"
            p["state"] = "END"
            save_player(p)
            bot.send_message(
                message.chat.id,
                "تصمیم گرفتی ریسک نکنی و فرار کنی.\n"
                "پایان خنثی: نه چیزی دزدیدی، نه گیر افتادی.\n"
                "شاید دفعه بعد شجاع‌تر باشی 😉",
                reply_markup=make_main_menu()
            )
            return

        if text == "🧰 تلاش برای باز کردن گاوصندوق":
            base = 35
            success, chance, roll = calc_success(base, p)
            change_energy(p, -15)
            if success:
                p["result"] = "SUCCESS_SAFE"
                p["state"] = "END"
                reward = random.randint(800, 1500)
                p["money"] += reward
                save_player(p)
                bot.send_message(
                    message.chat.id,
                    f"گاوصندوق رو باز کردی و پول زیادی برداشتی 💰✅\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                    f"پایان خوب: سرقت موفق بود و فرار کردی.\n"
                    f"پول جدیدت: <b>{p['money']}</b>",
                    reply_markup=make_main_menu()
                )
            else:
                p["result"] = "FAIL_SAFE"
                p["state"] = "END"
                save_player(p)
                bot.send_message(
                    message.chat.id,
                    f"گاوصندوق باز نشد و سیستم امنیتی فعال شد ❌\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                    "پایان بد: آژیرها روشن شد و مجبور شدی فرار کنی، بدون هیچ غنیمتی.",
                    reply_markup=make_main_menu()
                )
            return

        if text == "💻 تلاش برای هک سیستم":
            base = 40
            success, chance, roll = calc_success(base, p)
            change_energy(p, -10)
            if success:
                p["result"] = "SUCCESS_HACK"
                p["state"] = "END"
                reward = random.randint(600, 1300)
                p["money"] += reward
                save_player(p)
                bot.send_message(
                    message.chat.id,
                    f"سیستم امنیتی رو هک کردی و راه رو باز کردی 💻✅\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                    f"پایان خوب: سرقت موفق بود و بدون سر و صدا فرار کردی.\n"
                    f"پول جدیدت: <b>{p['money']}</b>",
                    reply_markup=make_main_menu()
                )
            else:
                p["result"] = "FAIL_HACK"
                p["state"] = "END"
                save_player(p)
                bot.send_message(
                    message.chat.id,
                    f"هک ناموفق بود و سیستم امنیتی قفل شد ❌\n"
                    f"(شانس موفقیت: {chance}٪، عدد تاس: {roll})\n\n"
                    "پایان متوسط: گیر نیفتادی، ولی دست خالی برگشتی.",
                    reply_markup=make_main_menu()
                )
            return

    # اگر هیچ‌کدوم نخورد:
    bot.send_message(
        message.chat.id,
        "ورودی‌ات با وضعیت فعلی بازی هماهنگ نیست.\n"
        "اگر گیج شدی، «📊 وضعیت من» یا «🔁 شروع دوباره» رو بزن.",
        reply_markup=make_main_menu()
    )


# ================== اجرای ربات ==================

def main():
    print("Heist Game Bot is running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)


if __name__ == "__main__":
    main()
