import requests
import urllib.parse
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
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
import uvicorn

# تنظیم لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات ربات
TOKEN = "7520523575:AAHNy73MjTRmatJejA96BlaNu0hGHczfYvk"
WEBHOOK_URL = "https://tts-qroo.onrender.com/webhook"
MAX_TEXT_LENGTH = 1000
MAX_FEELING_LENGTH = 500

# لیست صداهای پشتیبانی‌شده
SUPPORTED_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer",
    "coral", "verse", "ballad", "ash", "sage", "amuch", "dan", "elan"
]

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
    filled = percentage // 5
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
    user_id = update.effective_user.id
    text = update.message.text

    if text == "🎙 تبدیل متن به صدا":
        try:
            keyboard = [
                ["✍️ لحن و حس دستی"],
                ["📢 لحن‌های کاربردی", "👑 لحن‌های نمایشی / شخصیتی"],
                ["🎤 لحن‌های گفتاری", "🎭 لحن‌های احساسی"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "🎙 شما به بخش انتخاب لحن و حس منتقل شدید!\n\n"
                "لطفاً یکی از دسته‌بندی‌های زیر را انتخاب کنید یا حس را به‌صورت دستی وارد کنید:",
                reply_markup=reply_markup
            )
            context.user_data["state"] = "select_tone_category"
            return None
        except Exception as e:
            logger.error(f"خطا در نمایش منوی لحن‌ها برای کاربر {user_id}: {str(e)}")
            return None

    if "state" in context.user_data:
        # انتخاب دسته‌بندی لحن
        if context.user_data["state"] == "select_tone_category":
            category_map = {
                "✍️ لحن و حس دستی": "manual_feeling",
                "📢 لحن‌های کاربردی": "functional",
                "👑 لحن‌های نمایشی / شخصیتی": "character_affects",
                "🎤 لحن‌های گفتاری": "voice_styles",
                "🎭 لحن‌های احساسی": "emotional"
            }
            if text in category_map:
                if text == "✍️ لحن و حس دستی":
                    context.user_data["state"] = "manual_feeling"
                    await update.message.reply_text(
                        "لطفاً حس یا دستورالعمل‌های صدا رو وارد کنید (حداکثر 500 کاراکتر).\n"
                        "مثال: Dramatic یا Gruff, fast-talking, New York accent",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return None
                else:
                    category = category_map[text]
                    tones = TONES[category]
                    keyboard = []
                    for i in range(0, len(tones), 2):
                        row = [f"{tones[i]['emoji']} {tones[i]['name']}"]
                        if i + 1 < len(tones):
                            row.append(f"{tones[i+1]['emoji']} {tones[i+1]['name']}")
                        keyboard.append(row)
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    category_names = {
                        "emotional": "لحن‌های احساسی",
                        "voice_styles": "لحن‌های گفتاری",
                        "character_affects": "لحن‌های نمایشی / شخصیتی",
                        "functional": "لحن‌های کاربردی"
                    }
                    await update.message.reply_text(
                        f"🎙 {category_names[category]}\n\nلطفاً یکی از حس‌های زیر را انتخاب کنید:",
                        reply_markup=reply_markup
                    )
                    context.user_data["state"] = "select_tone"
                    context.user_data["selected_category"] = category
                    return None

        # انتخاب حس
        elif context.user_data["state"] == "select_tone":
            category = context.user_data.get("selected_category")
            tones = TONES[category]
            # حذف ایموجی از متن ورودی برای تطبیق
            tone_name = text
            for tone in tones:
                if f"{tone['emoji']} {tone['name']}" == text:
                    tone_name = tone["name"]
                    context.user_data["feeling"] = tone["prompt"]
                    context.user_data["state"] = "text"
                    await update.message.reply_text(
                        "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\n"
                        "مثال: Yeah, yeah, ya got Big Apple Insurance",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return None
            await update.message.reply_text(
                "لطفاً یک حس معتبر از لیست انتخاب کنید."
            )
            return None

        # دریافت حس دستی
        elif context.user_data["state"] == "manual_feeling":
            feeling = text
            if len(feeling) > MAX_FEELING_LENGTH:
                await update.message.reply_text(
                    f"خطا: حس شما {len(feeling)} کاراکتر است. لطفاً حسی با حداکثر {MAX_FEELING_LENGTH} کاراکتر وارد کنید."
                )
                return None
            context.user_data["feeling"] = feeling
            context.user_data["state"] = "text"
            await update.message.reply_text(
                "حالا متن موردنظر برای تبدیل به صدا رو وارد کنید (حداکثر 1000 کاراکتر).\n"
                "مثال: Yeah, yeah, ya got Big Apple Insurance",
                reply_markup=ReplyKeyboardRemove()
            )
            return None
        
        # دریافت متن
        elif context.user_data["state"] == "text":
            if len(text) > MAX_TEXT_LENGTH:
                await update.message.reply_text(
                    f"خطا: متن شما {len(text)} کاراکتر است. لطفاً متنی با حداکثر {MAX_TEXT_LENGTH} کاراکتر وارد کنید."
                )
                return None
            context.user_data["text"] = text
            context.user_data["state"] = "voice"
            keyboard = []
            row = []
            for voice in SUPPORTED_VOICES:
                row.append(voice.capitalize())
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
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
                    "لطفاً یک صدای معتبر از لیست انتخاب کنید."
                )
                return None
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
                    "خطا در شروع تولید صدا. لطفاً دوباره امتحان کنید."
                )
                return None
            
            success = generate_audio(text, instructions, voice, output_file)
            
            if success:
                try:
                    with open(output_file, "rb") as audio:
                        await update.message.reply_audio(
                            audio=audio,
                            caption=f"صدا: {voice.capitalize()}",
                            title="Generated Audio",
                            reply_markup=ReplyKeyboardRemove()
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
    
    return None

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"دریافت دستور /cancel از کاربر: {user_id}")
    try:
        await update.message.reply_text(
            "عملیات لغو شد. با /start می‌تونید دوباره شروع کنید.",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پاسخ /cancel برای کاربر {user_id}: {str(e)}")
    context.user_data.clear()
    return None

application = Application.builder().token(TOKEN).read_timeout(60).write_timeout(60).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(CommandHandler("cancel", cancel))

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
