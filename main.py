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
    ContextTypes,
)
from uuid import uuid4
import logging
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from PIL import Image
import io
import base64

# تنظیم لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7520523575:AAHNy73MjTRmatJejA96BlaNu0hGHczfYvk"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
MAX_TEXT_LENGTH = 1000  # حداکثر طول متن

# تنظیمات API دستیار هوشمند
API_URL = "https://text.pollinations.ai/"
SYSTEM_PROMPT = "شما دستیار ربات متن به صدا هستید لطفا به کاربران برای ساخت متن‌های کمک کنید."
MODEL = "openai-large"

# تعریف حس‌ها
TONES = {
    "emotional": {
        "joyful": {
            "name": "شاد و سرزنده 😊",
            "prompt": "Bright, lively, and warm, with a sing-song quality and frequent pitch rises. Upbeat, enthusiastic, and bursting with positivity. Fast and bouncy pacing, short pauses after key phrases, emphasizing elongated words like 'خوشحااال' or 'عااالی'."
        },
        "sad": {
            "name": "غمگین و محزون 😢",
            "prompt": "Soft, low-pitched, and heavy, with a trembling or wavering quality. Melancholic and sorrowful, slow and deliberate pacing, long heavy pauses, shaky tone for words like 'دلم' or 'غم'."
        },
        "excited": {
            "name": "هیجان‌زده 🎉",
            "prompt": "High-energy, animated, with rapid pitch shifts and vibrant intonation. Thrilled and eager, fast-paced with brief slows, short strategic pauses after big reveals, stretching words like 'فوووق‌العاده' or 'عاااالی'."
        },
        "angry": {
            "name": "عصبانی 😣",
            "prompt": "Sharp, intense, and forceful, with a raised pitch and clipped delivery. Heated and confrontational, quick and aggressive pacing, short tense pauses, emphasizing harsh consonants in words like 'بسّه' or 'دیگه'."
        },
        "hopeful": {
            "name": "امیدوارکننده 🌟",
            "prompt": "Warm, gentle, and rising, with a soothing yet optimistic cadence. Encouraging and inspiring, moderate pacing with slight slows, gentle pauses, softening vowels in words like 'امید' or 'آینده'."
        },
        "calm": {
            "name": "آرام و ریلکس 🕊️",
            "prompt": "Smooth, low, and steady, with minimal pitch variation. Serene and peaceful, slow and even pacing, long natural pauses, elongating words like 'آآآرام' or 'راحت'."
        },
        "anxious": {
            "name": "مضطرب 😓",
            "prompt": "High-pitched, shaky, and unsteady, with frequent hesitations. Tense and uncertain, erratic pacing with fast bursts and sudden slows, frequent uneven pauses, stuttering words like 'وااای' or 'استرس'."
        },
        "fearful": {
            "name": "ترس‌آلود 😨",
            "prompt": "Whispery, tense, and hushed, with sharp pitch rises for emphasis. Ominous and suspenseful, slow and deliberate pacing with sudden quick bursts, long pauses, whispering words like 'ترس' or 'خطر'."
        },
        "melancholic": {
            "name": "غم‌انگیز یا نوستالژیک 🕰️",
            "prompt": "Soft, wistful, and slightly breathy, with a reflective tone. Bittersweet and yearning, slow and lingering pacing, long reflective pauses, elongating vowels in 'خاطره' or 'گذشته'."
        },
        "loving": {
            "name": "محبت‌آمیز 💖",
            "prompt": "Warm, soft, and tender, with a gentle, caressing quality. Caring and intimate, slow and deliberate pacing, gentle pauses, softening words like 'عزیزم' or 'عشق'."
        }
    },
    "voice_styles": {
        "narrative": {
            "name": "داستان‌گونه 📖",
            "prompt": "Rich, expressive, and immersive, with varied pitch. Engaging and descriptive, moderate pacing with slows for drama, strategic pauses, emphasizing descriptive words like 'ناگهان' or 'ماجرا'."
        },
        "conversational": {
            "name": "محاوره‌ای و خودمونی 😎",
            "prompt": "Casual, friendly, and natural, like chatting with a friend. Relaxed and approachable, moderate pacing, natural pauses, using slang like 'آره دیگه' or 'خب'."
        },
        "formal": {
            "name": "رسمی و دقیق 🎩",
            "prompt": "Polished, clear, and authoritative, with steady intonation. Professional and respectful, measured pacing, brief purposeful pauses, enunciating words like 'محترم' or 'رسمی'."
        },
        "informal": {
            "name": "صمیمی و ساده 😄",
            "prompt": "Light, playful, and unpolished, with a relaxed vibe. Friendly and carefree, fast and loose pacing, minimal pauses, using colloquial terms like 'باحال' or 'فاز'."
        },
        "monotone": {
            "name": "یکنواخت و بی‌حالت 🤖",
            "prompt": "Flat, unchanging, and robotic, with no pitch variation. Neutral and detached, steady pacing, even predictable pauses, avoiding elongations."
        },
        "animated": {
            "name": "نمایشی و پرانرژی 🎭",
            "prompt": "NSNotification: Dynamic, colorful, and theatrical, with exaggerated pitch shifts. Lively and engaging, fast and varied pacing, dramatic pauses, stretching words like 'عاااالی' or 'باورنکردنییی'."
        },
        "dramatic": {
            "name": "دراماتیک و پرتعلیق 🎬",
            "prompt": "Intense, resonant, and gripping, with a cinematic quality. Suspenseful and emotional, slow pacing for tension, long suspenseful pauses, emphasizing words like 'سرنوشت' or 'خطر'."
        },
        "deadpan": {
            "name": "خشک و بی‌احساس 😐",
            "prompt": "Flat, monotone, and understated, with subtle irony. Sarcastic and detached, slow and deliberate pacing, brief pauses after sarcastic remarks, flat intonation for 'عجب' or 'جدی'."
        }
    },
    "character_affects": {
        "sarcastic": {
            "name": "طعنه‌آمیز 🙄",
            "prompt": "Snarky, exaggerated, and slightly nasal, with a mocking edge. Ironic and passive-aggressive, moderate pacing, pauses after sarcastic remarks, stretching words like 'عجببب' or 'واقعاًآآ'."
        },
        "heroic": {
            "name": "حماسی ⚔️",
            "prompt": "Deep, booming, and commanding, with a regal quality. Noble and inspiring, measured pacing, long pauses after rallying cries, emphasizing words like 'شجاعت' or 'افتخار'."
        },
        "mysterious": {
            "name": "مرموز 🕵️",
            "prompt": "Low, breathy, and elusive, with a hint of intrigue. Cryptic and alluring, slow and deliberate pacing, long suspenseful pauses, whispering words like 'راز' or 'پنهان'."
        },
        "commanding": {
            "name": "دستوری و قاطع 🛡️",
            "prompt": "Firm, loud, and authoritative, with a no-nonsense tone. Direct and confident, quick and sharp pacing, brief pauses, stressing words like 'برو' or 'باشه'."
        },
        "wise": {
            "name": "حکیمانه 🧙",
            "prompt": "Warm, deep, and measured, with a reflective quality. Thoughtful and profound, slow and deliberate pacing, long pauses, softening words like 'حکمت' or 'راه'."
        },
        "childlike": {
            "name": "کودکانه 🧸",
            "prompt": "High-pitched, bubbly, and playful, with a sing-song quality. Curious and naive, fast and erratic pacing, short excited pauses, using playful words like 'ووووی' or 'قشنگه'."
        },
        "evil": {
            "name": "شیطانی 😈",
            "prompt": "Low, raspy, and menacing, with a chilling edge. Dark and malicious, slow and deliberate pacing, long eerie pauses, hissing words like 'خطر' or 'نابودی'."
        },
        "old_fashioned": {
            "name": "کلاسیک و قدیمی 📜",
            "prompt": "Deep, formal, and slightly nasal, with an antique charm. Grand and reverent, slow and deliberate pacing, pauses after poetic phrases, using old Persian words like 'یار' or 'سخن'."
        },
        "seductive": {
            "name": "فریبنده و وسوسه‌انگیز 💋",
            "prompt": "Sultry, smooth, and breathy, with a teasing quality. Sensual and inviting, slow and languid pacing, long teasing pauses, softening words like 'عشق' or 'دل'."
        },
        "tired": {
            "name": "خسته و بی‌حال 😴",
            "prompt": "Sluggish, low, and breathy, with a yawning quality. Apathetic and unmotivated, slow and dragging pacing, long lazy pauses, stretching words like 'خسته‌م' or 'بی‌حال'."
        }
    },
    "functional": {
        "instructional": {
            "name": "آموزشی 📚",
            "prompt": "Clear, steady, and articulate, with a teacherly tone. Informative and patient, moderate pacing, brief pauses after steps, enunciating words like 'گام' or 'یاد'."
        },
        "motivational": {
            "name": "انگیزشی 🚀",
            "prompt": "Uplifting, passionate, and resonant, with rising intonation. Empowering and enthusiastic, moderate pacing, pauses after motivational phrases, stressing words like 'باور' or 'موفقیت'."
        },
        "sales": {
            "name": "تبلیغاتی و قانع‌کننده 💸",
            "prompt": "Smooth, confident, and enthusiastic, with a persuasive edge. Convincing and engaging, fast and dynamic pacing, brief pauses after selling points, emphasizing words like 'فرصت' or 'ویژه'."
        },
        "news_like": {
            "name": "خبری 📰",
            "prompt": "Clear, neutral, and professional, with a broadcast quality. Objective and concise, steady and brisk pacing, brief professional pauses, using formal words like 'گزارش' or 'اخبار'."
        },
        "documentary": {
            "name": "مستند 🎥",
            "prompt": "Warm, articulate, and engaging, with a storytelling quality. Informative and curious, moderate pacing, pauses after fascinating facts, emphasizing words like 'جهان' or 'کشف'."
        },
        "meditative": {
            "name": "مراقبه‌ای و معنوی 🕉️",
            "prompt": "Soft, breathy, and hypnotic, with a soothing cadence. Serene and introspective, very slow pacing, long calming pauses, softening words like 'آرامش' or 'روح'."
        },
        "debate": {
            "name": "بحث‌برانگیز و منطقی ⚖️",
            "prompt": "Sharp, confident, and assertive, with a debating edge. Logical and intense, fast and precise pacing, brief pauses after strong points, stressing words like 'دلیل' or 'حقیقت'."
        }
    }
}

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
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        payload["messages"].append({"role": "user", "content": {"image": image_base64}})

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("response", "پاسخی دریافت نشد.")
    except Exception as e:
        logger.error(f"API error: {e}")
        return f"خطا در ارتباط با API: {e}"

# تابع برای پردازش تصویر
def process_image(image_data):
    return Image.open(io.BytesIO(image_data))

def generate_audio(text, instructions, output_file):
    logger.info(f"تولید صدا با متن: {text[:50]}..., حس: {instructions[:50]}...")
    
    prompt = (
        f"Deliver the following text with the feeling described below:\n"
        f"Instructions: {instructions}\n\n"
        f"Now please repeat the text I give you with the same feeling I gave you, without adding anything to the text. Repeat the text:\n"
        f"{text}"
    )
    
    base_url = "https://text.pollinations.ai/"
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{base_url}{encoded_prompt}"
    
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
    filled = percentage // 5
    empty = 20 - filled
    bar = "█" * filled + "□" * empty
    return f"[{bar} {percentage}%]"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /start از کاربر: {user_id}")
    try:
        keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🎙 به ربات تبدیل متن به صدا و دستیار هوشمند خوش آمدید!\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )
        context.user_data["state"] = "home"
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /start برای کاربر {user_id}: {str(e)}")
    return None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if "state" not in context.user_data:
        context.user_data["state"] = "home"

    if text == "🔙 برگشت":
        if context.user_data["state"] in ["tone_category", "manual_tone", "select_tone", "text_input"]:
            # بازگشت به صفحه خانه
            keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "به صفحه اصلی بازگشتید. لطفاً یک گزینه انتخاب کنید:",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "home"
        elif context.user_data["state"] == "assistant":
            # بازگشت به صفحه خانه از دستیار هوشمند
            keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "به صفحه اصلی بازگشتید. لطفاً یک گزینه انتخاب کنید:",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "home"
        return None

    if context.user_data["state"] == "home":
        if text == "🎙 تبدیل متن به صدا":
            try:
                keyboard = [
                    ["لحن و صدا دستی"],
                    ["📢 لحن‌های کاربردی", "👑 لحن‌های نمایشی / شخصیتی"],
                    ["🎤 لحن‌های گفتاری", "🎭 لحن‌های احساسی"],
                    ["🔙 برگشت"]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    "شما به بخش انتخاب لحن و حس منتقل شدید!\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
                    reply_markup=reply_markup
                )
                context.user_data["state"] = "tone_category"
                return None
            except Exception as e:
                logger.error(f"خطا در ارسال پیام برای انتخاب لحن: {str(e)}")
                return None
        elif text == "🤖 دستیار هوشمند":
            try:
                keyboard = [["🔙 برگشت"]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    "سلام! من ربات دستیار متن به صدا هستم. متن یا تصویر بفرستید تا به شما کمک کنم!",
                    reply_markup=reply_markup
                )
                context.user_data["state"] = "assistant"
                return None
            except Exception as e:
                logger.error(f"خطا در ارسال پیام برای دستیار هوشمند: {str(e)}")
                return None

    elif context.user_data["state"] == "tone_category":
        if text == "لحن و صدا دستی":
            await update.message.reply_text(
                "لطفاً حس یا دستورالعمل‌های صدا را وارد کنید (حداکثر 500 کاراکتر).\n"
                "مثال: Dramatic یا Gruff, fast-talking, New York accent",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            context.user_data["state"] = "manual_tone"
            return None
        elif text in ["📢 لحن‌های کاربردی", "👑 لحن‌های نمایشی / شخصیتی", "🎤 لحن‌های گفتاری", "🎭 لحن‌های احساسی"]:
            category = {
                "📢 لحن‌های کاربردی": "functional",
                "👑 لحن‌های نمایشی / شخصیتی": "character_affects",
                "🎤 لحن‌های گفتاری": "voice_styles",
                "🎭 لحن‌های احساسی": "emotional"
            }[text]
            context.user_data["tone_category"] = category
            
            tones = TONES[category]
            keyboard = []
            row = []
            for tone_id, tone_data in tones.items():
                row.append(InlineKeyboardButton(tone_data["name"], callback_data=f"tone_{category}_{tone_id}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"لطفاً یکی از {text} را انتخاب کنید:",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "select_tone"
            return None

    elif context.user_data["state"] == "manual_tone":
        feeling = text
        if len(feeling) > 500:
            await update.message.reply_text(
                f"خطا: حس شما {len(feeling)} کاراکتر است. لطفاً حسی با حداکثر 500 کاراکتر وارد کنید.",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            return None
        
        context.user_data["feeling"] = feeling
        context.user_data["state"] = "text_input"
        await update.message.reply_text(
            "حالا متن موردنظر برای تبدیل به صدا را وارد کنید (حداکثر 1000 کاراکتر).\n"
            "مثال: Yeah, yeah, ya got Big Apple Insurance",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
        return None

    elif context.user_data["state"] == "text_input":
        text = text
        if len(text) > MAX_TEXT_LENGTH:
            await update.message.reply_text(
                f"خطا: متن شما {len(text)} کاراکتر است. لطفاً متنی با حداکثر {MAX_TEXT_LENGTH} کاراکتر وارد کنید.",
                reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
            )
            return None
        
        context.user_data["text"] = text
        await generate_audio_response(update, context)
        return None

    elif context.user_data["state"] == "assistant":
        response = call_api(text)
        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
        return None

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
        logger.error(f"Error processing image for user {user_id}: {e}")
        await update.message.reply_text(
            "مشکلی در پردازش تصویر پیش آمد. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
    return None

async def receive_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    logger.info(f"دریافت داده از کاربر {user_id}: {data}")

    if data.startswith("tone_"):
        _, category, tone_id = data.split("_")
        contextPanasonic: context.user_data["feeling"] = TONES[category][tone_id]["prompt"]
        context.user_data["state"] = "text_input"
        
        await query.message.reply_text(
            "حالا متن موردنظر برای تبدیل به صدا را وارد کنید (حداکثر 1000 کاراکتر).\n"
            "مثال: Yeah, yeah, ya got Big Apple Insurance",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
        return None

    return None

async def generate_audio_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = context.user_data["text"]
    instructions = context.user_data["feeling"]
    output_file = f"output_{uuid4()}.mp3"

    try:
        status_message = await update.message.reply_text("در حال آنالیز متن 🔍")
        await asyncio.sleep(1.5)
        await status_message.edit_text("درحال تولید صدا 🎙")
        
        progress_duration = 4
        step_duration = progress_duration / 20
        
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
        
        await status_message.edit_text("تولید صدا در حال انجام است...")
        
    except Exception as e:
        logger.error(f"خطا در ارسال یا به‌روزرسانی پیام وضعیت برای کاربر {user_id}: {str(e)}")
        await update.message.reply_text(
            "خطا در شروع تولید صدا. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )
        return None
    
    success = generate_audio(text, instructions, output_file)
    
    if success:
        try:
            with open(output_file, "rb") as audio:
                await update.message.reply_audio(
                    audio=audio,
                    caption="صدا تولید شد!",
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
                "❌ خطا در تولید صدا. لطفاً مطمئن شوید حس (حداکثر 500 کاراکتر) و متن (حداکثر 1000 کاراکتر) مناسب هستند."
            )
        except Exception:
            logger.warning(f"ناتوانی در به‌روزرسانی پیام وضعیت برای کاربر {user_id}")
    
    context.user_data.clear()
    context.user_data["state"] = "home"
    keyboard = [["🎙 تبدیل متن به صدا", "🤖 دستیار هوشمند"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "به صفحه اصلی بازگشتید. لطفاً یک گزینه انتخاب کنید:",
        reply_markup=reply_markup
    )
    return None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "خطایی رخ داد. لطفاً دوباره امتحان کنید.",
            reply_markup=ReplyKeyboardMarkup([["🔙 برگشت"]], resize_keyboard=True)
        )

# تنظیم ربات
application = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(CallbackQueryHandler(receive_voice))
application.add_error_handler(error_handler)

# تعریف endpoint برای webhook
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

if __name__ == "__main__":
    try:
        asyncio.run(main())
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error(f"خطا در اجرای برنامه: {str(e)}")
    finally:
        try:
            if application.running:
                logger.info("توقف ربات")
                asyncio.run(application.bot.delete_webhook())
                asyncio.run(application.stop())
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {str(e)}")
