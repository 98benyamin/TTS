import requests
import urllib.parse
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from uuid import uuid4
import logging
from aiohttp import web

# تنظیم لاگینگ برای دیباگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7520523575:AAHNy73MjTRmatJejA96BlaNu0hGHczfYvk"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
MAX_TEXT_LENGTH = 1000  # حداکثر طول متن
MAX_FEELING_LENGTH = 500  # حداکثر طول حس

# لیست صداهای پشتیبانی‌شده
SUPPORTED_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer",
    "coral", "verse", "ballad", "ash", "sage", "amuch", "dan", "elan"
]

# مراحل مکالمه
FEELING, TEXT, VOICE = range(3)

def generate_audio(text, instructions, voice, output_file):
    logger.info(f"تولید صدا با متن: {text[:50]}..., حس: {instructions[:50]}..., صدا: {voice}")
    if voice not in SUPPORTED_VOICES:
        logger.error(f"صدا {voice} پشتیبانی نمی‌شود")
        return False
    
    prompt = (
        f"Deliver the following text with the feeling described below:\n"
        f"Instructions: {instructions}\n\n"
        f"Now please repeat the text I give you with the same feeling I gave you, without adding anything to the text. Repeat the text:\n"
        f"{text}"
    )
    
    base_url = "https://text.pollinations.ai/"
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{base_url}{encoded_prompt}?model=openai-audio&voice={voice}"
    
    try:
        logger.info(f"ارسال درخواست GET به API: {url[:100]}...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            logger.info(f"فایل صوتی ذخیره شد: {output_file}")
            return True
        else:
            logger.error(f"خطا در API Pollinations: کد وضعیت {response.status_code}, پاسخ: {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"خطا در ارتباط با API Pollinations: {str(e)}")
        return False
    except IOError as e:
        logger.error(f"خطا در ذخیره فایل صوتی: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در تولید صدا: {str(e)}")
        return False

def create_progress_bar(percentage):
    filled = percentage // 5  # هر 5% یک بلوک
    empty = 20 - filled
    bar = "█" * filled + "□" * empty
    return f"[{bar} {percentage}%]"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    try:
        keyboard = [["🎙 تبدیل متن به صدا"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🎙 به ربات تبدیل متن به صدا خوش آمدید!\n\n"
            "من می‌توانم متن شما را با هر حس و صدایی که انتخاب کنید، به گفتار تبدیل کنم.\n"
            "برای شروع، روی دکمه زیر کلیک کنید:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🎙 تبدیل متن به صدا":
        try:
            await update.message.reply_text(
                "لطفاً حس یا دستورالعمل‌های صدا رو وارد کنید (حداکثر 500 کاراکتر).\n"
                "مثال: Dramatic یا Gruff, fast-talking, New York accent"
            )
            context.user_data["state"] = "feeling"
            return None
        except Exception as e:
            logger.error(f"خطا در ارسال پیام برای حس: {str(e)}")
            return None
    
    if "state" in context.user_data:
        if context.user_data["state"] == "feeling":
            feeling = update.message.text
            if len(feeling) > MAX_FEELING_LENGTH:
                await update.message.reply_text(
                    f"خطا: حس شما {len(feeling)} کاراکتر است. لطفاً حسی با حداکثر {MAX_FEELING_LENGTH} کاراکتر وارد کنید."
                )
                return None
            
            context.user_data["feeling"] = feeling
            context.user_data["state"] = "text"
            await update.message.reply_text(
                "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\n"
                "مثال: Yeah, yeah, ya got Big Apple Insurance"
            )
            return None
        
        elif context.user_data["state"] == "text":
            text = update.message.text
            if len(text) > MAX_TEXT_LENGTH:
                await update.message.reply_text(
                    f"خطا: متن شما {len(text)} کاراکتر است. لطفاً متنی با حداکثر {MAX_TEXT_LENGTH} کاراکتر وارد کنید."
                )
                return None
            
            context.user_data["text"] = text
            context.user_data["state"] = "voice"
            
            # نمایش کیبورد صداها
            keyboard = []
            row = []
            for voice in SUPPORTED_VOICES:
                row.append(InlineKeyboardButton(voice.capitalize(), callback_data=voice))
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "لطفاً یکی از صداهای زیر رو انتخاب کنید:",
                reply_markup=reply_markup
            )
            return None
    
    return None

async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    voice = query.data
    user_id = update.effective_user.id
    logger.info(f"صدا دریافت شد از کاربر {user_id}: {voice}")
    
    text = context.user_data["text"]
    instructions = context.user_data["feeling"]
    output_file = f"output_{uuid4()}.mp3"
    
    # نمایش پیام‌های اولیه
    try:
        status_message = await query.message.reply_text("در حال آنالیز متن 🔍")
        await asyncio.sleep(1.5)
        await status_message.edit_text("درحال تولید صدا 🎙")
        
        # نمایش پروگرس بار در دکمه شیشه‌ای
        progress_duration = 4  # 4 ثانیه برای پروگرس بار نمایشی
        step_duration = progress_duration / 20  # زمان هر 5%
        
        for percentage in range(0, 101, 5):
            try:
                keyboard = [[InlineKeyboardButton(f"{create_progress_bar(percentage)}", callback_data="progress")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_message.edit_text(
                    "درحال تولید صدا 🎙",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"خطا در به‌روزرسانی پروگرس بار ({percentage}%) برای کاربر {user_id}: {str(e)}")
            await asyncio.sleep(step_duration)
        
        # حذف دکمه پروگرس بار
        await status_message.edit_text("تولید صدا در حال انجام است...")
        
    except Exception as e:
        logger.error(f"خطا در ارسال یا به‌روزرسانی پیام وضعیت برای کاربر {user_id}: {str(e)}")
        await query.message.reply_text(
            "خطا در شروع تولید صدا. لطفاً دوباره امتحان کنید."
        )
        return None
    
    # ارسال درخواست به API
    success = generate_audio(text, instructions, voice, output_file)
    
    if success:
        try:
            with open(output_file, "rb") as audio:
                await query.message.reply_audio(
                    audio=audio,
                    caption=f"صدا: {voice.capitalize()}",
                    title="Generated Audio"
                )
            os.remove(output_file)
            logger.info(f"فایل صوتی ارسال و حذف شد برای کاربر {user_id}: {output_file}")
            
            await status_message.edit_text(
                "✅ فایل صوتی با موفقیت ارسال شد! برای تولید دوباره، روی دکمه تبدیل متن به صدا کلیک کنید."
            )
                
        except Exception as e:
            logger.error(f"خطا در ارسال فایل صوتی برای کاربر {user_id}: {str(e)}")
            try:
                await status_message.edit_text(
                    "❌ خطا در ارسال فایل صوتی. لطفاً دوباره امتحان کنید."
                )
            except Exception:
                logger.warning(f"ناتوانی در به‌روزرسانی پیام وضعیت برای کاربر {user_id}")
        finally:
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except Exception:
                logger.warning(f"ناتوانی در حذف فایل صوتی برای کاربر {user_id}: {output_file}")
    else:
        try:
            await status_message.edit_text(
                "❌ خطا در تولید صدا. لطفاً مطمئن شوید حس (حداکثر 500 کاراکتر) و متن (حداکثر 1000 کاراکتر) مناسب هستند و صدا پشتیبانی می‌شود."
            )
        except Exception:
            logger.warning(f"ناتوانی در به‌روزرسانی پیام وضعیت برای کاربر {user_id}")
    
    context.user_data.clear()
    return None

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /cancel از کاربر: {user_id}")
    try:
        await update.message.reply_text(
            "عملیات لغو شد. با /generate می‌تونید دوباره شروع کنید."
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /cancel برای کاربر {user_id}: {str(e)}")
    context.user_data.clear()
    return ConversationHandler.END

# تنظیم سرور Webhook
async def webhook_handler(request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
        return web.Response()
    except Exception as e:
        logger.error(f"خطا در پردازش درخواست webhook: {str(e)}")
        return web.Response(status=500)

async def setup_webhook():
    try:
        app = web.Application()
        app.router.add_post('/webhook', webhook_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)  # پورت 8080 برای Render
        await site.start()
        logger.info("سرور Webhook شروع شد")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی سرور webhook: {str(e)}")
        raise

# تنظیم ربات با تایم‌اوت بالاتر
application = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(CallbackQueryHandler(receive_voice))

# اجرای ربات با webhook
async def main():
    try:
        await application.initialize()
        logger.info("ربات مقداردهی اولیه شد")
        await application.start()
        logger.info("ربات شروع شد")
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook تنظیم شد: {WEBHOOK_URL}")
        await setup_webhook()
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی یا اجرای ربات: {str(e)}")
        raise
    finally:
        try:
            if application.running:
                logger.info("توقف ربات")
                await application.bot.delete_webhook()
                await application.stop()
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"خطا در asyncio.run: {str(e)}")
