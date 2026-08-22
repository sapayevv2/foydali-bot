import asyncio
import os
import re
import threading
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import Client, filters
from pyrogram.types import Message as PyroMessage
from pyrogram.errors import (
    SessionPasswordNeeded, 
    PasswordHashInvalid, 
    FloodWait, 
    RPCError
)

# ----------------- SOZLAMALAR -----------------
BOT_TOKEN = "8995038139:AAGbfl0eUNKJWm_BavdsWdAr-omsbmZaGhk"

API_ID = 34424037
API_HASH = "a2688add3c49c5015c996012b3a2dba3"

ADMIN_ID = 7559410726

# Majburiy obuna kanal username'i
CHANNEL_USERNAME = "@foydaliku_kanali"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}
connected_accounts = {}
active_clients = {}   
mention_flags = {}    

PHRASES_LIST = [
    "Almaz xachu", "Жоин", "Qanisz", "Mowina oberin 😁", "Oynamesmi sz",
    "Bitta sizi otaman ketaman qoshilin tez", "Qoshilin parichkez yolgiz qoldiyu",
    "Колиздан Ош йилу", "Kimni bolasi bu", "Siz nme jimsizee😅", "Maf goo",
    "Join", "Para keremasmi😂", "Mafia oynesmi", "Hammasi okeymi👍",
    "oyinga qoshilin", "Shashlikka boramizmi", "Lavash xochu 🌟",
    "Nyutonni 1 qonuni ni blasmi", "Kibrlani anaqasi bosezam kirin oyinga",
    "Хокими фарзанди босезам келн", "Пул Берн💔", "Salom", "byaxkelin",
    "Reak bosib otirganiz uchun oltin berilsa arzisiz😂", "Botmsz", "Keliinn endi",
    "Almaz berimi", "Yerning shakli qanday", "Tez qoshilmasez almaz yo😂",
    "Nime sz qoʻshilmesss", "qowilmasez kal siz🧑🏻‍🦲", "Keling aktivmassizu",
    "Jasmin sizi soginibti kelin", "Sz kemasez maf qizimedi😁", "Qoshililar 🫠",
    "Vevgi qilamiz qoshiling🤣", "Sizga yangi xabar borkeyingi utagda🤙🏻😹",
    "Hamma seni kutvoti O bez🗿", "Oling sizga", "Siz donsz🌚",
    "sz ni chaqirganim uchn almaz berin", "Kelin oo🗿", "Kozlariz chiroylikan join",
    "Qoshilmasez laqabz kal", "Келн бот 🗿", "Инстадан йозбкойн",
    "Bu hayot seni menga berdi dermidi😂", "Хайот тарвузде Ширин туйилмасн",
    "Szdayam pul koʻpayib ketdi", "Sushi yeysimi", "Mafga qo'shilsez AlpenGold oberaman😂",
    "Tfu tfu kibrligizga koz temasin😂 qoshilin oyinga", "KIA k5 oldim😁🦦",
    "Ухламен", "Amaki qoshilasmi", "Bot qo'shiling", "Реак босме кошлн мазги",
    "Joinasmi kibrbe", "Qayerda korganman sizi😁", "Сз нме утаг кмесз",
    "Hamma keldi bitta sz kam😐", "Qoshilsangz yaxw bolardi🫠", "Nma gap",
    "Qòlizi kòtaring don keldi🙈", "Baxona otmidi oyinga😁"
]

# ----------------- SQLITE BAZA -----------------
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

# ----------------- OBUNANI TEKSHIRISH FUNKSIYASI -----------------
async def check_user_subscription(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status not in ["left", "kicked"]:
            return True
    except Exception:
        return True 
    return False

async def ask_to_subscribe(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url="https://t.me/foydaliku_kanali")],
            [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub")]
        ]
    )
    # Parse mode ishlatilmadi, shuning uchun xatolik chiqmaydi
    await message.answer(
        "⚠️ Botdan foydalanish uchun quyidagi kanalga obuna bo'lishingiz kerak:\n\n"
        "👉 @foydaliku_kanali\n\n"
        "Kanalga a'zo bo'lgach, «✅ Obuna bo'ldim» tugmasini bosing.",
        reply_markup=keyboard
    )

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

# ----------------- CALLBACK HANDLER -----------------
@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subbed = await check_user_subscription(user_id)
    
    if is_subbed:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "✅ Rahmat! Obuna tasdiqlandi. Endi botdan to'liq foydalanishingiz mumkin.",
            reply_markup=main_keyboard
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

# ----------------- AIOGRAM HANDLERLARI -----------------

@dp.message(F.text == "⬅️ Bosh menyu")
@dp.message(Command("start"))
async def start_and_back_handler(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

    add_user_to_db(user_id)

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
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

    text = (
        "👨‍💻 **Bot Dasturchisi va Egasiga Bog'lanish:**\n\n"
        "Telegram: @sapayevv2"
    )
    await message.answer(text, reply_markup=main_keyboard, parse_mode="Markdown")

@dp.message(F.text == "👤 Akkauntim")
async def accounts_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

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
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

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
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

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
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

    text = (
        "📱 **Telefon orqali ulash**\n\n"
        "Telefon raqamingizni yuboring (masalan: `+998901234567`)\n"
        "Yoki pastdagi tugma orqali yuboring:"
    )
    await message.answer(text, reply_markup=phone_keyboard, parse_mode="Markdown")

@dp.message(F.contact)
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return
    await process_phone_number(message, message.contact.phone_number)

@dp.message(F.text.regexp(r'^\+?[0-9]{10,15}$'))
async def text_phone_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return
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
                f"Telegram ushbu raqamga kod yuborishni vaqtincha to'xtatdi.\n"
                f"⏱ **Kutish vaqti:** taxminan **{soat} soat**."
            )
            await status_msg.edit_text(pretty_text, parse_mode="Markdown")
        else:
            await status_msg.edit_text(f"❌ **Xatolik yuz berdi:** {e}")

def clean_telegram_code(text: str) -> str:
    digits = re.sub(r'\D', '', text)
    return digits if len(digits) == 5 else None

@dp.message(Command("smsall"))
async def smsall_command_handler(message: types.Message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ Bu buyruq faqat bot egasi uchun!")
        return

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

@dp.message(F.text)
async def process_input_handler(message: types.Message):
    user_id = message.from_user.id
    if not await check_user_subscription(user_id):
        await ask_to_subscribe(message)
        return

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
            await message.answer("🔐 **2FA (Oblachniy) parolingizni kiriting:**", reply_markup=cancel_keyboard)
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
    try:
        me = await client.get_me()
    except Exception as e:
        await message.answer(f"❌ Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
        return
    
    connected_accounts[user_id] = {
        "first_name": me.first_name,
        "phone": phone,
        "id": me.id,
        "username": f"@{me.username}" if me.username else "Mavjud emas"
    }
    
    if user_id in user_data:
        del user_data[user_id]

    setup_pyrogram_listeners(client, user_id)
    active_clients[user_id] = client

    await message.answer(f"✅ **Akkaunt muvaffaqiyatli ulandi va ishga tushdi!**\n\nIsm: {me.first_name}\nID: `{me.id}`", parse_mode="Markdown")
    await message.answer(
        "⚡ **Buyruqlar faollashdi!**\n\n"
        "• Oddiy utag: `.u`\n"
        "• Matnli utag: `.u Sizning so'zingiz`\n"
        "• KETMA-KET utag: `.ru`\n"
        "• To'xtatish: `.su`",
        reply_markup=main_keyboard
    )

# ----------------- PYROGRAM LISTENERS -----------------

def setup_pyrogram_listeners(client: Client, user_id: int):

    @client.on_message(filters.me)
    async def handle_commands(c: Client, msg: PyroMessage):
        if not msg.text:
            return

        cmd = msg.text.strip()

        if cmd == ".su":
            if mention_flags.get(user_id, False):
                mention_flags[user_id] = False
                await msg.reply_text("🛑 **Utag to'xtatildi!**")
            else:
                await msg.reply_text("ℹ️ Hozirda faol utag yo'q.")
            return

        if cmd == ".ru":
            if mention_flags.get(user_id, False):
                await msg.reply_text("⚠️ Utag davom etmoqda. To'xtatish uchun `.su` yuboring.")
                return

            mention_flags[user_id] = True
            asyncio.create_task(run_mention_loop(c, msg, user_id, use_sequential_phrases=True))
            return

        if cmd == ".u" or cmd.startswith(".u "):
            if mention_flags.get(user_id, False):
                await msg.reply_text("⚠️ Utag davom etmoqda. To'xtatish uchun `.su` yuboring.")
                return

            custom_text = cmd[3:].strip() if cmd.startswith(".u ") else ""
            mention_flags[user_id] = True
            asyncio.create_task(run_mention_loop(c, msg, user_id, custom_text, use_sequential_phrases=False))
            return

async def run_mention_loop(client: Client, msg: PyroMessage, user_id: int, custom_text: str = "", use_sequential_phrases: bool = False):
    chat_id = msg.chat.id
    
    try:
        await msg.delete()
    except Exception:
        pass

    try:
        count = 0
        total_phrases = len(PHRASES_LIST)
        
        async for member in client.get_chat_members(chat_id):
            if not mention_flags.get(user_id, False):
                break
                
            user = member.user
            if not user or user.is_bot or user.is_deleted:
                continue
                
            if user.id == client.me.id:
                continue

            if user.username:
                user_mention = f"@{user.username}"
            else:
                name = user.first_name or "Foydalanuvchi"
                user_mention = f"[{name}](tg://user?id={user.id})"

            try:
                if use_sequential_phrases and PHRASES_LIST:
                    phrase_index = count % total_phrases 
                    phrase = PHRASES_LIST[phrase_index]
                    text_to_send = f"{user_mention} {phrase}"
                elif custom_text:
                    text_to_send = f"{user_mention} {custom_text}"
                else:
                    text_to_send = user_mention
            except Exception:
                text_to_send = user_mention

            try:
                await client.send_message(chat_id, text_to_send)
                count += 1
            except Exception as send_err:
                if "FLOOD_WAIT" in str(send_err):
                    match = re.search(r'(\d+)', str(send_err))
                    wait_sec = int(match.group(1)) if match else 5
                    await asyncio.sleep(wait_sec)
                continue

            for _ in range(15):
                if not mention_flags.get(user_id, False):
                    return
                await asyncio.sleep(0.1)

        if count == 0:
            await client.send_message(chat_id, "❌ Guruh a'zolarini olish iloji bo'lmadi (Guruh yopiq yoki a'zolar ro'yxati yashiringan bo'lishi mumkin).")
        else:
            await client.send_message(chat_id, f"✅ Utag yakunlandi! Jami {count} ta foydalanuvchi belgilandi.")

    except Exception as e:
        try:
            await client.send_message(chat_id, f"❌ Xatolik yuz berdi: {e}")
        except Exception:
            pass
    finally:
        mention_flags[user_id] = False

# ----------------- WEB SERVER -----------------

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
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(main())


