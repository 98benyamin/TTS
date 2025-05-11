import requests
import urllib.parse
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ReactionTypeEmoji
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from uuid import uuid4
import logging
from fastapi import FastAPI, Request, HTTPException
from pydub import AudioSegment
from PIL import Image
import io
import base64
import uvicorn

# تنظیم لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7520523575:AAG787CwUPBFctoJzjETJ6Gk-GxxnF0RaWc"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
MAX_TEXT_LENGTH = 1000
MAX_FEELING_LENGTH = 500

# تنظیمات API دستیار هوشمند
API_URL = "https://text.pollinations.ai/"
SYSTEM_PROMPT = "شما دستیار ربات متن به صدا هستید لطفا به کاربران برای ساخت متن‌های کمک کنید."
MODEL = "openai-large"

# لیست صداهای پشتیبانی‌شده
SUPPORTED_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer",
    "coral", "verse", "ballad", "ash", "sage", "amuch", "dan", "elan"
]

# فرمت‌های صوتی پشتیبانی‌شده
SUPPORTED_FORMATS = ["mp3", "wav", "ogg"]

# ایموجی واکنش انیمیشنی
REACT_EMOJI = "💊"

# ایجاد اپلیکیشن FastAPI
app = FastAPI()

# تابع برای ارسال درخواست به API دستیار هوشمند
def call_api(prompt, image=None):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "vision": True
    }

    if image:
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            payload["messages"].append({"role": "user", "content": {"image": image_base64}})
        except Exception as e:
            logger.error(f"خطا در پردازش تصویر برای API: {str(e)}")
            return "خطا در پردازش تصویر."

    try:
        logger.info(f"ارسال درخواست به API: {API_URL}, payload: {payload}")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        raw_response = response.text
        logger.info(f"پاسخ خام API: {raw_response[:500]}...")
        
        if raw_response.strip():
            return raw_response
        else:
            return "پاسخی دریافت نشد."
    except requests.RequestException as e:
        logger.error(f"خطا در ارتباط با API: {str(e)}")
        return "خطا در ارتباط با API. لطفاً دوباره امتحان کنید."
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در API: {str(e)}")
        return "خطای غیرمنتظره رخ داد. لطفاً دوباره امتحان کنید."

# تابع برای پردازش تصویر
def process_image(image_data):
    return Image.open(io.BytesIO(image_data))

def generate_audio(text, instructions, voice, output_file, audio_format="mp3"):
    logger.info(f"تولید صدا با متن: {text[:50]}..., حس: {instructions[:50]}..., صدا: {voice}, فرمت: {audio_format}")
    if voice not in SUPPORTED_VOICES:
        logger.error(f"صدا {voice} پشتیبانی نمی‌شود")
        return False
    if audio_format not in SUPPORTED_FORMATS:
        logger.error(f"فرمت {audio_format} پشتیبانی نمی‌شود")
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
            temp_file = f"temp_{uuid4()}.mp3"
            with open(temp_file, "wb") as f:
                f.write(response.content)
            logger.info(f"فایل صوتی موقت ذخیره شد: {temp_file}")
            
            # تبدیل فرمت با pydub
            audio = AudioSegment.from_file(temp_file)
            audio.export(output_file, format=audio_format)
            logger.info(f"فایل صوتی با فرمت {audio_format} ذخیره شد: {output_file}")
            
            # حذف فایل موقت
            os.remove(temp_file)
            return True
        else:
            logger.error(f"خطا در API Pollinations: کد وضعیت {response.status_code}, پاسخ: {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"خطا در ارتباط با API Pollinations: {str(e)}")
        return False
    except IOError as e:
        logger.error(f"خطا در ذخیره یا تبدیل فایل صوتی: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در تولید صدا: {str(e)}")
        return False

def create_progress_bar(percentage):
    filled = percentage // 5
    empty = 20 - filled
    bar = "█" * filled + "□" * empty
    return f"[{bar} {percentage}%]"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    try:
        # اضافه کردن واکنش انیمیشنی 💊
        if update.message:
            chat_id = update.message.chat_id
            message_id = update.message.message_id
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=REACT_EMOJI)],
                is_big=True  # انیمیشنی کردن واکنش
            )
        
        keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"], ["🔙 برگشت"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🎙 به ربات تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n"
            "من می‌توانم متن شما را با هر حس و صدایی که انتخاب کنید، به گفتار تبدیل کنم یا به‌عنوان دستیار هوشمند به سوالات شما پاسخ دهم.\n"
            "برای شروع، یکی از دکمه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
        context.user_data.clear()
        context.user_data["state"] = "main"
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("state") != "assistant":
        await update.message.reply_text(
            "لطفاً ابتدا به بخش دستیار هوشمند بروید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
        return None

    photo = update.message.photo[-1]
    try:
        logger.info(f"پردازش تصویر از کاربر {user_id}")
        photo_file = await photo.get_file()
        image_data = await photo_file.download_as_bytearray()
        image = process_image(image_data)
        user_caption = update.message.caption or "لطفاً این تصویر را توصیف کنید و متن مناسب برای تبدیل به صدا پیشنهاد دهید."
        response = call_api(user_caption, image)
        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
    except Exception as e:
        logger.error(f"خطا در پردازش تصویر برای کاربر {user_id}: {str(e)}")
        await update.message.reply_text(
            "مشکلی در پردازش تصویر پیش آمد. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
    return None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # مدیریت دکمه برگشت
    if text == "🔙 برگشت":
        current_state = context.user_data.get("state", "main")
        previous_state = context.user_data.get("previous_state", "main")
        
        if current_state == "main":
            await update.message.reply_text(
                "شما در صفحه اصلی هستید!",
                reply_markup=ReplyKeyboardMarkup([["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"], ["🔙 برگشت"]], resize_keyboard=True)
            )
            return None
        
        if previous_state == "main" or current_state == "assistant":
            return await start(update, context)
        
        if previous_state == "text":
            await update.message.reply_text(
                "لطفاً حس یا دستورالعمل‌های صدا رو وارد کنید (حداکثر 500 کاراکتر).\n"
                "مثال: Dramatic یا Gruff, fast-talking, New York accent",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            context.user_data["state"] = "manual_feeling"
            context.user_data["previous_state"] = "main"
            return None
        
        if previous_state == "voice":
            await update.message.reply_text(
                "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\n"
                "مثال: Yeah, yeah, ya got Big Apple Insurance",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            context.user_data["state"] = "text"
            context.user_data["previous_state"] = "manual_feeling"
            return None
        
        if previous_state == "select_format":
            keyboard = []
            row = []
            for voice in SUPPORTED_VOICES:
                row.append(voice.capitalize())
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append(["🔙 برگشت"])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "لطفاً یکی از صداهای زیر رو انتخاب کنید:",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "voice"
            context.user_data["previous_state"] = "text"
            return None

    if text == "🎙 تبدیل متن به صدا":
        try:
            await update.message.reply_text(
                "لطفاً حس یا دستورالعمل‌های صدا رو وارد کنید (حداکثر 500 کاراکتر).\n"
                "مثال: Dramatic یا Gruff, fast-talking, New York accent",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            context.user_data["state"] = "manual_feeling"
            context.user_data["previous_state"] = "main"
            return None
        except Exception as e:
            logger.error(f"خطا در نمایش درخواست حس برای کاربر {user_id}: {str(e)}")
            return None

    if text == "🤖 دستیار هوشمند":
        try:
            keyboard = [["🔙 برگشت"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "سلام! من ربات دستیار متن به صدا هستم. متن یا تصویر بفرستید تا به شما کمک کنم!",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "assistant"
            context.user_data["previous_state"] = "main"
            return None
        except Exception as e:
            logger.error(f"خطا در ارسال پیام برای دستیار هوشمند برای کاربر {user_id}: {str(e)}")
            return None

    if "state" in context.user_data:
        # دریافت حس دستی
        if context.user_data["state"] == "manual_feeling":
            feeling = text
            if len(feeling) > MAX_FEELING_LENGTH:
                await update.message.reply_text(
                    f"خطا: حس شما {len(feeling)} کاراکتر است. لطفاً حسی با حداکثر {MAX_FEELING_LENGTH} کاراکتر وارد کنید.",
                    reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                )
                return None
            context.user_data["feeling"] = feeling
            context.user_data["feeling_name"] = "دستی"
            context.user_data["state"] = "text"
            context.user_data["previous_state"] = "manual_feeling"
            await update.message.reply_text(
                "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\n"
                "مثال: Yeah, yeah, ya got Big Apple Insurance",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            return None
        
        # دریافت متن
        elif context.user_data["state"] == "text":
            if len(text) > MAX_TEXT_LENGTH:
                await update.message.reply_text(
                    f"خطا: متن شما {len(text)} کاراکتر است. لطفاً متنی با حداکثر {MAX_TEXT_LENGTH} کاراکتر وارد کنید.",
                    reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                )
                return None
            context.user_data["text"] = text
            context.user_data["state"] = "voice"
            context.user_data["previous_state"] = "text"
            keyboard = []
            row = []
            for voice in SUPPORTED_VOICES:
                row.append(voice.capitalize())
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append(["🔙 برگشت"])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "لطفاً یکی از صداهای زیر رو انتخاب کنید:",
                reply_markup=reply_markup
            )
            return None
        
        # دریافت صدا
        elif context.user_data["state"] == "voice":
            voice = text.lower()
            if voice not in SUPPORTED_VOICES:
                await update.message.reply_text(
                    "لطفاً یک صدای معتبر از لیست انتخاب کنید.",
                    reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                )
                return None
            context.user_data["voice"] = voice
            context.user_data["state"] = "select_format"
            context.user_data["previous_state"] = "voice"
            keyboard = [["MP3", "WAV", "OGG"], ["🔙 برگشت"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "لطفاً فرمت صوتی موردنظر را انتخاب کنید:",
                reply_markup=reply_markup
            )
            return None
        
        # انتخاب فرمت صوتی
        elif context.user_data["state"] == "select_format":
            audio_format = text.lower()
            if audio_format not in SUPPORTED_FORMATS:
                await update.message.reply_text(
                    "لطفاً یک فرمت معتبر (MP3، WAV، OGG) انتخاب کنید.",
                    reply_markup=ReplyKeyboardMarkup([["MP3", "WAV", "OGG"], ["🔙 برگشت"]], resize_keyboard=True)
                )
                return None
            text = context.user_data["text"]
            instructions = context.user_data["feeling"]
            voice = context.user_data["voice"]
            feeling_name = context.user_data["feeling_name"]
            output_file = f"output_{uuid4()}.{audio_format}"
            
            try:
                status_message = await update.message.reply_text("در حال آنالیز متن 🔍")
                await asyncio.sleep(1.5)
                await status_message.edit_text("درحال تولید صدا 🎙")
                
                progress_duration = 4
                step_duration = progress_duration / 20
                for percentage in range(0, 101, 5):
                    try:
                        await status_message.edit_text(
                            f"درحال تولید صدا 🎙\n{create_progress_bar(percentage)}"
                        )
                    except Exception as e:
                        logger.error(f"خطا در به‌روزرسانی پروگرس بار ({percentage}%) برای کاربر {user_id}: {str(e)}")
                    await asyncio.sleep(step_duration)
                
                await status_message.edit_text("تولید صدا در حال انجام است...")
                
            except Exception as e:
                logger.error(f"خطا در ارسال یا به‌روزرسانی پیام وضعیت برای کاربر {user_id}: {str(e)}")
                await update.message.reply_text(
                    "خطا در شروع تولید صدا. لطفاً دوباره امتحان کنید.",
                    reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                )
                return None
            
            success = generate_audio(text, instructions, voice, output_file, audio_format)
            
            if success:
                try:
                    with open(output_file, "rb") as audio:
                        await update.message.reply_audio(
                            audio=audio,
                            caption=f"🎙 گوینده : {voice.capitalize()}\n🎼 حس صوت : {feeling_name}",
                            title="Generated Audio",
                            reply_markup=ReplyKeyboardRemove()
                        )
                    os.remove(output_file)
                    logger.info(f"فایل صوتی ارسال و حذف شد برای کاربر {user_id}: {output_file}")
                    
                    await status_message.edit_text(
                        "✅ فایل صوتی با موفقیت ارسال شد! برای تولید دوباره، روی دکمه تبدیل متن به صدا کلیک کنید."
                    )
                    
                    # بازگشت به صفحه اصلی
                    keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"], ["🔙 برگشت"]]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(
                        "🎙 به ربات تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n"
                        "برای تولید صدای جدید یا استفاده از دستیار هوشمند، یکی از دکمه‌های زیر را انتخاب کنید:",
                        reply_markup=reply_markup
                    )
                    context.user_data.clear()
                    context.user_data["state"] = "main"
                        
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
            
            return None
        
        # دستیار هوشمند
        elif context.user_data["state"] == "assistant":
            response = call_api(text)
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            return None
    
    return None

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /cancel از کاربر: {user_id}")
    try:
        await update.message.reply_text(
            "عملیات لغو شد. با /start می‌تونید دوباره شروع کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["state"] = "main"
        keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"], ["🔙 برگشت"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🎙 به ربات تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n"
            "برای تولید صدای جدید یا استفاده از دستیار هوشمند، یکی از دکمه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /cancel برای کاربر {user_id}: {str(e)}")
    return None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "خطایی رخ داد. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )

application = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(CommandHandler("cancel", cancel))
application.add_error_handler(error_handler)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        update = Update.de_json(await request.json(), application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"خطا در پردازش درخواست webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def main():
    try:
        await application.initialize()
        logger.info("ربات مقداردهی اولیه شد")
        await application.start()
        logger.info("ربات شروع شد")
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook تنظیم شد: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی ربات: {str(e)}")
        raise
    return application

if __name__ == "__main__":
    try:
        # اجرای ربات و سرور
        application = asyncio.run(main())
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error(f"خطا در اجرای برنامه: {str(e)}")
    finally:
        try:
            if application.running:
                logger.info("توقف ربات")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(application.bot.delete_webhook())
                loop.run_until_complete(application.stop())
                loop.close()
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {str(e)}")
