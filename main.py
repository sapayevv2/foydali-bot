import asyncio

# Pyrogram import bo'lishidan avval event loop yaratamiz
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import os
import re
import threading
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pyrogram import Client, filters
from pyrogram.types import Message as PyroMessage
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PasswordHashInvalid, 
    FloodWait, 
    RPCError
)

# ----------------- SOZLAMALAR -----------------
BOT_TOKEN = "8606815133:AAEHY0l5iWocDIC0CT5oxJ9DCEd8SyS5s4A"

API_ID = 34424037
API_HASH = "a2688add3c49c5015c996012b3a2dba3"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Xotira va obyektlar
user_data = {}
connected_accounts = {}
active_clients = {}
mention_flags = {}

# ----------------- SQLITE BAZA BILAN ISHLASH (/smsall uchun) -----------------
def db_start():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_user_to_db(user_id: int):
    try:
        conn = sqlite3.connect("bot_users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ----------------- MIDDLEWARE -----------------
@dp.message.middleware()
async def check_user_middleware(handler, event, data):
    if isinstance(event, types.Message) and event.from_user:
        add_user_to_db(event.from_user.id)
    return await handler(event, data)

# ----------------- KEYBOARDLAR -----------------

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Akkauntim")],
        [KeyboardButton(text="👨‍💻 Bot owner")]
    ],
    resize_keyboard=True
)

no_acc_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Yangi akkaunt qo'shish")],
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

has_acc_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Akkauntni o'chirish")],
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

add_acc_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📞 Telefon orqali")],
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⬅️ Bosh menyu")]
    ],
    resize_keyboard=True
)

def get_start_text(first_name: str) -> str:
    return (
        f"🤖 **FOYDALI Bot ga xush kelibsiz, {first_name}!**\n\n"
        "Kerakli bo'limni pastdagi tugmalardan tanlang 👇"
    )

# ----------------- AIOGRAM HANDLERLARI -----------------

# 1. /smsall buyrug'i (Mukammal ishlaydi)
@dp.message(Command("smsall"))
async def smsall_command_handler(message: types.Message):
    text_to_send = message.text.replace("/smsall", "").strip()
    if not text_to_send:
        await message.answer("❌ Yuborish uchun matn kiritmadingiz!\nNamuna: `/smsall Salom hammaga!`", parse_mode="Markdown")
        return

    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    if not users:
        await message.answer("⚠️ Bazada hali foydalanuvchilar mavjud emas.")
        return

    success = 0
    blocked = 0

    for row in users:
        u_id = row[0]
        try:
            await bot.send_message(u_id, text_to_send)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked += 1

    await message.answer(
        f"✅ **Xabar barchaga yuborildi!**\n\n"
        f"• Muvaffaqiyatli: {success} ta\n"
        f"• Botni bloklaganlar: {blocked} ta",
        parse_mode="Markdown"
    )

# 2. /start buyrug'i
@dp.message(Command("start"))
async def start_command_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_data:
        try:
            await user_data[user_id]["client"].disconnect()
        except Exception:
            pass
        del user_data[user_id]

    await message.answer(
        get_start_text(message.from_user.first_name),
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

# 3. Tugmalar va boshqa matnlar
@dp.message(F.text == "⬅️ Bosh menyu")
async def back_menu_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_data:
        try:
            await user_data[user_id]["client"].disconnect()
        except Exception:
            pass
        del user_data[user_id]

    await message.answer(
        get_start_text(message.from_user.first_name),
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

@dp.message(F.text == "👨‍💻 Bot owner")
async def owner_handler(message: types.Message):
    text = (
        "👨‍💻 **Bot Dasturchisi va Egasiga Bog'lanish:**\n\n"
        "Telegram: @sapayevv2"
    )
    await message.answer(text, reply_markup=main_keyboard, parse_mode="Markdown")

@dp.message(F.text == "👤 Akkauntim")
async def accounts_handler(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in connected_accounts and connected_accounts[user_id]:
        acc = connected_accounts[user_id]
        text = (
            "👤 **Akkauntim**\n\n"
            f"1. 🟢 Faol | **{acc['first_name']}**\n"
            f"📱 `{acc['phone']}`\n"
            f"🆔 `{acc['id']}`\n\n"
            "Kerakli amalni tanlang:"
        )
        markup = has_acc_keyboard
    else:
        text = (
            "👤 **Akkauntim**\n\n"
            "❌ Hozircha akkaunt ulanmagan.\n"
            "Yangi akkaunt qo'shish uchun pastdagi tugmani bosing."
        )
        markup = no_acc_keyboard
    
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "❌ Akkauntni o'chirish")
async def remove_account_handler(message: types.Message):
    user_id = message.from_user.id
    session_name = f"user_session_{user_id}"
    
    mention_flags[user_id] = False

    if user_id in active_clients:
        try:
            await active_clients[user_id].stop()
        except Exception:
            pass
        del active_clients[user_id]

    if user_id in connected_accounts:
        await message.answer("🔄 Akkaunt o'chirilmoqda...")
        del connected_accounts[user_id]
        
        if os.path.exists(f"{session_name}.session"):
            os.remove(f"{session_name}.session")
            
        text = "✅ **Akkaunt muvaffaqiyatli o'chirildi!**"
        markup = no_acc_keyboard
    else:
        text = "❌ Sizda ulangan akkaunt mavjud emas."
        markup = no_acc_keyboard
        
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "➕ Yangi akkaunt qo'shish")
async def add_account_handler(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in connected_accounts and connected_accounts[user_id]:
        await message.answer(
            "⚠️ **Sizda allaqachon akkaunt ulangan!**",
            reply_markup=has_acc_keyboard
        )
        return

    text = "➕ **Yangi akkaunt ulash**\n\nAkkauntni ulash uchun quyidagi tugmani bosing:"
    await message.answer(text, reply_markup=add_acc_keyboard, parse_mode="Markdown")

@dp.message(F.text == "📞 Telefon orqali")
async def phone_option_handler(message: types.Message):
    text = (
        "📱 **Telefon orqali ulash**\n\n"
        "Telefon raqamingizni yuboring (masalan: `+998901234567`)\n"
        "Yoki pastdagi tugma orqali yuboring:"
    )
    await message.answer(text, reply_markup=phone_keyboard, parse_mode="Markdown")

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    await process_phone_number(message, message.contact.phone_number)

@dp.message(F.text.regexp(r'^\+?[0-9]{10,15}$'))
async def text_phone_handler(message: types.Message):
    await process_phone_number(message, message.text.strip())

async def process_phone_number(message: types.Message, phone: str):
    user_id = message.from_user.id
    if not phone.startswith('+'):
        phone = '+' + phone

    session_name = f"user_session_{user_id}"
    
    if os.path.exists(f"{session_name}.session"):
        try:
            os.remove(f"{session_name}.session")
        except Exception:
            pass

    status_msg = await message.answer("🔄 Telegram'ga ulanish so'rovi yuborilmoqda...")
    client = Client(session_name, api_id=API_ID, api_hash=API_HASH)

    try:
        await client.connect()
        sent_code = await client.send_code(phone)
        
        user_data[user_id] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent_code.phone_code_hash,
            "step": "code"
        }
        
        text = (
            f"✅ Raqam qabul qilindi: `{phone}`\n\n"
            "📩 Telegram'ingizga yuborilgan tasdiqlash kodini kiriting.\n"
            "*(Kodni 1-2-3-4-5 ko'rinishida yuboring)*"
        )
        await status_msg.edit_text(text, parse_mode="Markdown")
        await message.answer("Amalni bekor qilish uchun pastdagi tugmani bosing:", reply_markup=cancel_keyboard)

    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        
        err_str = str(e)
        
        if "FLOOD_WAIT" in err_str or "420" in err_str:
            seconds_match = re.search(r'(\d+)', err_str)
            seconds = int(seconds_match.group(1)) if seconds_match else 60000
            soat = round(seconds / 3600, 1)
            
            pretty_text = (
                "⏳ **Vaqtincha cheklov!**\n\n"
                f"Siz Telegram'ga kirishingizda ko'p marotaba kodingizni so'ragansiz.\n"
                f"Telegram ushbu raqamga kod yuborishni vaqtincha to'xtatdi.\n\n"
                f"⏱ **Kutishingiz kerak bo'lgan vaqt:** taxminan **{soat} soat** ({seconds} soniya)."
            )
            await status_msg.edit_text(pretty_text, parse_mode="Markdown")
        else:
            await status_msg.edit_text(f"❌ **Xatolik yuz berdi:** {e}")

def clean_telegram_code(text: str) -> str:
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) == 5 else None

# Kod va parolni qabul qiluvchi handler
@dp.message(F.text & ~F.text.startswith("/"))
async def process_input_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]
    client: Client = data["client"]
    phone = data["phone"]

    if data.get("step") == "code":
        code = clean_telegram_code(message.text)
        if not code:
            await message.answer("❌ Noto'g'ri format! Kodni 5 xonali ko'rinishida yuboring.")
            return

        try:
            await client.sign_in(phone_number=phone, phone_code_hash=data["phone_code_hash"], phone_code=code)
            await finalize_login(message, client, user_id, phone)
        except SessionPasswordNeeded:
            data["step"] = "password"
            await message.answer("🔐 **2FA parolingizni kiriting:**", reply_markup=cancel_keyboard)
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")

    elif data.get("step") == "password":
        try:
            await client.check_password(message.text.strip())
            await finalize_login(message, client, user_id, phone)
        except PasswordHashInvalid:
            await message.answer("❌ Noto'g'ri parol! Qayta kiriting:")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")

async def finalize_login(message: types.Message, client: Client, user_id: int, phone: str):
    me = await client.get_me()
    
    connected_accounts[user_id] = {
        "first_name": me.first_name,
        "phone": phone,
        "id": me.id,
        "username": f"@{me.username}" if me.username else "Mavjud emas"
    }
    
    del user_data[user_id]

    try:
        await client.disconnect()
    except Exception:
        pass

    setup_pyrogram_listeners(client, user_id)
    active_clients[user_id] = client

    asyncio.create_task(client.start())

    await message.answer(f"✅ **Akkaunt muvaffaqiyatli ulandi va ishga tushdi!**\n\nIsm: {me.first_name}\nID: `{me.id}`", parse_mode="Markdown")
    await message.answer(
        "⚡ **.u funksiyasi faollashdi!**\n\n"
        "• Oddiy mention: `.u`\n"
        "• Matnli mention: `.u Sizning so'zingiz`\n"
        "• To'xtatish: `.su`",
        reply_markup=main_keyboard
    )

# ----------------- PYROGRAM LISTENERS -----------------

def setup_pyrogram_listeners(client: Client, user_id: int):

    @client.on_message(filters.me & filters.text)
    async def handle_commands(c: Client, msg: PyroMessage):
        cmd = msg.text.strip()

        if cmd == ".u" or cmd.startswith(".u "):
            if mention_flags.get(user_id, False):
                await msg.reply_text("⚠️ Mention davom etmoqda. To'xtatish uchun `.su` yuboring.")
                return

            custom_text = ""
            if cmd.startswith(".u "):
                custom_text = cmd[3:].strip()

            mention_flags[user_id] = True
            asyncio.create_task(run_mention_loop(c, msg, user_id, custom_text))

        elif cmd == ".su":
            if mention_flags.get(user_id, False):
                mention_flags[user_id] = False
                await msg.reply_text("🛑 **Mention to'xtatildi!**")
            else:
                await msg.reply_text("ℹ️ Hozirda faol mention yo'q.")

async def run_mention_loop(client: Client, msg: PyroMessage, user_id: int, custom_text: str = ""):
    chat_id = msg.chat.id
    
    try:
        await msg.delete()
    except Exception:
        pass

    try:
        async for member in client.get_chat_members(chat_id):
            if not mention_flags.get(user_id, False):
                break

            if member.user.is_bot or member.user.is_deleted:
                continue

            if member.user.username:
                user_mention = f"@{member.user.username}"
            else:
                name = member.user.first_name or "Foydalanuvchi"
                user_mention = f"[{name}](tg://user?id={member.user.id})"

            if custom_text:
                text_to_send = f"{user_mention} {custom_text}"
            else:
                text_to_send = user_mention

            await client.send_message(chat_id, text_to_send)

            for _ in range(15):
                if not mention_flags.get(user_id, False):
                    return
                await asyncio.sleep(0.1)

    except Exception as e:
        await client.send_message(chat_id, f"❌ Xatolik yuz berdi: {e}")
    finally:
        mention_flags[user_id] = False

# ----------------- THREADING WEB SERVER (RENDER FIX) -----------------

async def handle_ping(request):
    return web.Response(text="Bot runs fine!")

def run_web_server():
    server_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(server_loop)
    
    app = web.Application()
    app.router.add_get("/", handle_ping)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    server_loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, "0.0.0.0", port)
    server_loop.run_until_complete(site.start())
    print(f"Veb-server {port}-portda ishga tushdi!")
    server_loop.run_forever()

async def main():
    db_start()
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    loop.run_until_complete(main())


