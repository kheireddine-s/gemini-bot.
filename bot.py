# -*- coding: utf-8 -*-
"""AI
💎 Premium AI Friend Bot — Powered by Gemini
Features: Image analysis · Video description & translation · Voice transcription
          · Document analysis · Force-subscribe · Admin panel · Short-term memory
"""

import os
import telebot
import google.generativeai as genai
import time
import threading
import logging
import tempfile
from keep_alive import keep_alive

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from keep_alive import keep_alive

# ── Start keep-alive server immediately ──────────────────────────────────────
keep_alive()

# ── UTF-8 stdout/stderr ───────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set.")

ADMIN_ID = 7159825566
CHANNEL_USERNAME = "@GeminiDzNet"
CHANNEL_LINK = "https://t.me/GeminiDzNet"
USERS_FILE = "users.txt"
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB (Telegram Bot API limit)
MAX_HISTORY = 10  # 5 exchanges (5 user + 5 model)

# ── Gemini client ─────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = (
    "أنت مساعد ذكي ودود وذكي جداً داخل بوت تيليجرام. "
    "تتحدث بأسلوب دافئ وودي ومشجع باللغة العربية الفصحى البسيطة. "
    "إذا تحدث المستخدم بالإنجليزية، أجب بالإنجليزية. "
    "إذا تحدث بالعربية، أجب بالعربية. "
    "اجعل ردودك واضحة ومفيدة وموجزة. "
    "لا تستخدم تنسيق markdown — استخدم نصاً عادياً فقط."
)

IMAGE_PROMPT = """✨ حلّل هذه الصورة بعناية وقدِّم الآتي:

📝 الوصف الكامل:
صف ما تراه في الصورة بشكل مفصّل ودقيق.

🔍 التفاصيل المهمة:
أشخاص، أشياء، نصوص، ألوان، مكان، أي تفاصيل لافتة.

💡 الاستنتاج:
ما الرسالة أو الفكرة الرئيسية لهذه الصورة؟

استخدم أسلوباً ودياً ونصاً عادياً بدون تنسيق."""

VIDEO_PROMPT = """🎬 حلّل هذا الفيديو وقدِّم الآتي بالترتيب:

1. وصف الفيديو:
اذكر ما يحدث في الفيديو، الأشخاص، الأشياء، المكان، والأحداث بترتيب زمني.

2. النص الأصلي بالإنجليزية (إن وجد كلام):
اكتب النص الكامل لكل ما يُقال كما هو بالضبط. إذا لم يكن هناك كلام، اكتب: لا يوجد كلام في الفيديو.

3. الترجمة إلى العربية:
ترجم النص الإنجليزي أعلاه ترجمةً دقيقة. إذا لم يكن هناك كلام، اكتب: لا توجد ترجمة.

استخدم نصاً عادياً بدون تنسيق."""

VOICE_PROMPT = """🎙️ حلّل هذا التسجيل الصوتي وقدِّم الآتي:

1. النص الأصلي:
اكتب كل ما يُقال بالضبط بأي لغة كانت. إذا لم يكن هناك كلام واضح، اكتب: لا يوجد كلام واضح.

2. الترجمة إلى العربية:
ترجم النص إلى العربية. إذا كان النص عربياً أصلاً، اكتب: النص بالعربية بالفعل.

استخدم نصاً عادياً بدون تنسيق."""

DOCUMENT_PROMPT = """📄 حلّل هذا المستند وقدِّم الآتي:

1. موضوع المستند:
ما الموضوع الرئيسي أو الغرض منه؟

2. ملخص المحتوى:
ملخص شامل لأهم المعلومات والنقاط.

3. النقاط الرئيسية:
أبرز الاستنتاجات والتوصيات إن وجدت.

الرجاء الرد بالعربية ونص عادي بدون تنسيق."""

# ── MIME type routing ─────────────────────────────────────────────────────────
VIDEO_MIMES = {
    "video/mp4",
    "video/mpeg",
    "video/mov",
    "video/avi",
    "video/x-flv",
    "video/mpg",
    "video/webm",
    "video/wmv",
    "video/3gpp",
    "video/quicktime",
}
AUDIO_MIMES = {
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/wav",
    "audio/webm",
    "audio/aac",
    "audio/flac",
    "audio/x-m4a",
}
DOCUMENT_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/html",
    "text/csv",
    "text/xml",
    "application/rtf",
}

# ── State ─────────────────────────────────────────────────────────────────────
user_histories: dict[int, list[types.Content]] = {}
users_lock = threading.Lock()
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ── Static UI strings ─────────────────────────────────────────────────────────
WELCOME_MSG = (
    "✨ أهلاً وسهلاً {name}! 💎\n\n"
    "أنا صديقك الذكي المدعوم بتقنية Gemini 🤖\n\n"
    "🌟 ما يمكنني فعله:\n"
    "📸 تحليل الصور وحل المسائل البصرية\n"
    "🎬 وصف الفيديوهات + ترجمة الكلام إلى عربي\n"
    "🎙️ نقل وترجمة الرسائل الصوتية\n"
    "📄 تحليل وتلخيص PDF والمستندات\n"
    "💬 الدردشة الذكية بالعربية والإنجليزية\n"
    "🧠 تذكّر آخر 5 رسائل في المحادثة\n\n"
    "📦 الحجم الأقصى للملفات: 20 ميجابايت\n\n"
    "ابدأ بإرسال أي رسالة أو ملف! 🚀"
)

SUBSCRIBE_MSG = (
    "🔒 عذراً، يجب عليك الانضمام إلى قناتنا أولاً!\n\n"
    "📢 القناة: {channel}\n\n"
    "بعد الانضمام، اضغط على ✅ تحقق من الاشتراك"
).format(channel=CHANNEL_LINK)

HELP_TEXT = (
    "🛠️ دليل الاستخدام — Premium AI Friend Bot\n\n"
    "💬 نص — أكتب لي أي شيء وسأجيبك ذكياً\n"
    "📸 صورة — أرسل صورة وسأحللها أو أجيب عن سؤالك عنها\n"
    "🎬 فيديو — سأصفه وأk�رجم الكلام الإنجليزي فيه\n"
    "🎙️ رسالة صوتية — سأنقل الكلام وأترجمه للعربية\n"
    "📄 ملف PDF أو Word — سأقرأه وألخصه لك\n"
    "🧠 ذاكرة قصيرة — أتذكر آخر 5 رسائل لكل جلسة\n\n"
    "🔧 الأوامر:\n"
    "/start — رسالة الترحيب والقائمة\n"
    "/help  — هذه الرسالة\n"
    "/reset — مسح سجل المحادثة\n\n"
    "📦 الحجم الأقصى للملفات: 20 ميجابايت\n\n"
    "💡 نصيحة: عند إرسال صورة، أضف سؤالك كتعليق وسأجيب عنه!"
)

ABOUT_TEXT = (
    "🤖 عن الذكاء الاصطناعي\n\n"
    "أنا مدعوم بتقنية Gemini 2.5 Flash من Google 🌟\n"
    "واحد من أقوى نماذج الذكاء الاصطناعي في العالم!\n\n"
    "🧬 قدراتي:\n"
    "🧠 فهم السياق والمحادثات المعقدة\n"
    "📸 رؤية وتحليل الصور بدقة عالية\n"
    "🎬 معالجة وفهم مقاطع الفيديو\n"
    "🎙️ نقل الكلام وترجمته\n"
    "📄 قراءة المستندات وتلخيصها\n"
    "🌐 التحدث بالعربية والإنجليزية بطلاقة\n\n"
    "🔬 النموذج: Gemini 2.5 Flash\n"
    "🏢 المطوّر: Google DeepMind\n"
    "💡 الإصدار: 2025\n\n"
    "أنا هنا لمساعدتك في كل شيء! 💎"
)

PROCESSING_MSG = "⏳ جارٍ المعالجة، يرجى الانتظار… 🔄"
FILE_TOO_LARGE = (
    "⚠️ الملف كبير جداً! الحد الأقصى هو 20 ميجابايت.\n📦 يرجى إرسال ملف أصغر حجماً."
)
FILE_FAILED = "⚠️ تعذّرت معالجة هذا الملف. يرجى تجربة ملف آخر."
ERROR_MSG = "⚠️ حدث خطأ ما. يرجى المحاولة مرة أخرى! 🔄"
NO_RESPONSE_MSG = "⚠️ لم أتمكن من توليد رد. يرجى المحاولة مرة أخرى."
RESET_MSG = "✅ تم مسح سجل المحادثة!\nابدأ محادثة جديدة الآن 🌟"
UNSUPPORTED_DOC = (
    "⚠️ نوع الملف غير مدعوم.\n\n"
    "📋 الأنواع المدعومة:\n"
    "📸 صور · 🎬 فيديو · 🎙️ صوت · 📄 PDF · Word · Excel · TXT"
)
NOT_ADMIN_MSG = "⛔ هذا الأمر متاح للمشرف فقط."


# ── Keyboards ─────────────────────────────────────────────────────────────────


def subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 انضم للقناة الآن", url=CHANNEL_LINK))
    kb.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="verify"))
    return kb


def main_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🔗 القناة", url=CHANNEL_LINK),
        InlineKeyboardButton("🛠️ المساعدة", callback_data="help_menu"),
    )
    kb.add(InlineKeyboardButton("🤖 عن الذكاء الاصطناعي", callback_data="about"))
    return kb


def back_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu"))
    return kb


# ── User management ───────────────────────────────────────────────────────────


def load_users() -> set:
    with users_lock:
        if not os.path.exists(USERS_FILE):
            return set()
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}


def save_user(user_id: int) -> None:
    uid = str(user_id)
    with users_lock:
        existing = set()
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                existing = {line.strip() for line in f if line.strip()}
        if uid not in existing:
            with open(USERS_FILE, "a", encoding="utf-8") as f:
                f.write(uid + "\n")


# ── Subscription check ────────────────────────────────────────────────────────


def is_subscribed(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


def check_and_register(message: telebot.types.Message) -> bool:
    """Save user, verify subscription. Returns True if user may proceed."""
    user_id = message.from_user.id
    save_user(user_id)
    if is_subscribed(user_id):
        return True
    bot.reply_to(message, SUBSCRIBE_MSG, reply_markup=subscribe_keyboard())
    return False


# ── Conversation memory ───────────────────────────────────────────────────────


def get_history(user_id: int) -> list[types.Content]:
    return user_histories.setdefault(user_id, [])


def trim_history(history: list[types.Content]) -> None:
    if len(history) > MAX_HISTORY:
        del history[: len(history) - MAX_HISTORY]


# ── File utilities ────────────────────────────────────────────────────────────


def download_telegram_file(file_id: str) -> bytes:
    info = bot.get_file(file_id)
    return bot.download_file(info.file_path)


def upload_to_gemini(
    file_bytes: bytes, mime_type: str, display_name: str
) -> genai.types.File:
    ext = mime_type.split("/")[-1].split(";")[0]
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        return client.files.upload(
            file=tmp_path,
            config=types.UploadFileConfig(
                mime_type=mime_type, display_name=display_name
            ),
        )
    finally:
        os.unlink(tmp_path)


def wait_for_file_active(
    gemini_file: genai.types.File, timeout: int = 120
) -> genai.types.File:
    deadline = time.time() + timeout
    while gemini_file.state.name == "PROCESSING":
        if time.time() > deadline:
            raise TimeoutError("Gemini file processing timed out.")
        time.sleep(4)
        gemini_file = client.files.get(name=gemini_file.name)
    if gemini_file.state.name != "ACTIVE":
        raise RuntimeError(f"File state: {gemini_file.state.name}")
    return gemini_file


def format_response(icon: str, title: str, content: str) -> str:
    return f"{icon} {title}\n\n{content}\n\n{'─' * 20}\n💎 مدعوم بـ Gemini AI"


def process_file_with_gemini(
    message: telebot.types.Message,
    file_id: str,
    mime_type: str,
    prompt: str,
    icon: str,
    title: str,
    label: str,
) -> None:
    user_id = message.from_user.id
    bot.reply_to(message, PROCESSING_MSG)
    bot.send_chat_action(message.chat.id, "typing")
    gemini_file = None
    try:
        file_bytes = download_telegram_file(file_id)
        gemini_file = upload_to_gemini(file_bytes, mime_type, f"{label}_{user_id}")
        logger.info("Uploaded %s for user %d → %s", label, user_id, gemini_file.name)
        gemini_file = wait_for_file_active(gemini_file)
        response = client.models.generate_content(
            model=MODEL,
            contents=[gemini_file, prompt],
            config=types.GenerateContentConfig(max_output_tokens=8192),
        )
        reply_text = (response.text or "").strip() or NO_RESPONSE_MSG
        bot.reply_to(
            message,
            format_response(icon, title, reply_text),
            reply_markup=back_keyboard(),
        )
        logger.info("%s done for user %d.", label, user_id)
    except Exception as e:
        logger.error("Error processing %s for user %d: %s", label, user_id, e)
        bot.reply_to(message, FILE_FAILED)
    finally:
        if gemini_file is not None:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                pass


# ── Command handlers ──────────────────────────────────────────────────────────


@bot.message_handler(commands=["start"])
def handle_start(message: telebot.types.Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "صديقي"
    save_user(user_id)

    if not is_subscribed(user_id):
        bot.reply_to(message, SUBSCRIBE_MSG, reply_markup=subscribe_keyboard())
        return

    bot.reply_to(
        message,
        WELCOME_MSG.format(name=user_name),
        reply_markup=main_menu_keyboard(),
    )


@bot.message_handler(commands=["help"])
def handle_help(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return
    bot.reply_to(message, HELP_TEXT, reply_markup=main_menu_keyboard())


@bot.message_handler(commands=["reset"])
def handle_reset(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return
    user_histories.pop(message.from_user.id, None)
    bot.reply_to(message, RESET_MSG, reply_markup=main_menu_keyboard())


@bot.message_handler(commands=["users"])
def handle_users(message: telebot.types.Message) -> None:
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, NOT_ADMIN_MSG)
        return
    users = load_users()
    bot.reply_to(
        message,
        f"🛡️ لوحة المشرف\n\n👥 إجمالي المستخدمين: {len(users)}\n📁 الملف: {USERS_FILE}",
    )


@bot.message_handler(commands=["broadcast"])
def handle_broadcast(message: telebot.types.Message) -> None:
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, NOT_ADMIN_MSG)
        return

    parts = message.text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "📢 الاستخدام:\n/broadcast <رسالتك هنا>")
        return

    broadcast_text = parts[1].strip()
    users = load_users()

    if not users:
        bot.reply_to(message, "⚠️ لا يوجد مستخدمون مسجّلون بعد.")
        return

    bot.reply_to(message, f"📡 جارٍ الإرسال إلى {len(users)} مستخدم…")
    sent = failed = 0

    for uid_str in users:
        try:
            bot.send_message(
                int(uid_str),
                f"📢 إعلان من المشرف:\n\n{broadcast_text}",
            )
            sent += 1
            time.sleep(0.05)  # rate-limit courtesy
        except Exception:
            failed += 1

    bot.reply_to(
        message,
        f"✅ اكتمل البث!\n📬 نجح: {sent}\n❌ فشل: {failed}",
    )


# ── Callback query handler ────────────────────────────────────────────────────


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: telebot.types.CallbackQuery) -> None:
    user_id = call.from_user.id
    user_name = call.from_user.first_name or "صديقي"
    data = call.data

    if data == "verify":
        save_user(user_id)
        if is_subscribed(user_id):
            bot.answer_callback_query(call.id, "✅ تم التحقق! أهلاً بك 🎉")
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=WELCOME_MSG.format(name=user_name),
                    reply_markup=main_menu_keyboard(),
                )
            except Exception:
                bot.send_message(
                    call.message.chat.id,
                    WELCOME_MSG.format(name=user_name),
                    reply_markup=main_menu_keyboard(),
                )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ لم تنضم بعد! انضم ثم اضغط تحقق.",
                show_alert=True,
            )

    elif data == "help_menu":
        if not is_subscribed(user_id) and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "🔒 اشترك أولاً!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id, HELP_TEXT, reply_markup=main_menu_keyboard()
        )

    elif data == "about":
        if not is_subscribed(user_id) and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "🔒 اشترك أولاً!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id, ABOUT_TEXT, reply_markup=main_menu_keyboard()
        )

    elif data == "menu":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            "🏠 القائمة الرئيسية:",
            reply_markup=main_menu_keyboard(),
        )


# ── Photo handler ─────────────────────────────────────────────────────────────


@bot.message_handler(content_types=["photo"])
def handle_photo(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return

    user_id = message.from_user.id
    caption = message.caption  # User's question about the image (optional)

    bot.reply_to(message, PROCESSING_MSG)
    bot.send_chat_action(message.chat.id, "typing")

    try:
        photo = message.photo[-1]  # Highest resolution
        file_bytes = download_telegram_file(photo.file_id)
        prompt = caption if caption else IMAGE_PROMPT

        response = client.models.generate_content(
            model=MODEL,
            contents=types.Content(
                parts=[
                    types.Part(
                        inline_data=types.Blob(data=file_bytes, mime_type="image/jpeg")
                    ),
                    types.Part(text=prompt),
                ]
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=8192,
            ),
        )

        reply_text = (response.text or "").strip() or NO_RESPONSE_MSG
        bot.reply_to(
            message,
            format_response("📸", "تحليل الصورة", reply_text),
            reply_markup=back_keyboard(),
        )
        logger.info("Photo analyzed for user %d.", user_id)

    except Exception as e:
        logger.error("Error analyzing photo for user %d: %s", user_id, e)
        bot.reply_to(message, ERROR_MSG)


# ── Voice / Audio handler ─────────────────────────────────────────────────────


@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return

    user_id = message.from_user.id
    if message.content_type == "voice":
        media = message.voice
        mime_type = media.mime_type or "audio/ogg"
    else:
        media = message.audio
        mime_type = media.mime_type or "audio/mpeg"

    if (media.file_size or 0) > MAX_FILE_BYTES:
        bot.reply_to(message, FILE_TOO_LARGE)
        return

    logger.info("Voice from user %d — mime: %s", user_id, mime_type)
    process_file_with_gemini(
        message,
        media.file_id,
        mime_type,
        VOICE_PROMPT,
        "🎙️",
        "تحليل الرسالة الصوتية",
        "voice",
    )


# ── Video handler ─────────────────────────────────────────────────────────────


@bot.message_handler(content_types=["video"])
def handle_video(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return

    user_id = message.from_user.id
    media = message.video
    mime_type = media.mime_type or "video/mp4"

    if (media.file_size or 0) > MAX_FILE_BYTES:
        bot.reply_to(message, FILE_TOO_LARGE)
        return

    logger.info("Video from user %d — mime: %s", user_id, mime_type)
    process_file_with_gemini(
        message,
        media.file_id,
        mime_type,
        VIDEO_PROMPT,
        "🎬",
        "تحليل الفيديو",
        "video",
    )


# ── Document handler ──────────────────────────────────────────────────────────


@bot.message_handler(content_types=["document"])
def handle_document(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return

    user_id = message.from_user.id
    doc = message.document
    mime_type = (doc.mime_type or "").lower()
    file_size = doc.file_size or 0

    if file_size > MAX_FILE_BYTES:
        bot.reply_to(message, FILE_TOO_LARGE)
        return

    if mime_type in VIDEO_MIMES or mime_type.startswith("video/"):
        prompt, icon, title, label = VIDEO_PROMPT, "🎬", "تحليل الفيديو", "video_doc"
    elif mime_type in AUDIO_MIMES or mime_type.startswith("audio/"):
        prompt, icon, title, label = VOICE_PROMPT, "🎙️", "تحليل الصوت", "audio_doc"
    elif mime_type in DOCUMENT_MIMES or mime_type.startswith("text/"):
        prompt, icon, title, label = DOCUMENT_PROMPT, "📄", "تحليل المستند", "document"
    else:
        bot.reply_to(message, UNSUPPORTED_DOC)
        return

    logger.info("Document from user %d — mime: %s", user_id, mime_type)
    process_file_with_gemini(
        message, doc.file_id, mime_type, prompt, icon, title, label
    )


# ── Text handler ──────────────────────────────────────────────────────────────


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message: telebot.types.Message) -> None:
    if not check_and_register(message):
        return

    user_id = message.from_user.id
    user_text = message.text

    if not user_text or not user_text.strip():
        return

    safe = user_text[:80].encode("utf-8", errors="replace").decode("utf-8")
    logger.info("Text from user %d: %s", user_id, safe)

    try:
        bot.send_chat_action(message.chat.id, "typing")

        history = get_history(user_id)
        history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

        response = client.models.generate_content(
            model=MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=8192,
            ),
        )

        reply_text = (response.text or "").strip() or NO_RESPONSE_MSG
        history.append(types.Content(role="model", parts=[types.Part(text=reply_text)]))
        trim_history(history)

        bot.reply_to(message, reply_text)
        logger.info("Replied to user %d.", user_id)

    except Exception as e:
        logger.error("Error for user %d: %s", user_id, e)
        bot.reply_to(message, ERROR_MSG)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keep_alive()
    logger.info("🚀 Starting Premium AI Friend Bot (model: %s)…", MODEL)
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
