import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# تنظیم لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7520523575:AAG787CwUPBFctoJzjETJ6Gk-GxxnF0RaWc"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
REACT_EMOJI = "💊"  # ایموجی واکنش برای پیام /start

# ... (بقیه تنظیمات و ثابت‌ها مانند کد اصلی بدون تغییر)

def generate_audio(text, instructions, voice, output_file, audio_format="mp3"):
    logger.info(f"تولید صدا با متن: {text[:50]}..., حس: {instructions[:50]}..., صدا: {voice}, فرمت: {audio_format}")
    if voice not in SUPPORTED_VOICES:
        logger.error(f"صدا {voice} پشتیبانی نمی‌شود")
        return False
    if audio_format not in SUPPORTED_FORMATS:
        logger.error(f"فرمت {audio_format} پشتیبانی نمی‌شود")
        return False
    
    # پرامپ خالی برای حس، فقط از دستورالعمل‌های کاربر استفاده می‌شود
    prompt = f"{instructions}\n\nRepeat the text exactly as provided: {text}"
    
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    try:
        keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"], ["🔙 برگشت"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        # ارسال پیام خوش‌آمدگویی
        message = await update.message.reply_text(
            "🎙 به ربات تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n"
            "من می‌توانم متن شما را با هر حس و صدایی که انتخاب کنید، به گفتار تبدیل کنم یا به‌عنوان دستیار هوشمند به سوالات شما پاسخ دهم.\n"
            "برای شروع، یکی از دکمه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
        # اضافه کردن واکنش به پیام
        await context.bot.set_message_reaction(
            chat_id=update.message.chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji=REACT_EMOJI)],
            is_big=False
        )
        context.user_data.clear()
        context.user_data["state"] = "main"
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

# ... (بقیه توابع و کد اصلی بدون تغییر)
