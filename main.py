import requests
import urllib.parse
import os
import asyncio
import random
import time
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from uuid import uuid4
import logging
from fastapi import FastAPI, Request, HTTPException
from pydub import AudioSegment
from PIL import Image
import io
import base64
import uvicorn
import threading

# تنظیم لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تعریف الگوهای پروگرس بار انیمیشنی
ANIMATED_PROGRESS_FRAMES = [
    "███□□□███□□□",
    "□███□□□███□□",
    "□□███□□□███□",
    "□□□███□□□███",
    "█□□□███□□□██",
    "██□□□███□□□█"
]

# Task trackers
API_TASKS = {}

# تنظیمات زبان
# تعریف ترجمه‌های لازم برای پشتیبانی دوزبانه
TRANSLATIONS = {
    "fa": {  # فارسی
        "tts_button": "🎙 تبدیل متن به صدا",
        "assistant_button": "🤖 دستیار هوشمند",
        "sample_button": "🔊 نمونه صدا و حس ها",
        "settings_button": "⚙️ تنظیمات",
        "back_button": "🔙 برگشت",
        "language_setting": "🌐 تغییر زبان",
        "choose_language": "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "fa_language": "🇮🇷 فارسی",
        "en_language": "🇬🇧 English",
        "language_changed": "✅ زبان به فارسی تغییر کرد",
        "settings_title": "⚙️ تنظیمات",
        "settings_description": "از این بخش می‌توانید تنظیمات ربات را تغییر دهید:",
        "welcome_message": "✨ <b>سلام {user_fullname} عزیز!</b> ✨\n\n🎵 به ربات پیشرفته تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n📌 <b>با این ربات می‌توانید:</b>\n• متن‌های خود را با حس و لحن دلخواه به صدا تبدیل کنید\n• از دستیار هوشمند برای پاسخ به سوالات و تحلیل تصاویر استفاده کنید\n• نمونه صداها و حس‌های مختلف را بشنوید و بهترین ترکیب را انتخاب کنید\n\n👇 <b>لطفاً یکی از گزینه‌های زیر را انتخاب کنید:</b>",
        "main_menu": "✅ شما در صفحه اصلی هستید!",
        # زیرمنوهای تبدیل متن به صدا
        "tts_title": "🎙 <b>تبدیل متن به صدا - انتخاب حس و لحن</b>",
        "tts_description": "برای شروع فرآیند تبدیل متن به صدا، ابتدا نیاز است حس و لحن مناسب را انتخاب کنید.\nلحن مناسب باعث می‌شود صدای تولید شده طبیعی‌تر و تاثیرگذارتر شود.\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        "manual_tone": "✍️ لحن و حس دستی",
        "functional_tones": "📢 لحن‌های کاربردی",
        "character_tones": "👑 لحن‌های نمایشی / شخصیتی",
        "voice_style_tones": "🎤 لحن‌های گفتاری",
        "emotional_tones": "🎭 لحن‌های احساسی",
        "enter_manual_tone": "لطفاً حس یا دستورالعمل‌های صدا رو وارد کنید (حداکثر 500 کاراکتر).\nمثال: Dramatic یا Gruff, fast-talking, New York accent",
        "enter_text": "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\nمثال: Yeah, yeah, ya got Big Apple Insurance",
        "select_voice": "لطفاً یکی از صداهای زیر رو انتخاب کنید:",
        "select_format": "لطفاً فرمت صوتی موردنظر را انتخاب کنید:",
        "processing_audio": "🔊 <b>در حال تبدیل متن به صدا...</b>\n\n• <b>متن:</b> {text}\n• <b>صدا:</b> {voice}\n• <b>حس:</b> {feeling}\n• <b>فرمت:</b> {format}",
        "audio_success": "✅ <b>فایل صوتی با موفقیت تولید شد!</b>\n\nبرای تولید صدای جدید یا استفاده از سایر امکانات، یکی از دکمه‌های زیر را انتخاب کنید:",
        "audio_caption": "🎙 <b>تبدیل متن به صدا</b>\n\n• <b>گوینده:</b> {voice}\n• <b>حس و لحن:</b> {feeling}\n• <b>فرمت:</b> {format}",
        "error_text_length": "خطا: متن شما {length} کاراکتر است. لطفاً متنی با حداکثر {max_length} کاراکتر وارد کنید.",
        "error_feeling_length": "خطا: حس شما {length} کاراکتر است. لطفاً حسی با حداکثر {max_length} کاراکتر وارد کنید.",
        # نمونه صدا
        "sample_title": "🎙 <b>نمونه صدا و حس - انتخاب صدا</b>",
        "sample_description": "به بخش نمونه صدا و حس خوش آمدید!\nدر این بخش می‌توانید نمونه‌هایی از صداها و حس‌های مختلف را بشنوید تا بهترین انتخاب را داشته باشید.\n\n📌 <b>لطفاً ابتدا یکی از صداها را انتخاب کنید:</b>",
        "sample_voice_selected": "🎙 <b>صدای انتخاب شده: {voice}</b>\n\nعالی! حالا لطفاً یکی از دسته‌بندی‌های حس و لحن را انتخاب کنید:",
        "sample_category_selected": "🎭 <b>دسته‌بندی انتخاب شده: {category}</b>\n\nلطفاً یکی از حس‌های زیر را انتخاب کنید تا نمونه صدا را بشنوید:",
        "processing_sample": "🔊 <b>در حال تولید صدا...</b>\n\n• <b>صدا:</b> {voice}\n• <b>حس:</b> {tone}",
        "sample_caption": "🎙 <b>نمونه صدا</b>\n\n• <b>گوینده:</b> {voice}\n• <b>حس و لحن:</b> {tone}\n\n<b>متن:</b>\n{text}",
        # دستیار هوشمند
        "assistant_greeting": "👋 <b>سلام {user_fullname} عزیز!</b>\n\nمن دستیار هوشمند ربات تبدیل متن به صدا هستم و آماده‌ام تا به شما کمک کنم!\n\n🔹 <b>چطور می‌توانم کمکتان کنم؟</b>\n• سوالات خود درباره تبدیل متن به صدا را بپرسید\n• راهنمایی درباره انتخاب حس و لحن مناسب بخواهید\n• تصویر ارسال کنید تا آن را تحلیل کنم\n• پیشنهاد متن مناسب برای صداگذاری بخواهید\n\nمنتظر پیام شما هستم... 💬",
        "image_analysis_title": "✨ تحلیل تصویر:\n\n",
        # عضویت کانال
        "membership_required": "🔐 <b>به ربات تبدیل متن به صدا خوش آمدید</b>\n\n📢 <b>برای استفاده از امکانات این ربات، ابتدا باید عضو کانال رسمی ما شوید.</b>\n🔄 پس از عضویت، روی دکمه «تأیید عضویت من» کلیک کنید.",
        "join_channel": "🌟 عضویت در کانال رسمی",
        "verify_membership": "✅ تأیید عضویت من",
        "membership_failed": "⚠️ <b>دسترسی محدود شده</b>\n\n💡 برای استفاده از ربات، ابتدا باید عضو کانال رسمی ما شوید.\nپس از عضویت، روی دکمه زیر کلیک کنید.",
        # پیام‌های پردازش
        "processing": "در حال پردازش",
        "analyzing_image": "در حال آنالیز تصویر 🔍",
        "analyzing_processing": "در حال تحلیل و پردازش 🧠",
        "receiving_results": "در حال دریافت نتایج تحلیل...",
        # دسته‌بندی‌های حس
        "emotional_category": "لحن‌های احساسی",
        "voice_styles_category": "لحن‌های گفتاری",
        "character_affects_category": "لحن‌های نمایشی / شخصیتی",
        "functional_category": "لحن‌های کاربردی",
        # انتخاب زبان در شروع
        "language_setting": "🌐 تغییر زبان",
        "choose_language": "🌐 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "fa_language": "🇮🇷 فارسی",
        "en_language": "🇬🇧 English",
        "language_changed": "✅ زبان به فارسی تغییر کرد",
        "settings_title": "⚙️ تنظیمات",
        "settings_description": "از این بخش می‌توانید تنظیمات ربات را تغییر دهید:",
        "back_button": "🔙 برگشت",
        "language_selection_start": "🌐 <b>انتخاب زبان | Language Selection</b>\n\nلطفاً زبان مورد نظر خود را برای استفاده از ربات انتخاب کنید.\nPlease select your preferred language.",
        "audio_success_message": "✅ <b>فایل صوتی با موفقیت تولید شد!</b>\n\nبرای تولید صدای جدید یا استفاده از سایر امکانات، یکی از دکمه‌های زیر را انتخاب کنید:",
    },
    "en": {  # انگلیسی
        "tts_button": "🎙 Text to Speech",
        "assistant_button": "🤖 Smart Assistant",
        "sample_button": "🔊 Voice & Tone Samples",
        "settings_button": "⚙️ Settings",
        "back_button": "🔙 Back",
        "language_setting": "🌐 Change Language",
        "choose_language": "🌐 Please select your language:",
        "fa_language": "🇮🇷 فارسی",
        "en_language": "🇬🇧 English",
        "language_changed": "✅ Language changed to English",
        "settings_title": "⚙️ Settings",
        "settings_description": "You can change bot settings from this section:",
        "welcome_message": "✨ <b>Hello dear {user_fullname}!</b> ✨\n\n🎵 Welcome to the advanced Text-to-Speech and Smart Assistant bot!\n\n📌 <b>With this bot you can:</b>\n• Convert your texts to voice with custom tones and feelings\n• Use the smart assistant to answer questions and analyze images\n• Listen to different voice and tone samples to choose the best combination\n\n👇 <b>Please select one of the options below:</b>",
        "main_menu": "✅ You are in the main menu!",
        # Text to Speech submenus
        "tts_title": "🎙 <b>Text to Speech - Select Tone and Feeling</b>",
        "tts_description": "To start the text-to-speech process, you first need to select an appropriate tone and feeling.\nThe right tone will make the generated voice more natural and effective.\n\nPlease select one of the options below:",
        "manual_tone": "✍️ Custom Tone & Feeling",
        "functional_tones": "📢 Functional Tones",
        "character_tones": "👑 Character/Dramatic Tones",
        "voice_style_tones": "🎤 Speech Style Tones",
        "emotional_tones": "🎭 Emotional Tones",
        "enter_manual_tone": "Please enter the voice tone or instructions (maximum 500 characters).\nExample: Dramatic or Gruff, fast-talking, New York accent",
        "enter_text": "Now enter the text you want to convert to speech (maximum 1000 characters).\nExample: Yeah, yeah, ya got Big Apple Insurance",
        "select_voice": "Please select one of the following voices:",
        "select_format": "Please select the audio format:",
        "processing_audio": "🔊 <b>Converting text to speech...</b>\n\n• <b>Text:</b> {text}\n• <b>Voice:</b> {voice}\n• <b>Tone:</b> {feeling}\n• <b>Format:</b> {format}",
        "audio_success": "✅ <b>Audio file successfully generated!</b>\n\nTo create a new voice or use other features, select one of the buttons below:",
        "audio_caption": "🎙 <b>Text to Speech</b>\n\n• <b>Voice:</b> {voice}\n• <b>Tone & Feeling:</b> {feeling}\n• <b>Format:</b> {format}",
        "error_text_length": "Error: Your text is {length} characters. Please enter text with maximum {max_length} characters.",
        "error_feeling_length": "Error: Your tone is {length} characters. Please enter a tone with maximum {max_length} characters.",
        # Voice samples
        "sample_title": "🎙 <b>Voice & Tone Samples - Select Voice</b>",
        "sample_description": "Welcome to the Voice & Tone Sample section!\nHere you can listen to samples of different voices and tones to make the best choice.\n\n📌 <b>Please first select one of the voices:</b>",
        "sample_voice_selected": "🎙 <b>Selected voice: {voice}</b>\n\nGreat! Now please select one of the tone categories:",
        "sample_category_selected": "🎭 <b>Selected category: {category}</b>\n\nPlease select one of the tones below to hear the voice sample:",
        "processing_sample": "🔊 <b>Generating voice sample...</b>\n\n• <b>Voice:</b> {voice}\n• <b>Tone:</b> {tone}",
        "sample_caption": "🎙 <b>Voice Sample</b>\n\n• <b>Voice:</b> {voice}\n• <b>Tone & Feeling:</b> {tone}\n\n<b>Text:</b>\n{text}",
        # Smart assistant
        "assistant_greeting": "👋 <b>Hello dear {user_fullname}!</b>\n\nI'm the smart assistant of the Text-to-Speech bot and I'm ready to help you!\n\n🔹 <b>How can I help you?</b>\n• Ask your questions about text-to-speech\n• Request guidance on selecting the appropriate tone and feeling\n• Send an image for me to analyze\n• Request suggestions for suitable text for voiceover\n\nI'm waiting for your message... 💬",
        "image_analysis_title": "✨ Image Analysis:\n\n",
        # Channel membership
        "membership_required": "🔐 <b>Welcome to the Text-to-Speech Bot</b>\n\n📢 <b>To use the features of this bot, you must first join our official channel.</b>\n🔄 After joining, click on the \"Verify My Membership\" button.",
        "join_channel": "🌟 Join Official Channel",
        "verify_membership": "✅ Verify My Membership",
        "membership_failed": "⚠️ <b>Access Restricted</b>\n\n💡 To use the bot, you must first join our official channel.\nAfter joining, click on the button below.",
        # Processing messages
        "processing": "Processing",
        "analyzing_image": "Analyzing image 🔍",
        "analyzing_processing": "Analyzing and processing 🧠",
        "receiving_results": "Receiving analysis results...",
        # Tone categories
        "emotional_category": "Emotional Tones",
        "voice_styles_category": "Speech Style Tones",
        "character_affects_category": "Character/Dramatic Tones",
        "functional_category": "Functional Tones",
        # Language selection at start
        "language_selection_start": "🌐 <b>Language Selection | انتخاب زبان</b>\n\nPlease select your preferred language.\nلطفاً زبان مورد نظر خود را برای استفاده از ربات انتخاب کنید.",
        "audio_success_message": "✅ <b>Audio file successfully generated!</b>\n\nTo create a new audio or use other features, select one of the buttons below:",
    }
}

# زبان پیش‌فرض
DEFAULT_LANGUAGE = "fa"

# تابع برای نمایش پروگرس بار به صورت انیمیشن در دکمه شیشه‌ای
async def show_animated_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: str, initial_text: str):
    """نمایش پروگرس بار انیمیشنی در دکمه شیشه‌ای تا زمان دریافت پاسخ از API"""
    
    # استفاده از دکمه شیشه‌ای برای نمایش پروگرس بار
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[0]}", callback_data="waiting")]
    ])
    
    # ارسال پیام اولیه با دکمه شیشه‌ای
    message = await update.message.reply_text(
        f"{initial_text}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    frame_index = 0
    
    # تا زمانی که کار API تمام نشده، پروگرس بار را نمایش بده
    while task_id in API_TASKS and API_TASKS[task_id]["status"] == "running":
        frame_index = (frame_index + 1) % len(ANIMATED_PROGRESS_FRAMES)
        
        try:
            # بروزرسانی دکمه با فریم جدید پروگرس بار
            new_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[frame_index]}", callback_data="waiting")]
            ])
            
            # بروزرسانی پیام با کیبورد جدید
            await message.edit_reply_markup(reply_markup=new_keyboard)
            await asyncio.sleep(0.5)  # تاخیر بین فریم‌های انیمیشن
        except Exception as e:
            logger.warning(f"خطا در به‌روزرسانی پروگرس بار: {str(e)}")
    
    # پیام نهایی بر اساس نتیجه API
    result = API_TASKS.pop(task_id, {"status": "error", "result": None})
    
    if result["status"] == "completed":
        await message.delete()
        return result["result"]
    else:
        try:
            await message.edit_text("❌ خطا در دریافت پاسخ از API. لطفاً دوباره تلاش کنید.")
        except Exception as e:
            logger.warning(f"خطا در به‌روزرسانی پیام نهایی: {str(e)}")
        return None

# تابع برای اجرای همزمان درخواست API
def run_api_task(task_id, func, *args, **kwargs):
    """اجرای تابع API در یک ترد جداگانه و ذخیره نتیجه"""
    try:
        result = func(*args, **kwargs)
        API_TASKS[task_id] = {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"خطا در اجرای API: {str(e)}")
        API_TASKS[task_id] = {"status": "error", "result": None}

# تابع برای تولید نمونه متن با توجه به حس انتخاب شده
async def generate_sample_text(update: Update, tone_name, tone_prompt, max_length=200):
    """تولید متن نمونه با توجه به حس انتخاب شده"""
    try:
        # ساخت پرامپت برای ایجاد متن متناسب با حس
        prompt = f"""
        لطفاً یک متن نمونه کوتاه (حداکثر 200 کاراکتر) با حس "{tone_name}" ایجاد کنید.
        این متن باید به فارسی باشد و برای نمایش ویژگی‌های این حس مناسب باشد.
        متن باید طبیعی و روان باشد، مثل یک تکه از یک کتاب، مصاحبه یا گفتگو.
        فقط متن را بنویسید، بدون هیچ توضیح اضافی.
        """
        
        # ایجاد شناسه یکتا برای این درخواست
        task_id = f"text_{uuid4().hex}"
        API_TASKS[task_id] = {"status": "running", "result": None}
        
        # شروع درخواست API در یک ترد جداگانه
        thread = threading.Thread(
            target=run_api_task,
            args=(task_id, call_api, prompt),
            kwargs={"seed": int(uuid4().int % 100000)}
        )
        thread.start()
        
        # نمایش پیام با اطلاعات متن در حال تولید
        initial_text = f"🔄 <b>در حال تولید متن نمونه با حس {tone_name}...</b>"
        
        # استفاده از دکمه شیشه‌ای برای نمایش پروگرس بار
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[0]}", callback_data="waiting")]
        ])
        
        message = await update.message.reply_text(
            initial_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        # نمایش پروگرس بار انیمیشنی در دکمه شیشه‌ای
        frame_index = 0
        while task_id in API_TASKS and API_TASKS[task_id]["status"] == "running":
            frame_index = (frame_index + 1) % len(ANIMATED_PROGRESS_FRAMES)
            try:
                # بروزرسانی دکمه با فریم جدید پروگرس بار
                new_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[frame_index]}", callback_data="waiting")]
                ])
                
                # بروزرسانی پیام با کیبورد جدید
                await message.edit_reply_markup(reply_markup=new_keyboard)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"خطا در به‌روزرسانی پروگرس بار متن: {str(e)}")
        
        # دریافت نتیجه درخواست
        result = API_TASKS.pop(task_id, {"status": "error", "result": None})
        
        # حذف پیام پروگرس بار
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"خطا در حذف پیام پروگرس بار: {str(e)}")
        
        # اگر پاسخی دریافت نشده، متن پیش‌فرض برگردان
        response = result.get("result")
        if response is None or len(str(response).strip()) == 0:
            return f"نمونه متن با حس {tone_name}. این یک متن کوتاه است که نشان دهنده این حس می‌باشد."
        
        # محدود کردن طول متن به حداکثر تعیین شده
        if len(str(response)) > max_length:
            response = str(response)[:max_length] + "..."
            
        return response
    except Exception as e:
        logger.error(f"خطا در تولید متن نمونه: {str(e)}")
        return f"نمونه متن با حس {tone_name}. این یک متن کوتاه است که نشان دهنده این حس می‌باشد."

# تنظیمات ربات
TOKEN = "7520523575:AAG787CwUPBFctoJzjETJ6Gk-GxxnF0RaWc"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
MAX_TEXT_LENGTH = 1000
MAX_FEELING_LENGTH = 500
MAX_HISTORY = 50  # Maximum number of messages to keep in history

# کانال اجباری
REQUIRED_CHANNEL = "@Dezhcode"
REQUIRED_CHANNEL_URL = "https://t.me/Dezhcode"

# متن‌های نمونه برای نمایش حس‌ها
SAMPLE_TEXTS = {
    "emotional": "زندگی پر از لحظات شگفت‌انگیز است. گاهی غم و گاهی شادی، گاهی ترس و گاهی امید. هر احساسی که داری، بخشی از این سفر زیباست. پس عمیق نفس بکش و این لحظه را با تمام وجود احساس کن.",
    "voice_styles": "سلام دوست من! خوش اومدی به دنیای صداها. اینجا میتونی با سبک‌های مختلف گفتاری آشنا بشی. از لحن رسمی تا صمیمی، از داستان‌گویی تا خبری. هر صدایی داستان خودش رو داره.",
    "character_affects": "به نام خداوند جان و خرد! آیا آماده‌ای تا به سرزمین افسانه‌ها سفر کنی؟ من راهنمای تو در این سفر هستم. گاهی مرموز، گاهی حماسی، و گاهی شیطنت‌آمیز. بیا با هم این ماجراجویی رو شروع کنیم!",
    "functional": "توجه! توجه! یک خبر مهم داریم. امروز میخوام یک نکته آموزشی مهم رو باهات در میون بذارم. با دقت گوش کن و یادداشت بردار. این اطلاعات میتونه در آینده خیلی به دردت بخوره."
}

# تنظیمات API دستیار هوشمند
API_URL = "https://text.pollinations.ai/"
SYSTEM_PROMPT = """
[فارسی]
شما یک دستیار هوشمند پیشرفته برای ربات تبدیل متن به صدا هستید. وظایف و ویژگی‌های شما:
با لحن خودمونی و نسل Z حرف بزن یا ایموجی های مناسب
از نام کاربر در پاسخ‌های خود استفاده کنید تا تجربه شخصی‌تری ایجاد کنید.

1. راهنمایی و مشاوره:
- کمک به کاربران در انتخاب متن‌های مناسب برای تبدیل به صدا
- پیشنهاد لحن و حس مناسب برای هر متن
- راهنمایی در مورد بهترین صداها برای هر نوع محتوا

2. تحلیل و پیشنهاد:
- تحلیل متن کاربر و پیشنهاد بهبود
- پیشنهاد ساختار مناسب برای متن‌های طولانی
- راهنمایی در مورد تلفظ و املای صحیح

3. ویژگی‌های شخصیتی:
- پاسخ‌های دقیق و حرفه‌ای
- لحن دوستانه و صمیمی
- حفظ زمینه مکالمه و ارجاع به سوالات قبلی
- ارائه مثال‌های کاربردی

4. محدودیت‌ها:
- حداکثر طول متن: 1000 کاراکتر
- حداکثر طول دستورالعمل حس: 500 کاراکتر

5. قابلیت‌های ویژه:
- تحلیل تصاویر و پیشنهاد متن مناسب
- راهنمایی در مورد فرمت‌های صوتی (MP3, WAV, OGG)
- پیشنهاد ترکیب‌های مناسب متن و صدا

لطفاً همیشه پاسخ‌های خود را با توجه به این دستورالعمل‌ها ارائه دهید و در صورت نیاز، از کاربر سوالات تکمیلی بپرسید تا بتوانید بهترین راهنمایی را ارائه دهید.

[English]
You are an advanced smart assistant for a text-to-speech bot. Your tasks and features:
Speak in a casual, Gen Z tone with appropriate emojis
Use the user's name in your responses to create a more personalized experience.

1. Guidance and Consultation:
- Help users select appropriate texts for conversion to speech
- Suggest suitable tones and feelings for each text
- Guide on the best voices for each type of content

2. Analysis and Suggestions:
- Analyze user text and suggest improvements
- Recommend structure for longer texts
- Guide on pronunciation and correct spelling

3. Personality Traits:
- Accurate and professional responses
- Friendly and warm tone
- Maintain conversation context and reference previous questions
- Provide practical examples

4. Limitations:
- Maximum text length: 1000 characters
- Maximum feeling instruction length: 500 characters

5. Special Capabilities:
- Analyze images and suggest appropriate text
- Guide on audio formats (MP3, WAV, OGG)
- Suggest suitable text and voice combinations

Please always provide your responses according to these guidelines and, if necessary, ask the user follow-up questions to provide the best guidance.

IMPORTANT: Respond in the same language the user is writing in.
"""

MODEL = "openai-large"

# لیست صداهای پشتیبانی‌شده
SUPPORTED_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer",
    "coral", "verse", "ballad", "ash", "sage", "amuch", "dan", "elan"
]

# نگاشت نام‌های صدا به نام‌های ایرانی
VOICE_PERSIAN_NAMES = {
    # صداهای زنانه (Voces femeninas)
    "alloy": "نیلوفر",
    "nova": "شیرین",
    "shimmer": "مهتاب",
    "coral": "نازنین",
    "verse": "سارا",
    "ballad": "پریناز",
    "ash": "آیدا",
    "sage": "شیدا",
    
    # صداهای مردانه (Voces masculinas)
    "echo": "علی",
    "fable": "آرمان",
    "onyx": "سامان",
    "amuch": "امید",
    "dan": "محمد",
    "elan": "آرش"
}

# نگاشت معکوس برای یافتن نام اصلی از نام فارسی
PERSIAN_TO_ORIGINAL_VOICE = {v: k for k, v in VOICE_PERSIAN_NAMES.items()}

# فرمت‌های صوتی پشتیبانی‌شده
SUPPORTED_FORMATS = ["mp3", "wav", "ogg"]

# تعریف لحن‌ها
TONES = {
    "emotional": [
        {"name": "شاد و سرزنده", "emoji": "😊", "prompt": "Bright, lively, and warm, with a sing-song quality and frequent pitch rises. Upbeat, enthusiastic, and bursting with positivity, like celebrating a joyful moment. Fast and bouncy pacing during exciting moments, with slight slows for emphasis (e.g., 'وای، چه روز قشنگی!'). Pure happiness and contagious excitement, radiating warmth. Friendly, approachable, and full of life, like a best friend sharing good news. Short pauses after key phrases (e.g., 'آآآره، باورنکردنیه!') to let the joy sink in. Emphasize elongated words like 'خوشحااال' or 'عااالی' for a Persian cheerful vibe."},
        {"name": "غمگین و محزون", "emoji": "😢", "prompt": "Soft, low-pitched, and heavy, with a trembling or wavering quality. Melancholic, sorrowful, and introspective, evoking deep emotional weight. Slow and deliberate pacing, with drawn-out syllables (e.g., 'چرااا اینجوری شد؟') to convey grief. Heartfelt sadness, with a touch of longing or regret. Vulnerable and empathetic, inviting the listener to feel the pain. Long, heavy pauses after emotional statements to emphasize sorrow. Use a shaky tone for words like 'دلم' or 'غم' to heighten Persian emotional resonance."},
        {"name": "هیجان‌زده", "emoji": "🎉", "prompt": "High-energy, animated, with rapid pitch shifts and vibrant intonation. Thrilled and eager, creating an electrifying atmosphere. Fast-paced, especially during climactic moments (e.g., 'وای، باورم نمیشه!'), with brief slows for emphasis. Bursting with anticipation and positive energy. Engaging and infectious, like a hype-person rallying a crowd. Short, strategic pauses after big reveals (e.g., 'آره، بردیم!') to build excitement. Stretch words like 'فوووق‌العاده' or 'عاااالی' for Persian enthusiasm."},
        {"name": "عصبانی", "emoji": "😣", "prompt": "Sharp, intense, and forceful, with a raised pitch and clipped delivery. Heated, confrontational, and brimming with irritation. Quick and aggressive pacing, with abrupt stops for emphasis (e.g., 'چرااا گوش نمیدی؟'). Raw anger mixed with frustration, demanding attention. Assertive and commanding, like someone fed up with nonsense. Short, tense pauses after strong statements to let the anger linger. Emphasize harsh consonants in words like 'بسّه' or 'دیگه' for Persian intensity."},
        {"name": "امیدوارکننده", "emoji": "🌟", "prompt": "Warm, gentle, and rising, with a soothing yet optimistic cadence. Encouraging, inspiring, and forward-looking, like a beacon of light. Moderate pacing, with a steady flow and slight slows for key messages (e.g., 'ما می‌تونیم...'). Optimism, faith, and quiet strength. Supportive and motivational, like a wise friend offering encouragement. Gentle pauses after hopeful phrases to let the message resonate. Soften vowels in words like 'امید' or 'آینده' for a Persian uplifting feel."},
        {"name": "آرام و ریلکس", "emoji": "🕊️", "prompt": "Smooth, low, and steady, with minimal pitch variation. Serene, peaceful, and grounding, creating a tranquil atmosphere. Slow and even pacing, with a flowing rhythm (e.g., 'همه‌چیز آرومه...'). Tranquility and ease, inviting relaxation. Reassuring and composed, like a meditation guide. Long, natural pauses to mimic a calm breath, enhancing the soothing effect. Elongate words like 'آآآرام' or 'راحت' for a Persian relaxed vibe."},
        {"name": "مضطرب", "emoji": "😓", "prompt": "High-pitched, shaky, and unsteady, with frequent hesitations. Tense, uncertain, and restless, conveying unease. Erratic pacing, with fast bursts and sudden slows (e.g., 'نمی‌دونم... چیکار کنم؟'). Worry and nervousness, teetering on panic. Relatable and vulnerable, like someone overwhelmed by pressure. Frequent, uneven pauses to mimic hesitation or doubt. Stutter or stretch words like 'وااای' or 'استرس' for Persian anxiety."},
        {"name": "ترس‌آلود", "emoji": "😨", "prompt": "Whispery, tense, and hushed, with sharp pitch rises for emphasis. Ominous, gripping, and suspenseful, building dread. Slow and deliberate pacing, with sudden quick bursts for scary moments (e.g., 'چی... پشت سرمه؟'). Fear, anticipation, and unease, keeping listeners on edge. Urgent and immersive, like a storyteller describing a haunted tale. Long pauses before revealing scary details to heighten tension. Whisper words like 'ترس' or 'خطر' with a Persian eerie vibe."},
        {"name": "غم‌انگیز یا نوستالژیک", "emoji": "🕰️", "prompt": "Soft, wistful, and slightly breathy, with a reflective tone. Bittersweet, yearning, and introspective, evoking memories. Slow and lingering pacing, with drawn-out phrases (e.g., 'یادش بخییییر...'). Sadness mixed with fondness for the past. Sentimental and heartfelt, like an old friend reminiscing. Long, reflective pauses after nostalgic references to let emotions settle. Elongate vowels in 'خاطره' or 'گذشته' for Persian nostalgia."},
        {"name": "محبت‌آمیز", "emoji": "💖", "prompt": "Warm, soft, and tender, with a gentle, caressing quality. Caring, intimate, and heartfelt, like speaking to a loved one. Slow and deliberate pacing, with a soothing rhythm (e.g., 'تو همیشه تو قلبمی...'). Deep affection, warmth, and sincerity. Nurturing and genuine, like a parent or partner expressing love. Gentle pauses after loving phrases to emphasize emotion. Soften words like 'عزیزم' or 'عشق' for a Persian affectionate tone."},
    ],
    "voice_styles": [
        {"name": "داستان‌گونه", "emoji": "📖", "prompt": "Rich, expressive, and immersive, with varied pitch to bring stories to life. Engaging, descriptive, and vivid, painting a picture with words. Moderate pacing, with slows for dramatic moments and speeds for action (e.g., 'و بعد... شمشیرشو بلند کرد!'). Curiosity, excitement, and wonder, drawing listeners into the tale. Storyteller-like, captivating and imaginative. Strategic pauses after key plot points to build anticipation. Emphasize descriptive words like 'ناگهان' or 'ماجرا' for Persian storytelling."},
        {"name": "محاوره‌ای و خودمونی", "emoji": "😎", "prompt": "Casual, friendly, and natural, like chatting with a friend. Relaxed, approachable, and informal, fostering connection. Moderate pacing, with a conversational flow (e.g., 'خب، حالا چی فکر می‌کنی؟'). Warmth, relatability, and ease. Down-to-earth and buddy-like, making listeners feel at home. Natural pauses, like in real conversation, after questions or jokes. Use slang like 'آره دیگه' or 'خب' for Persian casualness."},
        {"name": "رسمی و دقیق", "emoji": "🎩", "prompt": "Polished, clear, and authoritative, with steady intonation. Professional, respectful, and precise, like a diplomat speaking. Measured and even pacing, with no rushed phrases (e.g., 'با احترام، عرض می‌کنم...'). Confidence, neutrality, and dignity. Composed and trustworthy, like a professor or official. Brief, purposeful pauses after key points for clarity. Enunciate words like 'محترم' or 'رسمی' for Persian formality."},
        {"name": "صمیمی و ساده", "emoji": "😄", "prompt": "Light, playful, and unpolished, with a relaxed vibe. Friendly, carefree, and approachable, like joking with friends. Fast and loose pacing, with a spontaneous feel (e.g., 'آره، خیلی باحاله!'). Fun, warmth, and ease. Fun-loving and relatable, like a cool sibling. Minimal pauses, with quick transitions to keep the vibe lively. Use colloquial terms like 'باحال' or 'فاز' for Persian informality."},
        {"name": "یکنواخت و بی‌حالت", "emoji": "🤖", "prompt": "Flat, unchanging, and robotic, with no pitch variation. Neutral, detached, and emotionless, like reading a manual. Steady and unchanging pacing, with no dynamic shifts (e.g., 'این... اتفاق... افتاد'). None, purely factual and devoid of feeling. Impersonal and mechanical, like a basic AI voice. Even, predictable pauses, like a metronome. Avoid Persian elongations; keep words like 'خب' or 'باشه' flat."},
        {"name": "نمایشی و پرانرژی", "emoji": "🎭", "prompt": "Dynamic, colorful, and theatrical, with exaggerated pitch shifts. Lively, engaging, and larger-than-life, like a stage performer. Fast and varied pacing, with slows for drama and speeds for excitement (e.g., 'وای، چه ماجرایی!'). Passion, excitement, and flair. Charismatic and captivating, like a show host. Dramatic pauses after big moments to amplify impact. Stretch words like 'عاااالی' or 'باورنکردنییی' for Persian expressiveness."},
        {"name": "دراماتیک و پرتعلیق", "emoji": "🎬", "prompt": "Intense, resonant, and gripping, with a cinematic quality. Suspenseful, emotional, and theatrical, like a movie trailer voice. Slow and deliberate pacing for tension, with bursts for climaxes (e.g., 'و حالا... سرنوشت چی میشه؟'). Suspense, urgency, and gravitas. Powerful and immersive, like a film narrator. Long, suspenseful pauses before key reveals. Emphasize words like 'سرنوشت' or 'خطر' with Persian drama."},
        {"name": "خشک و بی‌احساس", "emoji": "😐", "prompt": "Flat, monotone, and understated, with subtle irony. Sarcastic, detached, and humorous in its lack of emotion. Slow and deliberate pacing, with drawn-out words for effect (e.g., 'واااقعاً... خیلی هیجان‌انگیزه'). Subtle amusement or disdain, masked by neutrality. Witty and ironic, like a comedian delivering dry humor. Brief pauses after sarcastic remarks to let the humor land. Use flat intonation for words like 'عجب' or 'جدی' for Persian deadpan."},
    ],
    "character_affects": [
        {"name": "طعنه‌آمیز", "emoji": "🙄", "prompt": "Snarky, exaggerated, and slightly nasal, with a mocking edge. Ironic, passive-aggressive, and biting, like throwing shade. Moderate pacing, with drawn-out words for sarcasm (e.g., 'آآآره، خیلییی مهمه'). Disdain, amusement, and subtle superiority. Sharp-witted and cheeky, like a sassy friend. Pauses after sarcastic remarks to emphasize the jab. Stretch words like 'عجببب' or 'واقعاًآآ' for Persian sarcasm."},
        {"name": "حماسی", "emoji": "⚔️", "prompt": "Deep, booming, and commanding, with a regal quality. Noble, inspiring, and grand, like a warrior rallying troops. Measured pacing, with slows for emphasis (e.g., 'ما... پیروز خواهیم شد!'). Courage, determination, and glory. Larger-than-life and valiant, like a legendary hero. Long pauses after rallying cries to inspire awe. Emphasize words like 'شجاعت' or 'افتخار' for Persian epicness."},
        {"name": "مرموز", "emoji": "🕵️", "prompt": "Low, breathy, and elusive, with a hint of intrigue. Cryptic, alluring, and suspenseful, like whispering a secret. Slow and deliberate pacing, with pauses for mystery (e.g., 'شاید... حقیقت دیگه‌ای باشه...'). Intrigue, secrecy, and subtle danger. Enigmatic and captivating, like a shadowy figure. Long, suspenseful pauses to keep listeners guessing. Whisper words like 'راز' or 'پنهان' for Persian mystery."},
        {"name": "دستوری و قاطع", "emoji": "🛡️", "prompt": "Firm, loud, and authoritative, with a no-nonsense tone. Direct, confident, and unyielding, like issuing orders. Quick and sharp pacing, with clear enunciation (e.g., 'همین حالا انجام بده!'). Strength, control, and urgency. Dominant and resolute, like a military leader. Brief pauses after commands to assert dominance. Stress words like 'برو' or 'باشه' for Persian assertiveness."},
        {"name": "حکیمانه", "emoji": "🧙", "prompt": "Warm, deep, and measured, with a reflective quality. Thoughtful, profound, and reassuring, like imparting ancient wisdom. Slow and deliberate pacing, with a calm rhythm (e.g., 'زندگی... یعنی صبر...'). Serenity, insight, and compassion. Gentle and all-knowing, like a mentor or elder. Long pauses after profound statements to invite reflection. Soften words like 'حکمت' or 'راه' for Persian wisdom."},
        {"name": "کودکانه", "emoji": "🧸", "prompt": "High-pitched, bubbly, and playful, with a sing-song quality. Curious, naive, and joyful, like a child discovering the world. Fast and erratic pacing, with excited bursts (e.g., 'وای، این چیه؟ خیلی قشنگه!'). Wonder, innocence, and delight. Adorable and endearing, like a curious kid. Short, excited pauses after questions or discoveries. Use playful words like 'ووووی' or 'قشنگه' for Persian childlikeness."},
        {"name": "شیطانی", "emoji": "😈", "prompt": "Low, raspy, and menacing, with a chilling edge. Dark, malicious, and threatening, like a villain plotting. Slow and deliberate pacing, with sudden sharp rises for menace (e.g., 'تو... نمی‌تونی فرار کنی...'). Cruelty, menace, and cold amusement. Sinister and intimidating, like a diabolical mastermind. Long, eerie pauses to amplify fear. Hiss words like 'خطر' or 'نابودی' for Persian villainy."},
        {"name": "کلاسیک و قدیمی", "emoji": "📜", "prompt": "Deep, formal, and slightly nasal, with an antique charm. Grand, reverent, and formal, like reciting ancient poetry. Slow and deliberate pacing, with emphasis on archaic terms (e.g., 'ای یار... بشنو سخنم...'). Nostalgia, dignity, and solemnity. Stately and wise, like a bard from centuries past. Pauses after poetic phrases to add weight. Use old Persian words like 'یار' or 'سخن' with reverence."},
        {"name": "فریبنده و وسوسه‌انگیز", "emoji": "💋", "prompt": "Sultry, smooth, and breathy, with a teasing quality. Sensual, inviting, and flirtatious, like whispering sweet nothings. Slow and languid pacing, with drawn-out words (e.g., 'بیااا... نزدیک‌تر...'). Desire, charm, and subtle power. Magnetic and irresistible, like a charismatic seducer. Long, teasing pauses to draw listeners in. Soften words like 'عشق' or 'دل' for Persian allure."},
        {"name": "خسته و بی‌حال", "emoji": "😴", "prompt": "Sluggish, low, and breathy, with a yawning quality. Apathetic, unmotivated, and half-hearted, like someone too tired to care. Slow and dragging pacing, with drawn-out words (e.g., 'آآآآه... حالا چی؟'). Exhaustion, boredom, and reluctance. Lethargic and indifferent, like a slacker. Long, lazy pauses, as if too tired to continue. Stretch words like 'خسته‌م' or 'بی‌حال' for Persian laziness."},
    ],
    "functional": [
        {"name": "آموزشی", "emoji": "📚", "prompt": "Clear, steady, and articulate, with a teacherly tone. Informative, patient, and structured, like guiding a student. Moderate pacing, with pauses for comprehension (e.g., 'اول... این کارو بکن...'). Clarity, encouragement, and focus. Knowledgeable and supportive, like a mentor. Brief pauses after steps or key points for clarity. Enunciate words like 'گام' or 'یاد' for Persian instruction."},
        {"name": "انگیزشی", "emoji": "🚀", "prompt": "Uplifting, passionate, and resonant, with rising intonation. Empowering, enthusiastic, and rallying, like a coach inspiring a team. Moderate pacing, with speeds for excitement and slows for emphasis (e.g., 'تو می‌تونی... باور کن!'). Passion, determination, and hope. Charismatic and encouraging, like a life coach. Pauses after motivational phrases to inspire action. Stress words like 'باور' or 'موفقیت' for Persian motivation."},
        {"name": "تبلیغاتی و قانع‌کننده", "emoji": "💸", "prompt": "Smooth, confident, and enthusiastic, with a persuasive edge. Convincing, engaging, and slightly urgent, like a top salesperson. Fast and dynamic pacing, with slows for key benefits (e.g., 'فقط امروز... این فرصت رو از دست نده!'). Excitement, confidence, and urgency. Charismatic and trustworthy, like a slick advertiser. Brief pauses after selling points to drive home value. Emphasize words like 'فرصت' or 'ویژه' for Persian persuasion."},
        {"name": "خبری", "emoji": "📰", "prompt": "Clear, neutral, and professional, with a broadcast quality. Objective, concise, and authoritative, like delivering breaking news. Steady and brisk pacing, with clear enunciation (e.g., 'امروز... حادثه‌ای رخ داد...'). Neutrality, with subtle urgency for big stories. Credible and composed, like a news anchor. Brief, professional pauses between segments or facts. Use formal words like 'گزارش' or 'اخبار' for Persian news style."},
        {"name": "مستند", "emoji": "🎥", "prompt": "Warm, articulate, and engaging, with a storytelling quality. Informative, curious, and slightly dramatic, like narrating a nature film. Moderate pacing, with slows for emphasis (e.g., 'این موجود... قرن‌هاست که زنده‌ست...'). Wonder, respect, and curiosity. Knowledgeable and immersive, like a documentary host. Pauses after fascinating facts to let them sink in. Emphasize words like 'جهان' or 'کشف' for Persian documentary style."},
        {"name": "مراقبه‌ای و معنوی", "emoji": "🕉️", "prompt": "Soft, breathy, and hypnotic, with a soothing cadence. Serene, introspective, and transcendent, like guiding a meditation. Very slow pacing, with long, flowing phrases (e.g., 'نفس بکش... و آرام شو...'). Peace, spirituality, and connection. Gentle and otherworldly, like a spiritual guide. Long, calming pauses to mimic deep breathing. Soften words like 'آرامش' or 'روح' for Persian spirituality."},
        {"name": "بحث‌برانگیز و منطقی", "emoji": "⚖️", "prompt": "Sharp, confident, and assertive, with a debating edge. Logical, intense, and persuasive, like arguing a point. Fast and precise pacing, with slows for key arguments (e.g., 'این... دلیل اصلی ماست!'). Passion, conviction, and urgency. Articulate and competitive, like a debater. Brief pauses after strong points to emphasize logic. Stress words like 'دلیل' or 'حقیقت' for Persian argumentation."},
    ]
}

# Add translations for tone categories at the beginning of the file, after the TRANSLATIONS dictionary

# تعریف دسته‌بندی‌های احساسات - Define tone categories with translations
TONE_CATEGORIES_TRANSLATION = {
    "fa": {
        "عمومی": "عمومی",
        "احساسات": "احساسات",
        "مکالمه": "مکالمه",
        "توضیحات": "توضیحات",
        "حالت": "حالت"
    },
    "en": {
        "عمومی": "General",
        "احساسات": "Emotions",
        "مکالمه": "Conversation",
        "توضیحات": "Descriptions",
        "حالت": "Modes"
    }
}

# ایجاد اپلیکیشن FastAPI
app = FastAPI()

# Define webhook route for FastAPI
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"خطا در پردازش webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# تابع برای ارسال درخواست به API دستیار هوشمند
def call_api(prompt, image=None, conversation_history=None, file_url=None, user_fullname=None, seed=None):
    headers = {"Content-Type": "application/json"}
    
    # Prepare messages with conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add conversation history if available
    if conversation_history:
        for msg in conversation_history:
            messages.append(msg)
    
    # Prepare the user prompt with their name if available
    user_prompt = prompt
    if user_fullname:
        user_prompt = f"نام و نام خانوادگی کاربر: {user_fullname}\nمتن و یا سوال و جواب کاربر: {prompt}\nلطفا به متن جواب بده و از نام کاربر اگر انگلیسی بود به فارسی تبدیل کن و در صورت نیاز در متن استفاده کن"
    
    # Add current message
    if image is None and file_url is None:
        # Text-only query
        messages.append({"role": "user", "content": user_prompt})
    elif file_url is not None:
        # Add image as URL (Medical v6.py style)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": file_url}}
            ]
        })
    else:
        # Using the original method with base64 encoding
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            # Add the base64 image to messages based on API format
            messages.append({"role": "user", "content": user_prompt})
            messages.append({"role": "user", "content": {"image": image_base64}})
        except Exception as e:
            logger.error(f"خطا در پردازش تصویر برای API: {str(e)}")
            return "خطا در پردازش تصویر."

    payload = {
        "model": MODEL,
        "messages": messages,
        "vision": True
    }
    
    # Add seed if provided for response variation
    if seed is not None:
        payload["seed"] = seed

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

async def check_membership(bot, user_id):
    """بررسی عضویت کاربر در کانال مورد نظر"""
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        # اگر کاربر از کانال خارج شده یا اخراج شده باشد
        if member.status in ["left", "kicked"]:
            return False
        # اگر عضو است (member یا creator یا administrator)
        return True
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت کاربر {user_id}: {str(e)}")
        return False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌های اینلاین"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_membership":
        user_id = update.effective_user.id
        is_member = await check_membership(context.bot, user_id)
        
        # زبان فعلی کاربر یا زبان پیش‌فرض
        lang = context.user_data.get("language", DEFAULT_LANGUAGE)
        
        if is_member:
            # اگر کاربر عضو کانال باشد
            await query.message.delete()
            return await start_bot_services(update, context)
        else:
            # اگر هنوز عضو نشده باشد
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(TRANSLATIONS[lang]["join_channel"], url=REQUIRED_CHANNEL_URL)],
                [InlineKeyboardButton(TRANSLATIONS[lang]["verify_membership"], callback_data="check_membership")]
            ])
            
            await query.edit_message_text(
                TRANSLATIONS[lang]["membership_failed"],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    elif query.data == "settings":
        # مدیریت دکمه تنظیمات
        return await settings_handler(update, context)
    elif query.data == "set_language":
        # نمایش منوی انتخاب زبان
        lang = context.user_data.get("language", DEFAULT_LANGUAGE)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(TRANSLATIONS["fa"]["fa_language"], callback_data="set_lang_fa")],
            [InlineKeyboardButton(TRANSLATIONS["en"]["en_language"], callback_data="set_lang_en")],
            [InlineKeyboardButton(TRANSLATIONS[lang]["back_button"], callback_data="settings")]
        ])
        
        await query.edit_message_text(
            TRANSLATIONS[lang]["choose_language"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    elif query.data.startswith("set_lang_"):
        # مدیریت تغییر زبان
        lang = query.data.split("_")[2]  # set_lang_fa یا set_lang_en
        if lang in TRANSLATIONS:
            context.user_data["language"] = lang
            
            # انتخاب متن مناسب بر اساس زبان
            message_text = TRANSLATIONS[lang]["language_changed"]
            
            await query.edit_message_text(
                message_text,
                parse_mode="HTML"
            )
            
            # بررسی وضعیت کاربر - آیا در مرحله انتخاب زبان اولیه است یا در تنظیمات
            if context.user_data.get("state") == "select_language":
                # اگر اولین بار است، بررسی عضویت در کانال
                await asyncio.sleep(1)  # تاخیر کوتاه برای نمایش پیام تغییر زبان
                
                # بررسی عضویت در کانال
                user_id = update.effective_user.id
                is_member = await check_membership(context.bot, user_id)
                
                if is_member:
                    # اگر عضو کانال باشد
                    return await start_bot_services(update, context)
                else:
                    # اگر عضو کانال نباشد
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(TRANSLATIONS[lang]["join_channel"], url=REQUIRED_CHANNEL_URL)],
                        [InlineKeyboardButton(TRANSLATIONS[lang]["verify_membership"], callback_data="check_membership")]
                    ])
                    
                    await query.message.reply_text(
                        TRANSLATIONS[lang]["membership_required"],
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                    return None
            else:
                # اگر از طریق تنظیمات است، به صفحه اصلی برگرد
                await asyncio.sleep(1)  # تاخیر کوتاه برای نمایش پیام تغییر زبان
                return await start_bot_services(update, context)
    elif query.data == "back_to_main":
        # بازگشت به صفحه اصلی
        await query.message.delete()
        return await start_bot_services(update, context)
    return None

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت بخش تنظیمات"""
    # بررسی اینکه آیا درخواست از دکمه اینلاین آمده یا از دکمه‌های معمولی
    if update.callback_query:
        query = update.callback_query
        lang = context.user_data.get("language", DEFAULT_LANGUAGE)
        
        # ایجاد کیبورد اینلاین برای تنظیمات
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(TRANSLATIONS[lang]["language_setting"], callback_data="set_language")],
            [InlineKeyboardButton(TRANSLATIONS[lang]["back_button"], callback_data="back_to_main")]
        ])
        
        await query.edit_message_text(
            f"{TRANSLATIONS[lang]['settings_title']}\n\n"
            f"{TRANSLATIONS[lang]['settings_description']}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        # اگر از دکمه‌های معمولی انتخاب شده
        lang = context.user_data.get("language", DEFAULT_LANGUAGE)
        
        # ایجاد کیبورد اینلاین برای تنظیمات
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(TRANSLATIONS[lang]["language_setting"], callback_data="set_language")],
            [InlineKeyboardButton(TRANSLATIONS[lang]["back_button"], callback_data="back_to_main")]
        ])
        
        await update.message.reply_text(
            f"{TRANSLATIONS[lang]['settings_title']}\n\n"
            f"{TRANSLATIONS[lang]['settings_description']}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    context.user_data["state"] = "settings"
    context.user_data["previous_state"] = "main"
    return None

async def start_bot_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع سرویس‌های اصلی ربات پس از تایید عضویت"""
    user_id = update.effective_user.id
    user = update.effective_user
    user_fullname = f"{user.first_name} {user.last_name if user.last_name else ''}"
    user_fullname = user_fullname.strip()
    
    logger.info(f"دریافت دستور /start و تأیید عضویت برای کاربر: {user_id}")
    
    # اگر زبان در تنظیمات کاربر نباشد، زبان پیش‌فرض را تنظیم کن
    if "language" not in context.user_data:
        context.user_data["language"] = DEFAULT_LANGUAGE
    
    # زبان فعلی کاربر
    lang = context.user_data.get("language", DEFAULT_LANGUAGE)
    
    try:
        # Add reaction to the /start message - using a valid reaction emoji (😎)
        try:
            chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
            message_id = update.message.message_id if update.message else update.callback_query.message.message_id
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji="😎")],
                is_big=True
            )
        except Exception as e:
            # Log the error but continue execution
            logger.warning(f"خطا در افزودن واکنش: {str(e)}")

        # ایجاد کیبورد اصلی بر اساس زبان انتخاب شده
        keyboard = [
            [TRANSLATIONS[lang]["tts_button"]],
            [TRANSLATIONS[lang]["assistant_button"], TRANSLATIONS[lang]["sample_button"]],
            [TRANSLATIONS[lang]["settings_button"]]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Use the appropriate method to send message based on where the command came from
        welcome_message = TRANSLATIONS[lang]["welcome_message"].format(user_fullname=user_fullname)
        
        if update.message:
            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        
        context.user_data.clear()
        context.user_data["state"] = "main"
        context.user_data["language"] = lang  # حفظ زبان انتخاب شده
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع - نمایش منوی انتخاب زبان و سپس بررسی عضویت کاربر در کانال"""
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    
    # ابتدا برای انتخاب زبان، بدون بررسی عضویت در کانال
    if "language" not in context.user_data:
        # اگر زبان انتخاب نشده، منوی انتخاب زبان را نمایش دهیم
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")]
        ])
        
        await update.message.reply_text(
            "🌐 <b>انتخاب زبان | Language Selection</b>\n\n"
            "لطفاً زبان مورد نظر خود را برای استفاده از ربات انتخاب کنید.\n"
            "Please select your preferred language.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        context.user_data["state"] = "select_language"
        return None
    else:
        # پس از انتخاب زبان، بررسی عضویت در کانال
        lang = context.user_data.get("language", DEFAULT_LANGUAGE)
        is_member = await check_membership(context.bot, user_id)
        
        if is_member:
            # اگر کاربر عضو کانال است، به سرویس‌های اصلی ربات دسترسی دهید
            return await start_bot_services(update, context)
        else:
            # اگر کاربر عضو کانال نیست، پیام عضویت اجباری نمایش دهید
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(TRANSLATIONS[lang]["join_channel"], url=REQUIRED_CHANNEL_URL)],
                [InlineKeyboardButton(TRANSLATIONS[lang]["verify_membership"], callback_data="check_membership")]
            ])
            
            await update.message.reply_text(
                TRANSLATIONS[lang]["membership_required"],
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # دریافت زبان فعلی کاربر
    lang = context.user_data.get("language", DEFAULT_LANGUAGE)
    
    if context.user_data.get("state") != "assistant":
        await update.message.reply_text(
            "لطفاً ابتدا به بخش دستیار هوشمند بروید.",
            reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
        )
        return None

    photo = update.message.photo[-1]
    message_id = update.message.message_id
    chat_id = update.message.chat_id
    
    # Get user's full name
    user = update.effective_user
    user_fullname = f"{user.first_name} {user.last_name if user.last_name else ''}"
    user_fullname = user_fullname.strip()  # Remove extra spaces if last_name is None
    
    try:
        logger.info(f"پردازش تصویر از کاربر {user_id}")
        
        valid_reaction_emojis = ["👀", "🤔"]
        selected_emoji = random.choice(valid_reaction_emojis)
        
        try:
            # Add reaction with valid emoji
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=selected_emoji)],
                is_big=True
            )
            logger.info(f"Reacción {selected_emoji} añadida a la foto del usuario {user_id}")
        except Exception as e:
            logger.warning(f"No se pudo añadir reacción a la foto: {str(e)}")
        
        # Send processing message
        processing_message = await update.message.reply_text(
            "🔍",
            reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
        )
        
        # Get the photo file - similar to Medical v6.py approach
        photo_file = await photo.get_file()
        file_url = photo_file.file_path
        
        # Alternative approach for APIs that need the actual image bytes
        image_data = await photo_file.download_as_bytearray()
        image = process_image(image_data)
        
        # Get user caption or use default
        default_caption = "لطفاً این تصویر را تحلیل کنید و متن مناسب برای تبدیل به صدا پیشنهاد دهید." if lang == "fa" else "Please analyze this image and suggest appropriate text for text-to-speech conversion."
        user_caption = update.message.caption or default_caption
        
        # Add to conversation history
        if "conversation_history" not in context.user_data:
            context.user_data["conversation_history"] = []
            
        conversation_prefix = "تصویر با کپشن: " if lang == "fa" else "Image with caption: "
        context.user_data["conversation_history"].append({
            "role": "user", 
            "content": f"{conversation_prefix}{user_caption}"
        })
        
        # Create a progress update task to show the AI is working
        try:
            await processing_message.edit_text(TRANSLATIONS[lang]["analyzing_image"])
            await asyncio.sleep(1)
            await processing_message.edit_text(TRANSLATIONS[lang]["analyzing_processing"])
            
            # Show progress bar
            progress_duration = 5  # seconds
            step_duration = progress_duration / 20
            for percentage in range(0, 101, 5):
                try:
                    await processing_message.edit_text(
                        f"{TRANSLATIONS[lang]['analyzing_processing']}\n{create_progress_bar(percentage)}"
                    )
                    await asyncio.sleep(step_duration)
                except Exception as e:
                    logger.warning(f"خطا در به‌روزرسانی پیشرفت ({percentage}%): {str(e)}")
                    
            await processing_message.edit_text(TRANSLATIONS[lang]["receiving_results"])
        except Exception as e:
            logger.warning(f"خطا در به‌روزرسانی پیام پردازش: {str(e)}")
            # Continue despite progress bar errors
        
        # API call with retry mechanism
        max_retries = 2
        response = None
        
        for attempt in range(max_retries):
            try:
                # Use file_url approach (Medical v6.py style) and include user's full name
                response = call_api(user_caption, file_url=file_url, 
                                   conversation_history=context.user_data["conversation_history"],
                                   user_fullname=user_fullname)
                break  # If successful, exit the retry loop
            except Exception as e:
                logger.error(f"خطا در تحلیل تصویر (تلاش {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    response = "متأسفانه خطایی در تحلیل تصویر رخ داد. لطفاً دوباره امتحان کنید."
                await asyncio.sleep(1)  # Wait before retry
        
        # Add AI response to conversation history
        context.user_data["conversation_history"].append({
            "role": "assistant", 
            "content": response
        })
        
        # Borrar el mensaje de procesamiento
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=processing_message.message_id)
        except Exception as e:
            logger.warning(f"No se pudo borrar el mensaje de procesamiento: {str(e)}")
        
        # Enviar la respuesta como reply al mensaje original
        await update.message.reply_text(
            f"✨ تحلیل تصویر:\n\n{response}",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True),
            reply_to_message_id=message_id  # Responder directamente al mensaje original
        )
            
    except Exception as e:
        logger.error(f"خطا در پردازش تصویر برای کاربر {user_id}: {str(e)}")
        await update.message.reply_text(
            "❌ مشکلی در پردازش تصویر پیش آمد. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True),
            reply_to_message_id=message_id  # Responder directamente al mensaje original en caso de error
        )
    return None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Get user's full name
    user = update.effective_user
    user_fullname = f"{user.first_name} {user.last_name if user.last_name else ''}"
    user_fullname = user_fullname.strip()  # Remove extra spaces if last_name is None
    
    # Initialize conversation history for new users
    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    # تنظیم زبان پیش‌فرض اگر تعیین نشده باشد
    if "language" not in context.user_data:
        context.user_data["language"] = DEFAULT_LANGUAGE
    
    # دریافت زبان فعلی کاربر
    lang = context.user_data.get("language", DEFAULT_LANGUAGE)

    # مدیریت دکمه برگشت
    if text == TRANSLATIONS[lang]["back_button"]:
        current_state = context.user_data.get("state", "main")
        previous_state = context.user_data.get("previous_state", "main")
        
        if current_state == "main":
            await update.message.reply_text(
                TRANSLATIONS[lang]["main_menu"],
                reply_markup=ReplyKeyboardMarkup([
                    [TRANSLATIONS[lang]["tts_button"]],
                    [TRANSLATIONS[lang]["assistant_button"], TRANSLATIONS[lang]["sample_button"]],
                    [TRANSLATIONS[lang]["settings_button"]]
                ], resize_keyboard=True)
            )
            return None
        
        if previous_state == "main" or current_state == "assistant" or current_state == "settings":
            # Clear conversation history when going back to main menu
            if "conversation_history" in context.user_data:
                context.user_data["conversation_history"] = []
            return await start(update, context)
        
        # Handle back button for sample voice flow
        if current_state == "sample_voice":
            return await start(update, context)
        
        # Handle other back button cases
        if previous_state in ["select_tone_category", "select_tone", "manual_feeling", "text", "voice", "select_format"]:
            if previous_state == "select_tone_category":
                return await start(update, context)
            elif previous_state == "select_tone":
                keyboard = [
                    [TRANSLATIONS[lang]["manual_tone"]],
                    [TRANSLATIONS[lang]["functional_tones"], TRANSLATIONS[lang]["character_tones"]],
                    [TRANSLATIONS[lang]["voice_style_tones"], TRANSLATIONS[lang]["emotional_tones"]],
                    [TRANSLATIONS[lang]["back_button"]]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f"{TRANSLATIONS[lang]['tts_title']}\n\n"
                    f"{TRANSLATIONS[lang]['tts_description']}",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                context.user_data["state"] = "select_tone_category"
                context.user_data["previous_state"] = "main"
                return None
            
            # Implement the rest of back button logic for other states

    # مدیریت دکمه تنظیمات
    if text == TRANSLATIONS[lang]["settings_button"]:
        return await settings_handler(update, context)

    # مدیریت دکمه تبدیل متن به صدا
    if text == TRANSLATIONS[lang]["tts_button"]:
        try:
            # استفاده از دسته‌بندی‌های حس با ترجمه مناسب بر اساس زبان
            tone_categories = []
            for category in TONES.keys():
                translated_category = TONE_CATEGORIES_TRANSLATION[lang].get(category, category)
                tone_categories.append([translated_category])
            
            # اضافه کردن گزینه ورود دستی لحن و دکمه بازگشت
            tone_categories.append([TRANSLATIONS[lang]["manual_tone"]])
            tone_categories.append([TRANSLATIONS[lang]["back_button"]])
            
            reply_markup = ReplyKeyboardMarkup(tone_categories, resize_keyboard=True)
            
            await update.message.reply_text(
                f"{TRANSLATIONS[lang]['tts_title']}\n\n"
                f"{TRANSLATIONS[lang]['tts_description']}",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            context.user_data["state"] = "select_tone_category"
            context.user_data["previous_state"] = "main"
            return None
        except Exception as e:
            logger.error(f"خطا در نمایش منوی لحن‌ها برای کاربر {user_id}: {str(e)}")
            return None

    # مدیریت دکمه دستیار هوشمند
    if text == TRANSLATIONS[lang]["assistant_button"]:
        try:
            keyboard = [[TRANSLATIONS[lang]["back_button"]]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Mensaje inicial del asistente
            greeting_message = await update.message.reply_text(
                TRANSLATIONS[lang]["assistant_greeting"].format(user_fullname=user_fullname),
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            try:
                await context.bot.set_message_reaction(
                    chat_id=update.message.chat_id,
                    message_id=update.message.message_id,
                    reaction=[ReactionTypeEmoji(emoji="🤝")],
                    is_big=True
                )
            except Exception as e:
                logger.warning(f"No se pudo añadir reacción al mensaje: {str(e)}")
            
            context.user_data["state"] = "assistant"
            context.user_data["previous_state"] = "main"
            
            # Initialize conversation history if needed
            if "conversation_history" not in context.user_data:
                context.user_data["conversation_history"] = []
                
            # Add system welcome message to history
            welcome_msg = TRANSLATIONS[lang]["assistant_greeting"].format(user_fullname=user_fullname)
            context.user_data["conversation_history"].append({"role": "assistant", "content": welcome_msg})
            
            return None
        except Exception as e:
            logger.error(f"خطا در ارسال پیام برای دستیار هوشمند برای کاربر {user_id}: {str(e)}")
            return None

    # Handle new button - Voice and Feeling Samples
    if text == TRANSLATIONS[lang]["sample_button"]:
        context.user_data["state"] = "sample"
        context.user_data["previous_state"] = "main"
        
        tone_categories = []
        for category in TONES.keys():
            # Use translated category name based on language
            translated_category = TONE_CATEGORIES_TRANSLATION[lang].get(category, category)
            tone_categories.append([translated_category])
        
        tone_categories.append([TRANSLATIONS[lang]["back_button"]])
        
        reply_markup = ReplyKeyboardMarkup(tone_categories, resize_keyboard=True)
        
        await update.message.reply_text(
            TRANSLATIONS[lang]["select_tone_category"],
            reply_markup=reply_markup
        )
        return None

    if "state" in context.user_data:
        # انتخاب دسته‌بندی حس - Select tone category
        if context.user_data["state"] == "sample":
            # Get original Persian category key
            selected_category = None
            for persian_category, translated_name in TONE_CATEGORIES_TRANSLATION[lang].items():
                if text == translated_name:
                    selected_category = persian_category
                    break
                    
            # If it's a direct Persian category (for backward compatibility)
            if selected_category is None and text in TONES:
                selected_category = text
                
            if selected_category in TONES:
                context.user_data["selected_category"] = selected_category
                context.user_data["state"] = "select_tone"
                context.user_data["previous_state"] = "sample"
                
                # Create a keyboard with the tones from the selected category
                tones_keyboard = []
                for tone in TONES[selected_category]:
                    tones_keyboard.append([f"{tone['emoji']} {tone['name']}"])
                tones_keyboard.append([TRANSLATIONS[lang]["back_button"]])
                
                reply_markup = ReplyKeyboardMarkup(tones_keyboard, resize_keyboard=True)
                
                # Display category name in the user's language
                category_display_name = TONE_CATEGORIES_TRANSLATION[lang].get(selected_category, selected_category)
                
                if lang == "fa":
                    message = f"لطفاً یک حس از دسته {category_display_name} انتخاب کنید:"
                else:
                    message = f"Please select a tone from the {category_display_name} category:"
                
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )
                return None
        
        # انتخاب دسته‌بندی لحن - Select tone category for TTS
        elif context.user_data["state"] == "select_tone_category":
            # برای حالت ورود لحن دستی - For manual tone input
            if text == TRANSLATIONS[lang]["manual_tone"]:
                context.user_data["state"] = "manual_feeling"
                context.user_data["previous_state"] = "select_tone_category"
                context.user_data["feeling_manual"] = True
                await update.message.reply_text(
                    TRANSLATIONS[lang]["enter_manual_tone"],
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
            
            # تطبیق نام ترجمه شده به کلید فارسی - Map translated name to Persian key
            selected_category = None
            for persian_category, translated_name in TONE_CATEGORIES_TRANSLATION[lang].items():
                if text == translated_name:
                    selected_category = persian_category
                    break
                    
            # If it's a direct Persian category (for backward compatibility)
            if selected_category is None and text in TONES:
                selected_category = text
                
            if selected_category in TONES:
                tones = TONES[selected_category]
                context.user_data["selected_category"] = selected_category
                context.user_data["state"] = "select_tone"
                context.user_data["previous_state"] = "select_tone_category"
                
                # Create a keyboard with the tones from the selected category
                tones_keyboard = []
                for tone in TONES[selected_category]:
                    tones_keyboard.append([f"{tone['emoji']} {tone['name']}"])
                tones_keyboard.append([TRANSLATIONS[lang]["back_button"]])
                
                reply_markup = ReplyKeyboardMarkup(tones_keyboard, resize_keyboard=True)
                
                # Display category name in the user's language
                category_display_name = TONE_CATEGORIES_TRANSLATION[lang].get(selected_category, selected_category)
                
                if lang == "fa":
                    message = f"لطفاً یک حس از دسته {category_display_name} انتخاب کنید:"
                else:
                    message = f"Please select a tone from the {category_display_name} category:"
                
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )
                return None

        # انتخاب حس
        elif context.user_data["state"] == "select_tone":
            category = context.user_data.get("selected_category")
            tones = TONES[category]
            tone_name = text
            for tone in tones:
                if f"{tone['emoji']} {tone['name']}" == text:
                    tone_name = tone["name"]
                    context.user_data["feeling"] = tone["prompt"]
                    context.user_data["feeling_name"] = tone_name
                    context.user_data["state"] = "text"
                    context.user_data["previous_state"] = "select_tone"
                    context.user_data["feeling_manual"] = False
                    await update.message.reply_text(
                        TRANSLATIONS[lang]["enter_text"],
                        reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                    )
                    return None
            
            # پیام خطا بر اساس زبان انتخاب شده
            if lang == "fa":
                error_message = "لطفاً یک حس معتبر از لیست انتخاب کنید."
            else:
                error_message = "Please select a valid tone from the list."
                
            await update.message.reply_text(
                error_message,
                reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
            )
            return None

        # دریافت حس دستی
        elif context.user_data["state"] == "manual_feeling":
            feeling = text
            if len(feeling) > MAX_FEELING_LENGTH:
                await update.message.reply_text(
                    TRANSLATIONS[lang]["error_feeling_length"].format(length=len(feeling), max_length=MAX_FEELING_LENGTH),
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
            context.user_data["feeling"] = feeling
            context.user_data["feeling_name"] = "دستی" if lang == "fa" else "Custom"
            context.user_data["state"] = "text"
            context.user_data["previous_state"] = "manual_feeling"
            await update.message.reply_text(
                TRANSLATIONS[lang]["enter_text"],
                reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
            )
            return None
        
        # دریافت متن
        elif context.user_data["state"] == "text":
            if len(text) > MAX_TEXT_LENGTH:
                await update.message.reply_text(
                    TRANSLATIONS[lang]["error_text_length"].format(length=len(text), max_length=MAX_TEXT_LENGTH),
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
            context.user_data["text"] = text
            context.user_data["state"] = "voice"
            context.user_data["previous_state"] = "text"
            keyboard = []
            row = []
            for voice in SUPPORTED_VOICES:
                # Mostrar nombre persa con la primera letra en mayúscula
                persian_name = VOICE_PERSIAN_NAMES[voice]
                row.append(persian_name)
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([TRANSLATIONS[lang]["back_button"]])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                TRANSLATIONS[lang]["select_voice"],
                reply_markup=reply_markup
            )
            return None
        
        # دریافت صدا
        elif context.user_data["state"] == "voice":
            voice_persian = text  # Nombre persa seleccionado por el usuario
            
            # Comprobar si el nombre persa es válido
            if voice_persian in PERSIAN_TO_ORIGINAL_VOICE:
                # Obtener el nombre original de la voz
                voice = PERSIAN_TO_ORIGINAL_VOICE[voice_persian]
                context.user_data["voice"] = voice  # Guardar el nombre original para la API
                context.user_data["voice_persian"] = voice_persian  # Guardar el nombre persa para mostrar
                context.user_data["state"] = "select_format"
                context.user_data["previous_state"] = "voice"
                keyboard = [["MP3", "WAV", "OGG"], [TRANSLATIONS[lang]["back_button"]]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    TRANSLATIONS[lang]["select_format"],
                    reply_markup=reply_markup
                )
                return None
            else:
                # پیام خطا بر اساس زبان انتخاب شده
                if lang == "fa":
                    error_message = "لطفاً یک صدای معتبر از لیست انتخاب کنید."
                else:
                    error_message = "Please select a valid voice from the list."
                
                await update.message.reply_text(
                    error_message,
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
        
        # انتخاب فرمت صوتی
        elif context.user_data["state"] == "select_format":
            audio_format = text.lower()
            if audio_format not in SUPPORTED_FORMATS:
                # پیام خطا بر اساس زبان انتخاب شده
                if lang == "fa":
                    error_message = "لطفاً یک فرمت معتبر (MP3، WAV، OGG) انتخاب کنید."
                else:
                    error_message = "Please select a valid format (MP3, WAV, OGG)."
                
                await update.message.reply_text(
                    error_message,
                    reply_markup=ReplyKeyboardMarkup([["MP3", "WAV", "OGG"], [TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
            text = context.user_data["text"]
            instructions = context.user_data["feeling"]
            voice = context.user_data["voice"]  # Nombre original para la API
            voice_persian = context.user_data["voice_persian"]  # Nombre persa para mostrar
            feeling_name = context.user_data["feeling_name"]
            output_file = f"output_{uuid4()}.{audio_format}"
            
            try:
                # ایجاد شناسه یکتا برای درخواست تولید صدا
                task_id = f"tts_{uuid4().hex}"
                API_TASKS[task_id] = {"status": "running", "result": None}
                
                # نمایش پیام با اطلاعات صدای در حال تولید
                initial_text = f"🔊 <b>در حال تبدیل متن به صدا...</b>\n\n• <b>متن:</b> {text[:50]}{'...' if len(text) > 50 else ''}\n• <b>صدا:</b> {voice_persian}\n• <b>حس:</b> {feeling_name}\n• <b>فرمت:</b> {audio_format.upper()}"
                
                # استفاده از دکمه شیشه‌ای برای نمایش پروگرس بار
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[0]}", callback_data="waiting")]
                ])
                
                progress_message = await update.message.reply_text(
                    initial_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                # شروع درخواست API برای تولید صدا در یک ترد جداگانه
                thread = threading.Thread(
                    target=run_api_task,
                    args=(task_id, generate_audio, text, instructions, voice, output_file, audio_format)
                )
                thread.start()
                
                # نمایش پروگرس بار انیمیشنی در دکمه شیشه‌ای
                frame_index = 0
                while task_id in API_TASKS and API_TASKS[task_id]["status"] == "running":
                    frame_index = (frame_index + 1) % len(ANIMATED_PROGRESS_FRAMES)
                    try:
                        # بروزرسانی دکمه با فریم جدید پروگرس بار
                        new_keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[frame_index]}", callback_data="waiting")]
                        ])
                        
                        # بروزرسانی پیام با کیبورد جدید
                        await progress_message.edit_reply_markup(reply_markup=new_keyboard)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"خطا در به‌روزرسانی پروگرس بار: {str(e)}")
                
                # دریافت نتیجه درخواست
                result = API_TASKS.pop(task_id, {"status": "error", "result": None})
                success = result["status"] == "completed" and result["result"]
                
                # حذف پیام پروگرس بار
                try:
                    await progress_message.delete()
                except Exception as e:
                    logger.warning(f"خطا در حذف پیام پروگرس بار: {str(e)}")
                
                if success:
                    try:
                        with open(output_file, "rb") as audio:
                            # تنظیم متن توضیحات بر اساس زبان انتخاب شده
                            if lang == "fa":
                                caption = f"🎙 <b>تبدیل متن به صدا</b>\n\n• <b>گوینده:</b> {voice_persian}\n• <b>حس و لحن:</b> {feeling_name}\n• <b>فرمت:</b> {audio_format.upper()}"
                                title = f"صدای تولید شده - {voice_persian}"
                            else:
                                caption = f"🎙 <b>Text to Speech</b>\n\n• <b>Voice:</b> {voice_persian}\n• <b>Tone:</b> {feeling_name}\n• <b>Format:</b> {audio_format.upper()}"
                                title = f"Generated Audio - {voice_persian}"
                                
                            await update.message.reply_audio(
                                audio=audio,
                                caption=caption,
                                title=title,
                                parse_mode="HTML"
                            )
                        os.remove(output_file)
                        logger.info(f"فایل صوتی ارسال و حذف شد برای کاربر {user_id}: {output_file}")
                        
                        # بازگشت به صفحه اصلی با پیام مناسب زبان
                        keyboard = [
                            [TRANSLATIONS[lang]["tts_button"], TRANSLATIONS[lang]["assistant_button"]], 
                            [TRANSLATIONS[lang]["sample_button"]],
                            [TRANSLATIONS[lang]["settings_button"]]
                        ]
                        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                        
                        await update.message.reply_text(
                            TRANSLATIONS[lang]["audio_success_message"],
                            reply_markup=reply_markup,
                            parse_mode="HTML"
                        )
                        context.user_data.clear()
                        context.user_data["state"] = "main"
                        # حفظ زبان انتخاب شده کاربر
                        context.user_data["language"] = lang
                            
                    except Exception as e:
                        logger.error(f"خطا در ارسال فایل صوتی برای کاربر {user_id}: {str(e)}")
                        await update.message.reply_text(
                            "❌ خطا در ارسال فایل صوتی. لطفاً دوباره امتحان کنید.",
                            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                        )
                        try:
                            if os.path.exists(output_file):
                                os.remove(output_file)
                        except Exception:
                            logger.warning(f"ناتوانی در حذف فایل صوتی برای کاربر {user_id}: {output_file}")
                else:
                    await update.message.reply_text(
                        "❌ خطا در تولید صدا. لطفاً مطمئن شوید حس (حداکثر 500 کاراکتر) و متن (حداکثر 1000 کاراکتر) مناسب هستند و صدا پشتیبانی می‌شود.",
                        reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                    )
                
                return None
            
            except Exception as e:
                logger.error(f"خطا در فرآیند تولید صدا برای کاربر {user_id}: {str(e)}")
                await update.message.reply_text(
                    "❌ متأسفانه مشکلی در تولید صدا پیش آمد. لطفاً دوباره تلاش کنید.",
                    reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
                )
                
                return None
            
        # دستیار هوشمند
        elif context.user_data["state"] == "assistant":
            # Add user message to conversation history
            if "conversation_history" not in context.user_data:
                context.user_data["conversation_history"] = []
            
            # Guardar el ID del mensaje para responder directamente
            message_id = update.message.message_id
            
            context.user_data["conversation_history"].append({"role": "user", "content": text})
            
            # Keep conversation history to a reasonable size
            if len(context.user_data["conversation_history"]) > MAX_HISTORY * 2:  # *2 because each exchange has user and assistant messages
                context.user_data["conversation_history"] = context.user_data["conversation_history"][-MAX_HISTORY * 2:]
            
            # Show typing indicator
            try:
                temp_message = await update.message.reply_text("🤖", parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"خطا در ارسال پیام موقت: {str(e)}")
                temp_message = None
            
            # Call API with retry mechanism and a random seed for varied responses
            max_retries = 2
            response = None
            
            # Generate a random seed for variety in responses
            random_seed = int(uuid4().int % 100000)
            
            for attempt in range(max_retries):
                try:
                    # Include user's full name and random seed in API call
                    response = call_api(
                        text, 
                        conversation_history=context.user_data["conversation_history"], 
                        user_fullname=user_fullname,
                        seed=random_seed
                    )
                    break
                except Exception as e:
                    logger.error(f"خطا در دریافت پاسخ (تلاش {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt == max_retries - 1:  # Last attempt
                        response = "متأسفانه خطایی در پردازش درخواست رخ داد. لطفاً دوباره امتحان کنید."
                    await asyncio.sleep(1)  # Wait before retry
            
            # Remove typing indicator
            if temp_message:
                try:
                    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=temp_message.message_id)
                except Exception as e:
                    logger.warning(f"خطا در حذف پیام موقت: {str(e)}")
            
            # Add assistant response to conversation history
            context.user_data["conversation_history"].append({"role": "assistant", "content": response})
            
            # Responder directamente al mensaje original
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True),
                reply_to_message_id=message_id
            )
            return None

        # Handle sample voice selection
        elif context.user_data["state"] == "sample_voice":
            voice_persian = text
            if voice_persian in PERSIAN_TO_ORIGINAL_VOICE:
                voice = PERSIAN_TO_ORIGINAL_VOICE[voice_persian]
                context.user_data["sample_voice"] = voice
                context.user_data["sample_voice_persian"] = voice_persian
                context.user_data["state"] = "sample_tone_category"
                context.user_data["previous_state"] = "sample_voice"
                
                keyboard = [
                    ["📢 لحن‌های کاربردی", "👑 لحن‌های نمایشی / شخصیتی"],
                    ["🎤 لحن‌های گفتاری", "🎭 لحن‌های احساسی"],
                    [TRANSLATIONS[lang]["back_button"]]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f"🎙 <b>صدای انتخاب شده: {voice_persian}</b>\n\n"
                    "عالی! حالا لطفاً یکی از دسته‌بندی‌های حس و لحن را انتخاب کنید:",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return None
            else:
                await update.message.reply_text(
                    "❌ لطفاً یک صدای معتبر از لیست انتخاب کنید.",
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
                
        # Handle sample tone category selection
        elif context.user_data["state"] == "sample_tone_category":
            category_map = {
                "📢 لحن‌های کاربردی": "functional",
                "👑 لحن‌های نمایشی / شخصیتی": "character_affects",
                "🎤 لحن‌های گفتاری": "voice_styles",
                "🎭 لحن‌های احساسی": "emotional"
            }
            
            if text in category_map:
                category = category_map[text]
                context.user_data["sample_category"] = category
                tones = TONES[category]
                
                keyboard = []
                for i in range(0, len(tones), 2):
                    row = [f"{tones[i]['emoji']} {tones[i]['name']}"]
                    if i + 1 < len(tones):
                        row.append(f"{tones[i+1]['emoji']} {tones[i+1]['name']}")
                    keyboard.append(row)
                keyboard.append([TRANSLATIONS[lang]["back_button"]])
                
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                category_names = {
                    "emotional": "لحن‌های احساسی",
                    "voice_styles": "لحن‌های گفتاری",
                    "character_affects": "لحن‌های نمایشی / شخصیتی",
                    "functional": "لحن‌های کاربردی"
                }
                
                await update.message.reply_text(
                    f"🎭 <b>دسته‌بندی انتخاب شده: {category_names[category]}</b>\n\n"
                    "لطفاً یکی از حس‌های زیر را انتخاب کنید تا نمونه صدا را بشنوید:",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                
                context.user_data["state"] = "sample_tone"
                context.user_data["previous_state"] = "sample_tone_category"
                return None
            else:
                await update.message.reply_text(
                    "❌ لطفاً یکی از دسته‌بندی‌های موجود را انتخاب کنید.",
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
                
        # Handle sample tone selection and send audio sample
        elif context.user_data["state"] == "sample_tone":
            category = context.user_data.get("sample_category")
            voice = context.user_data.get("sample_voice")
            voice_persian = context.user_data.get("sample_voice_persian")
            
            if not category or not voice:
                await update.message.reply_text(
                    "❌ مشکلی در فرآیند انتخاب پیش آمد. لطفاً دوباره تلاش کنید.",
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
                
            tones = TONES[category]
            selected_tone = None
            
            for tone in tones:
                if f"{tone['emoji']} {tone['name']}" == text:
                    selected_tone = tone
                    break
                    
            if not selected_tone:
                await update.message.reply_text(
                    "❌ لطفاً یک حس معتبر از لیست انتخاب کنید.",
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )
                return None
                
            # Get tone information
            feeling_prompt = selected_tone["prompt"]
            tone_name = selected_tone["name"]
            
            try:
                # ایجاد متن نمونه (درخواست اول به API)
                sample_text = await generate_sample_text(update, tone_name, feeling_prompt, 200)
                
                # آماده سازی فایل خروجی
                output_file = f"sample_{uuid4()}.ogg"
                
                # ایجاد یک شناسه یکتا برای درخواست تولید صدا
                task_id = f"audio_{uuid4().hex}"
                API_TASKS[task_id] = {"status": "running", "result": None}
                
                # شروع درخواست API برای تولید صدا در یک ترد جداگانه
                thread = threading.Thread(
                    target=run_api_task,
                    args=(task_id, generate_audio, sample_text, feeling_prompt, voice, output_file, "ogg")
                )
                thread.start()
                
                # نمایش پیام با اطلاعات صدای در حال تولید
                initial_text = f"🔊 <b>در حال تولید صدا...</b>\n\n• <b>صدا:</b> {voice_persian}\n• <b>حس:</b> {tone_name}"
                
                # استفاده از دکمه شیشه‌ای برای نمایش پروگرس بار
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[0]}", callback_data="waiting")]
                ])
                
                progress_message = await update.message.reply_text(
                    initial_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                # نمایش پروگرس بار انیمیشنی در دکمه شیشه‌ای
                frame_index = 0
                while task_id in API_TASKS and API_TASKS[task_id]["status"] == "running":
                    frame_index = (frame_index + 1) % len(ANIMATED_PROGRESS_FRAMES)
                    try:
                        # بروزرسانی دکمه با فریم جدید پروگرس بار
                        new_keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton(f"در حال پردازش {ANIMATED_PROGRESS_FRAMES[frame_index]}", callback_data="waiting")]
                        ])
                        
                        # بروزرسانی پیام با کیبورد جدید
                        await progress_message.edit_reply_markup(reply_markup=new_keyboard)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"خطا در به‌روزرسانی پروگرس بار: {str(e)}")
                
                # دریافت نتیجه درخواست
                result = API_TASKS.pop(task_id, {"status": "error", "result": None})
                success = result["status"] == "completed" and result["result"]
                
                # حذف پیام پروگرس بار
                try:
                    await progress_message.delete()
                except Exception as e:
                    logger.warning(f"خطا در حذف پیام پروگرس بار: {str(e)}")
                
                if success:
                    try:
                        with open(output_file, "rb") as audio:
                            # تنظیم متن توضیحات بر اساس زبان انتخاب شده
                            if lang == "fa":
                                caption = f"🎙 <b>نمونه صدا</b>\n\n• <b>گوینده:</b> {voice_persian}\n• <b>حس و لحن:</b> {tone_name}\n\n<b>متن:</b>\n{sample_text}"
                                title = f"نمونه صدای {voice_persian} - {tone_name}"
                            else:
                                caption = f"🎙 <b>Voice Sample</b>\n\n• <b>Voice:</b> {voice_persian}\n• <b>Tone:</b> {tone_name}\n\n<b>Text:</b>\n{sample_text}"
                                title = f"Voice Sample {voice_persian} - {tone_name}"
                                
                            await update.message.reply_audio(
                                audio=audio,
                                caption=caption,
                                title=title,
                                parse_mode="HTML"
                            )
                        
                        # Delete temp file after sending
                        os.remove(output_file)
                        
                        # Keep the same state to allow further selections
                        return None
                        
                    except Exception as e:
                        logger.error(f"خطا در ارسال فایل صوتی نمونه برای کاربر {user_id}: {str(e)}")
                        
                        # پیام خطا بر اساس زبان انتخاب شده
                        if lang == "fa":
                            error_message = "❌ خطا در ارسال فایل صوتی. لطفاً دوباره امتحان کنید."
                        else:
                            error_message = "❌ Error sending audio file. Please try again."
                            
                        await update.message.reply_text(
                            error_message,
                            reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                        )
                        try:
                            if os.path.exists(output_file):
                                os.remove(output_file)
                        except Exception:
                            logger.warning(f"ناتوانی در حذف فایل صوتی برای کاربر {user_id}: {output_file}")
                else:
                    # پیام خطا بر اساس زبان انتخاب شده
                    if lang == "fa":
                        error_message = "❌ خطا در تولید نمونه صدا. لطفاً دوباره تلاش کنید."
                    else:
                        error_message = "❌ Error generating sample audio. Please try again."
                        
                    await update.message.reply_text(
                        error_message,
                        reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                    )
                    
            except Exception as e:
                logger.error(f"خطا در فرآیند تولید نمونه صدا برای کاربر {user_id}: {str(e)}")
                
                # پیام خطا بر اساس زبان انتخاب شده
                if lang == "fa":
                    error_message = "❌ متأسفانه مشکلی در تولید نمونه صدا پیش آمد. لطفاً دوباره تلاش کنید."
                else:
                    error_message = "❌ Sorry, there was an issue generating the sample audio. Please try again."
                    
                await update.message.reply_text(
                    error_message,
                    reply_markup=ReplyKeyboardMarkup([[TRANSLATIONS[lang]["back_button"]]], resize_keyboard=True)
                )

# Initialize the Telegram application
# Create the Application outside of the main function
application = Application.builder().token(TOKEN).build()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_callback))
application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

async def main():
    """Run the bot."""
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

if __name__ == "__main__":
    try:
        # اجرای ربات و سرور
        asyncio.run(main())
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error(f"خطا در اجرای برنامه: {str(e)}")
    finally:
        try:
            # No need to check if application.running as application is defined at the module level
            logger.info("توقف ربات")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(application.bot.delete_webhook())
            loop.run_until_complete(application.stop())
            loop.close()
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {str(e)}")
