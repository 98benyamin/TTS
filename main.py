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

# دیکشنری برای ترجمه متون و دکمه‌ها
TRANSLATIONS = {
    "fa": {
        # متون عمومی
        "welcome_message": "✨ <b>سلام {user_fullname} عزیز!</b> ✨\n\n🎵 به ربات پیشرفته تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n📌 <b>با این ربات می‌توانید:</b>\n• متن‌های خود را با حس و لحن دلخواه به صدا تبدیل کنید\n• از دستیار هوشمند برای پاسخ به سوالات و تحلیل تصاویر استفاده کنید\n• نمونه صداها و حس‌های مختلف را بشنوید و بهترین ترکیب را انتخاب کنید\n\n👇 <b>لطفاً یکی از گزینه‌های زیر را انتخاب کنید:</b>",
        "language_selection": "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید:</b>",
        "language_changed": "✅ زبان ربات به فارسی تغییر کرد.",
        
        # دکمه‌های منو
        "text_to_speech": "🎙 تبدیل متن به صدا",
        "smart_assistant": "🤖 دستیار هوشمند",
        "voice_samples": "🔊 نمونه صدا و حس ها",
        "settings": "⚙️ تنظیمات",
        "back": "🔙 برگشت",
        
        # تنظیمات
        "settings_title": "⚙️ <b>تنظیمات ربات</b>\n\nدر این بخش می‌توانید تنظیمات ربات را شخصی‌سازی کنید:",
        "language_settings": "🌐 تغییر زبان",
        "persian": "🇮🇷 فارسی",
        "english": "🇬🇧 انگلیسی",
        
        # منوی تنظیمات
        "in_main_menu": "✅ شما در صفحه اصلی هستید!",
    },
    "en": {
        # General texts
        "welcome_message": "✨ <b>Hello dear {user_fullname}!</b> ✨\n\n🎵 Welcome to the advanced Text-to-Speech and Smart Assistant bot!\n\n📌 <b>With this bot you can:</b>\n• Convert your texts to speech with custom tone and style\n• Use the smart assistant to answer questions and analyze images\n• Listen to sample voices and tones to choose the best combination\n\n👇 <b>Please select one of the options below:</b>",
        "language_selection": "🌐 <b>Please select your preferred language:</b>",
        "language_changed": "✅ Bot language changed to English.",
        
        # Menu buttons
        "text_to_speech": "🎙 Text to Speech",
        "smart_assistant": "🤖 Smart Assistant",
        "voice_samples": "🔊 Voice Samples",
        "settings": "⚙️ Settings",
        "back": "🔙 Back",
        
        # Settings
        "settings_title": "⚙️ <b>Bot Settings</b>\n\nIn this section you can customize bot settings:",
        "language_settings": "🌐 Change Language",
        "persian": "🇮🇷 Persian",
        "english": "🇬🇧 English",
        
        # Settings menu
        "in_main_menu": "✅ You are in the main menu!",
    }
}

# تنظیمات API دستیار هوشمند
API_URL = "https://text.pollinations.ai/"
SYSTEM_PROMPT = """
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
    """مدیریت کلیک روی دکمه‌های شیشه‌ای"""
    
    query = update.callback_query
    callback_data = query.data
    
    # برای حفظ UX، ابتدا acknowledged کنید
    await query.answer()
    
    user_id = update.effective_user.id
    
    # بررسی callback برای دکمه انتخاب زبان
    if callback_data.startswith("lang_"):
        language = callback_data.split("_")[1]  # fa یا en
        context.user_data["language"] = language
        translations = TRANSLATIONS[language]
        
        # پاسخ به کاربر با تایید تغییر زبان
        await query.message.edit_text(
            translations["language_changed"],
            parse_mode="HTML"
        )
        
        # برگرداندن کاربر به منوی اصلی با زبان جدید
        return await start_bot_services(update, context)
    
    # بررسی عضویت کاربر در کانال
    elif callback_data == "check_membership":
        is_member = await check_membership(context.bot, user_id)
        
        if is_member:
            await query.message.delete()
            await start_bot_services(update, context)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌟 عضویت در کانال رسمی", url=REQUIRED_CHANNEL_URL)],
                [InlineKeyboardButton("✅ تأیید عضویت من", callback_data="check_membership")]
            ])
            
            # پیام خطا - کاربر هنوز عضو کانال نیست
            await query.message.edit_text(
                "❌ <b>شما هنوز عضو کانال رسمی ما نشده‌اید!</b>\n\n"
                "📢 برای استفاده از امکانات ربات، ابتدا در کانال عضو شوید و سپس روی «تأیید عضویت من» کلیک کنید.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    
    # در اینجا می‌توانید سایر موارد callback را اضافه کنید
    elif callback_data == "settings_language":
        # نمایش دکمه‌های انتخاب زبان
        language = context.user_data.get("language", "fa")
        translations = TRANSLATIONS[language]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(translations["back"], callback_data="back_to_settings")]
        ])
        
        await query.message.edit_text(
            translations["language_selection"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    elif callback_data == "back_to_settings":
        # برگشت به منوی تنظیمات
        language = context.user_data.get("language", "fa")
        translations = TRANSLATIONS[language]
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translations["language_settings"], callback_data="settings_language")]
        ])
        
        await query.message.edit_text(
            translations["settings_title"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    return None

async def start_bot_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع سرویس‌های اصلی ربات پس از تایید عضویت"""
    user_id = update.effective_user.id
    user = update.effective_user
    user_fullname = f"{user.first_name} {user.last_name if user.last_name else ''}"
    user_fullname = user_fullname.strip()
    
    logger.info(f"دریافت دستور /start و تأیید عضویت برای کاربر: {user_id}")
    
    # اگر زبان قبلاً تنظیم نشده باشد، درخواست انتخاب زبان
    if "language" not in context.user_data:
        # نمایش دکمه‌های انتخاب زبان (شیشه‌ای)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ])
        
        if update.message:
            await update.message.reply_text(
                "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید:</b>\n\n"
                "🌐 <b>Please select your preferred language:</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                "🌐 <b>لطفاً زبان مورد نظر خود را انتخاب کنید:</b>\n\n"
                "🌐 <b>Please select your preferred language:</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        context.user_data["state"] = "language_selection"
        return None
    
    try:
        # استفاده از زبان انتخاب شده کاربر یا زبان پیش‌فرض (فارسی)
        language = context.user_data.get("language", "fa")
        translations = TRANSLATIONS[language]
        
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

        # ایجاد کیبورد با چیدمان مورد نظر
        keyboard = [
            [translations["text_to_speech"]], 
            [translations["smart_assistant"], translations["voice_samples"]],
            [translations["settings"]]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_message = translations["welcome_message"].format(user_fullname=user_fullname)
        
        # Use the appropriate method to send message based on where the command came from
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
            
        context.user_data["state"] = "main"
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع - بررسی عضویت کاربر در کانال"""
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    
    # بررسی عضویت کاربر در کانال
    is_member = await check_membership(context.bot, user_id)
    
    if is_member:
        # اگر عضو کانال است، مستقیم به سرویس‌های ربات دسترسی دهید
        return await start_bot_services(update, context)
    else:
        # اگر کاربر عضو کانال نیست، پیام عضویت اجباری نمایش دهید        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 عضویت در کانال رسمی", url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton("✅ تأیید عضویت من", callback_data="check_membership")]
        ])
        
        await update.message.reply_text(
            "🔐 <b>به ربات تبدیل متن به صدا خوش آمدید</b>\n\n"
            "📢 <b>برای استفاده از امکانات این ربات، ابتدا باید عضو کانال رسمی ما شوید.</b>\n"
            "🔄 پس از عضویت، روی دکمه «تأیید عضویت من» کلیک کنید.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # دریافت زبان فعلی کاربر یا تنظیم زبان پیش‌فرض (فارسی)
    language = context.user_data.get("language", "fa")
    translations = TRANSLATIONS[language]
    
    if context.user_data.get("state") != "assistant":
        error_message = "لطفاً ابتدا به بخش دستیار هوشمند بروید." if language == "fa" else "Please go to Smart Assistant first."
        await update.message.reply_text(
            error_message,
            reply_markup=ReplyKeyboardMarkup([[translations["back"]]], resize_keyboard=True)
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
            logger.info(f"واکنش {selected_emoji} به تصویر کاربر {user_id} اضافه شد")
        except Exception as e:
            logger.warning(f"خطا در افزودن واکنش به تصویر: {str(e)}")
        
        # Send processing message
        processing_message = await update.message.reply_text(
            "🔍",
            reply_markup=ReplyKeyboardMarkup([[translations["back"]]], resize_keyboard=True)
        )
        
        # Get the photo file - similar to Medical v6.py approach
        photo_file = await photo.get_file()
        file_url = photo_file.file_path
        
        # Alternative approach for APIs that need the actual image bytes
        image_data = await photo_file.download_as_bytearray()
        image = process_image(image_data)
        
        # Get user caption or use default
        default_caption = "لطفاً این تصویر را تحلیل کنید و متن مناسب برای تبدیل به صدا پیشنهاد دهید." if language == "fa" else "Please analyze this image and suggest appropriate text for conversion to speech."
        user_caption = update.message.caption or default_caption
        
        # Add to conversation history
        if "conversation_history" not in context.user_data:
            context.user_data["conversation_history"] = []
            
        context.user_data["conversation_history"].append({
            "role": "user", 
            "content": f"تصویر با کپشن: {user_caption}"
        })
        
        # متن‌های مراحل پردازش بر اساس زبان
        analyzing_text = "در حال آنالیز تصویر 🔍" if language == "fa" else "Analyzing image 🔍"
        processing_text = "در حال تحلیل و پردازش 🧠" if language == "fa" else "Processing and analyzing 🧠"
        results_text = "در حال دریافت نتایج تحلیل..." if language == "fa" else "Getting analysis results..."
        
        # Create a progress update task to show the AI is working
        try:
            await processing_message.edit_text(analyzing_text)
            await asyncio.sleep(1)
            await processing_message.edit_text(processing_text)
            
            # Show progress bar
            progress_duration = 5  # seconds
            step_duration = progress_duration / 20
            for percentage in range(0, 101, 5):
                try:
                    await processing_message.edit_text(
                        f"{processing_text}\n{create_progress_bar(percentage)}"
                    )
                    await asyncio.sleep(step_duration)
                except Exception as e:
                    logger.warning(f"خطا در به‌روزرسانی پیشرفت ({percentage}%): {str(e)}")
                    
            await processing_message.edit_text(results_text)
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
                    response = "متأسفانه خطایی در تحلیل تصویر رخ داد. لطفاً دوباره امتحان کنید." if language == "fa" else "Sorry, an error occurred while analyzing the image. Please try again."
                await asyncio.sleep(1)  # Wait before retry
        
        # Add AI response to conversation history
        context.user_data["conversation_history"].append({
            "role": "assistant", 
            "content": response
        })
        
        # پاک کردن پیام پردازش
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=processing_message.message_id)
        except Exception as e:
            logger.warning(f"خطا در پاک کردن پیام پردازش: {str(e)}")
        
        # تنظیم عنوان تحلیل بر اساس زبان
        analysis_title = "✨ تحلیل تصویر:" if language == "fa" else "✨ Image Analysis:"
        
        # ارسال پاسخ به عنوان پاسخ به پیام اصلی
        await update.message.reply_text(
            f"{analysis_title}\n\n{response}",
            reply_markup=ReplyKeyboardMarkup([[translations["back"]]], resize_keyboard=True),
            reply_to_message_id=message_id  # پاسخ مستقیم به پیام اصلی
        )
            
    except Exception as e:
        logger.error(f"خطا در پردازش تصویر برای کاربر {user_id}: {str(e)}")
        error_message = "❌ مشکلی در پردازش تصویر پیش آمد. لطفاً دوباره امتحان کنید." if language == "fa" else "❌ An error occurred while processing the image. Please try again."
        await update.message.reply_text(
            error_message,
            reply_markup=ReplyKeyboardMarkup([[translations["back"]]], resize_keyboard=True),
            reply_to_message_id=message_id  # پاسخ مستقیم به پیام اصلی در صورت خطا
        )
    return None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # بررسی عضویت در کانال
    is_member = await check_membership(context.bot, user_id)
    if not is_member:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 عضویت در کانال رسمی", url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton("✅ تأیید عضویت من", callback_data="check_membership")]
        ])
        
        await update.message.reply_text(
            "🔐 <b>به ربات تبدیل متن به صدا خوش آمدید</b>\n\n"
            "📢 <b>برای استفاده از امکانات این ربات، ابتدا باید عضو کانال رسمی ما شوید.</b>\n"
            "🔄 پس از عضویت، روی دکمه «تأیید عضویت من» کلیک کنید.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return None

    # Get user's full name
    user = update.effective_user
    user_fullname = f"{user.first_name} {user.last_name if user.last_name else ''}"
    user_fullname = user_fullname.strip()  # Remove extra spaces if last_name is None
    
    # دریافت زبان فعلی کاربر یا تنظیم زبان پیش‌فرض (فارسی)
    language = context.user_data.get("language", "fa")
    translations = TRANSLATIONS[language]
    
    # Initialize conversation history for new users
    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    # مدیریت دکمه برگشت
    if text == "🔙 برگشت" or text == "🔙 Back":  # پشتیبانی از هر دو زبان برای دکمه برگشت
        current_state = context.user_data.get("state", "main")
        previous_state = context.user_data.get("previous_state", "main")
        
        if current_state == "main":
            # ساخت کیبورد اصلی با زبان فعلی
            keyboard = [
                [translations["text_to_speech"]], 
                [translations["smart_assistant"], translations["voice_samples"]],
                [translations["settings"]]
            ]
            await update.message.reply_text(
                translations["in_main_menu"],
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return None
        
        if previous_state == "main" or current_state == "assistant":
            # ساخت کیبورد اصلی با زبان فعلی
            keyboard = [
                [translations["text_to_speech"]], 
                [translations["smart_assistant"], translations["voice_samples"]],
                [translations["settings"]]
            ]
            
            await update.message.reply_text(
                "🏠",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            
            context.user_data["state"] = "main"
            context.user_data["previous_state"] = None
            return None
    
    # مدیریت دکمه تنظیمات
    elif text == "⚙️ تنظیمات" or text == "⚙️ Settings":  # پشتیبانی از هر دو زبان برای دکمه تنظیمات
        # ذخیره وضعیت قبلی
        context.user_data["previous_state"] = context.user_data.get("state", "main")
        context.user_data["state"] = "settings"
        
        # ساخت دکمه‌های تنظیمات
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translations["language_settings"], callback_data="settings_language")]
        ])
        
        await update.message.reply_text(
            translations["settings_title"],
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return None
    
    # مدیریت دکمه تبدیل متن به صدا
    elif text == "🎙 تبدیل متن به صدا" or text == "🎙 Text to Speech":  # پشتیبانی از هر دو زبان
        # ذخیره وضعیت قبلی و تغییر به حالت تبدیل متن به صدا
        context.user_data["previous_state"] = context.user_data.get("state", "main")
        context.user_data["state"] = "text_to_speech"
        
        # متن راهنما بر اساس زبان فعلی
        instructions_text = "🎙 <b>تبدیل متن به صدا</b>\n\n" if language == "fa" else "🎙 <b>Text to Speech</b>\n\n"
        instructions_text += "لطفاً متن خود را برای تبدیل به صدا وارد کنید:" if language == "fa" else "Please enter your text to convert to speech:"
        
        # نمایش دکمه برگشت با نام مناسب زبان
        keyboard = [[translations["back"]]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            instructions_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return None
    
    # مدیریت دکمه دستیار هوشمند
    elif text == "🤖 دستیار هوشمند" or text == "🤖 Smart Assistant":
        # ذخیره وضعیت قبلی و تغییر به حالت دستیار هوشمند
        context.user_data["previous_state"] = context.user_data.get("state", "main")
        context.user_data["state"] = "assistant"
        
        # متن راهنما بر اساس زبان فعلی
        instructions_text = "🤖 <b>دستیار هوشمند</b>\n\n" if language == "fa" else "🤖 <b>Smart Assistant</b>\n\n"
        instructions_text += "لطفاً سوال خود را بپرسید یا یک تصویر ارسال کنید تا تحلیل شود:" if language == "fa" else "Please ask your question or send an image to analyze:"
        
        # نمایش دکمه برگشت با نام مناسب زبان
        keyboard = [[translations["back"]]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            instructions_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return None
    
    # مدیریت دکمه نمونه صدا و حس ها
    elif text == "🔊 نمونه صدا و حس ها" or text == "🔊 Voice Samples":
        # ذخیره وضعیت قبلی و تغییر به حالت نمونه صدا
        context.user_data["previous_state"] = context.user_data.get("state", "main")
        context.user_data["state"] = "voice_samples"
        
        # متن راهنما بر اساس زبان فعلی
        instructions_text = "🔊 <b>نمونه صدا و حس ها</b>\n\n" if language == "fa" else "🔊 <b>Voice Samples</b>\n\n"
        instructions_text += "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:" if language == "fa" else "Please select one of the options below:"
        
        # دکمه‌های مخصوص بخش نمونه صدا و حس ها
        voices_text = "📊 صداهای موجود" if language == "fa" else "📊 Available Voices"
        tones_text = "🎭 حس‌های موجود" if language == "fa" else "🎭 Available Tones"
        
        keyboard = [
            [voices_text, tones_text],
            [translations["back"]]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            instructions_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        return None
    
    # بقیه کد تابع message_handler
    # پردازش متن بر اساس حالت فعلی کاربر
    # ...

    # برای رعایت اختصار، بقیه کد را حفظ کنیم
    # و فقط قسمت‌های مورد نیاز را تغییر دهیم
    
    # کد موجود برای حالت‌های مختلف
    # ...
    
    return None

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
