import re
from datetime import datetime, timedelta, date
import threading
import html
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 توكن البوت الخاص بك
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# ================= إعدادات المالك والقناة =================
OWNER_ID = 7454358135                 # آيدي المالك (يتم التعرف عليه تلقائياً في الخاص)
LEAK_CHANNEL_ID = -1003335103713      # آيدي قناة التسريبات التي يأخذ منها البوت تلقائياً

# ================= قواعد البيانات المؤقتة (في الذاكرة) =================
# ملاحظة هامة: كل هذه البيانات مخزنة في الذاكرة فقط، إذا أعدت تشغيل البوت ستُمسح.
# إذا أردت حفظها بشكل دائم يفضل استخدام قاعدة بيانات (SQLite / JSON file) لاحقاً.

ratings_data = {}
user_xp = {}
tournaments = {}
user_violations = {}

# 📨 سجلّ كل رسائل المجموعة (لأجل ميزة الحذف التلقائي عند 1000 رسالة)
group_message_log = {}          # {chat_id: [message_id, message_id, ...]}

# 🐢 نظام مكافحة السبام (5 ثواني بين كل رسالة وأخرى)
last_message_time = {}          # {user_id: datetime}
FLOOD_WAIT_SECONDS = 5

# 🕒 حذف رسائل البوت تلقائياً بعد 3 دقائق (إلا المثبتة)
BOT_MESSAGE_LIFETIME = 180

# 📰 التسريبات: كل مجموعة عندها قائمة تسريبات خاصة بها
# {chat_id: [ {"text":..., "photo":...}, ... ]}
news_store = {}

# 👑 عند تفعيل وضع "إضافة تسريبات" من الخاص، نحتاج لمعرفة أي مجموعة يقصدها المالك
owner_target_group = {}         # {OWNER_ID: chat_id}

# 📡 تتبع آخر يوم أضاف فيه المالك تسريباً يدوياً (لتفادي التكرار مع تسريبات القناة)
last_owner_leak_date = None

# ================= دوال المساعدة =================
def delete_message_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def add_xp(user_id, name, amount):
    if user_id not in user_xp:
        user_xp[user_id] = {"name": name, "xp": 0}
    user_xp[user_id]["xp"] += amount

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception:
        return False

def is_owner(user_id):
    return user_id == OWNER_ID

def is_pinned(chat_id, message_id):
    """يتحقق هل هذه الرسالة هي الرسالة المثبتة حالياً في المحادثة"""
    try:
        chat = bot.get_chat(chat_id)
        pinned = chat.pinned_message
        return bool(pinned and pinned.message_id == message_id)
    except Exception:
        return False

def schedule_bot_message_delete(chat_id, message_id, delay=BOT_MESSAGE_LIFETIME):
    """يجدول حذف رسالة أرسلها البوت بعد مدة معينة، إلا إذا كانت مثبتة"""
    def _job():
        if is_pinned(chat_id, message_id):
            return
        delete_message_safe(chat_id, message_id)
    threading.Timer(delay, _job).start()

def track_bot_message(chat_id, msg, chat_type=None, delay=BOT_MESSAGE_LIFETIME):
    """يسجّل رسالة البوت ضمن سجل المجموعة (لحساب الـ1000 رسالة) ويجدول حذفها بعد 3 دقائق"""
    if msg is None:
        return
    if chat_type is None:
        chat_type = "group"
    if chat_type != 'private':
        log_group_message(chat_id, msg.message_id)
        schedule_bot_message_delete(chat_id, msg.message_id, delay)
    return msg

def log_group_message(chat_id, message_id):
    """يسجّل أي رسالة (من عضو أو من البوت) في سجل المجموعة، ويفرغ المجموعة عند الوصول لـ1000"""
    group_message_log.setdefault(chat_id, [])
    group_message_log[chat_id].append(message_id)
    if len(group_message_log[chat_id]) >= 1000:
        clear_group_messages(chat_id)

def clear_group_messages(chat_id):
    """يحذف كل رسائل المجموعة (المالك + الأدمن + الأعضاء العاديين) إلا الرسالة المثبتة"""
    ids = group_message_log.get(chat_id, [])
    pinned_id = None
    try:
        chat = bot.get_chat(chat_id)
        if chat.pinned_message:
            pinned_id = chat.pinned_message.message_id
    except Exception:
        pass

    for mid in ids:
        if pinned_id and mid == pinned_id:
            continue
        delete_message_safe(chat_id, mid)

    group_message_log[chat_id] = []
    try:
        notice = bot.send_message(chat_id, "🧹 <b>تم تنظيف المجموعة تلقائياً بعد الوصول إلى 1000 رسالة!</b>\nتم الاحتفاظ بالرسالة المثبتة فقط.", parse_mode="HTML")
        track_bot_message(chat_id, notice)
    except Exception:
        pass

# 🚫 لائحة الكلمات البذيئة الشاملة
BAD_WORDS = [
    "قحب", "قحبة", "تبة", "زمل", "زملي", "زامل", "حاوي", "منيوك", "مك", "مكك", "اختك", "موك",
    "تيك", "زبي", "زب", "قلاوي", "قلوة", "طاسيلتك", "عصيد", "كحاب", "ميكة", "بزول", "طرمة",
    "كلب", "حمار", "وسخ", "منحط", "حقير", "لعنة", "ابن الحرام", "ساقط", "متخلف", "قذر",
    "fuck", "fucking", "shit", "bitch", "asshole", "dick", "cunt", "bastard", "slut", "whore",
    "idiot", "motherfucker", "pussy", "crap", "suck",
    "putain", "merde", "connard", "connasse", "salope", "enculé", "nique", "bite", "fdp", "pute"
]

# ================= لوحات الأزرار =================
def create_rating_markup():
    markup = InlineKeyboardMarkup(row_width=5)
    markup.add(
        InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
        InlineKeyboardButton("⭐ 2", callback_data="rate_2"),
        InlineKeyboardButton("⭐ 3", callback_data="rate_3"),
        InlineKeyboardButton("⭐ 4", callback_data="rate_4"),
        InlineKeyboardButton("⭐ 5", callback_data="rate_5")
    )
    return markup

def create_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔍 بحث عن سكواد", callback_data="menu_squad"),
        InlineKeyboardButton("🔥 آخر التسريبات", callback_data="menu_news"),
        InlineKeyboardButton("🏆 أفضل اللاعبين", callback_data="menu_top"),
        InlineKeyboardButton("📚 موسوعة اللعبة", callback_data="menu_wiki"),
        InlineKeyboardButton("🛡️ دعم المجموعة", url="https://t.me/an_as1209")
    )
    return markup

def create_admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🏆 إنشاء بطولة", callback_data="admin_tour"),
        InlineKeyboardButton("🗑️ حذف الرسالة", callback_data="admin_delete")
    )
    return markup

# ================= 0. تسجيل كل الرسائل (لحساب الـ1000 رسالة) + مكافحة السبام =================
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'], content_types=[
    'text', 'photo', 'video', 'document', 'sticker', 'voice', 'audio', 'animation', 'video_note'
])
def track_all_group_messages(message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else None
    text_or_caption = message.text or message.caption or ""

    # تسجيل الرسالة ضمن سجل المجموعة (لحساب الـ1000 رسالة لاحقاً)
    log_group_message(chat_id, message.message_id)

    # مكافحة السبام: لا تُطبَّق على الأوامر ولا على الأدمن
    if user_id and not text_or_caption.strip().startswith('/') and not is_admin(chat_id, user_id):
        now = datetime.now()
        last_time = last_message_time.get(user_id)
        if last_time and (now - last_time).total_seconds() < FLOOD_WAIT_SECONDS:
            delete_message_safe(chat_id, message.message_id)
            return
        last_message_time[user_id] = now

# ================= 1. نظام العقوبات الذكي (بدون تعطيل الأوامر) =================
def is_bad_message(message):
    text_to_check = message.text or message.caption
    if not text_to_check:
        return False
    # عدم معاقبة الأوامر وعدم تعطيلها
    if text_to_check.strip().startswith('/'):
        return False
    # الإدمنز مستثنون
    if is_admin(message.chat.id, message.from_user.id):
        return False

    text_lower = text_to_check.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

@bot.message_handler(func=is_bad_message, content_types=['text', 'photo', 'video'])
def filter_bad_words(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = html.escape(message.from_user.first_name)

    delete_message_safe(chat_id, message.message_id)

    if user_id not in user_violations:
        user_violations[user_id] = 0
    user_violations[user_id] += 1
    violation_count = user_violations[user_id]

    try:
        if violation_count == 1:
            msg = bot.send_message(
                chat_id,
                f"⚠️ <b>تـحـذيـر رسـمـي !</b>\n\n👤 العضو: <b>{user_name}</b>\n💬 السبب: استخدام ألفاظ بذيئة.\n📌 <i>هذا تحذيرك الأول!</i>",
                parse_mode="HTML"
            )
            threading.Timer(7.0, delete_message_safe, args=(chat_id, msg.message_id)).start()

        elif violation_count == 2:
            until_time = datetime.now() + timedelta(minutes=5)
            bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
            msg = bot.send_message(
                chat_id,
                f"🔇 <b>عـقـوبـة مـيـوت مـؤقـت !</b>\n\n👤 العضو: <b>{user_name}</b>\n⏳ المدة: <b>5 دقائق</b>",
                parse_mode="HTML"
            )
            threading.Timer(10.0, delete_message_safe, args=(chat_id, msg.message_id)).start()

        elif violation_count == 3:
            until_time = datetime.now() + timedelta(days=1)
            bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
            msg = bot.send_message(chat_id, f"⏳ <b>تـعـليـق مـؤقـت (24 سـاعـة) !</b>\n\n👤 العضو: <b>{user_name}</b>\n⚠️ تم كتمك لمدة يوم كامل.", parse_mode="HTML")
            track_bot_message(chat_id, msg)

        elif violation_count == 4:
            until_time = datetime.now() + timedelta(days=5)
            bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
            msg = bot.send_message(chat_id, f"⛔ <b>حـظـر تـفـاعـل (5 أيـام) !</b>\n\n👤 العضو: <b>{user_name}</b>\n🚨 تم منعك من الكتابة لمدة 5 أيام.", parse_mode="HTML")
            track_bot_message(chat_id, msg)

        else:
            bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
            apology_text = f"السلام عليكم مالك المجموعة، أنا العضو {user_name} وأتأسف على صدور الألفاظ البذيئة مني، أرجو أن تسامحني وتفك عني الميوت وشكراً لك."
            encoded_text = apology_text.replace(" ", "%20").replace("\n", "%0A")
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛡️ تواصل مع المالك للإعتذار", url=f"https://t.me/an_as1209?text={encoded_text}"))
            msg = bot.send_message(
                chat_id,
                f"🔒 <b>تـم كـتـم الـعـضـو مـدى الـحـيـاة !</b>\n\n👤 العضو: <b>{user_name}</b>\n❌ تم إسكاتك نهائياً. اضغط على الزر للاعتذار 👇",
                parse_mode="HTML", reply_markup=markup
            )
            track_bot_message(chat_id, msg)
    except Exception:
        pass

# ================= 2. أوامر الإدارة =================
def resolve_target_user(message):
    """يحاول تحديد آيدي الشخص المطلوب عبر: الرد على رسالته، أو كتابة يوزره، أو كتابة آيدي رقمي"""
    args = message.text.split(maxsplit=1)

    # 1) عبر الرد على رسالة الشخص
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id, message.reply_to_message.from_user.first_name

    # 2) عبر كتابة يوزر أو آيدي بعد الأمر
    if len(args) >= 2:
        target = args[1].strip()
        username = target.lstrip('@')
        try:
            if target.isdigit() or (target.startswith('-') and target[1:].isdigit()):
                chat_info = bot.get_chat(int(target))
            else:
                chat_info = bot.get_chat(f"@{username}")
            return chat_info.id, getattr(chat_info, "first_name", chat_info.username or "العضو")
        except Exception:
            return None, None

    return None, None

@bot.message_handler(commands=['unmute'])
def owner_unmute_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id) and message.chat.type != 'private' and not is_owner(user_id):
        return

    target_id, target_name = resolve_target_user(message)
    if not target_id:
        return bot.reply_to(
            message,
            "⚠️ يرجى تحديد العضو بإحدى الطريقتين:\n"
            "1️⃣ الرد على رسالته وكتابة /unmute\n"
            "2️⃣ كتابة /unmute متبوعة بيوزره، مثال: /unmute @username"
        )

    try:
        target_chat_id = chat_id if message.chat.type != 'private' else (owner_target_group.get(OWNER_ID) or chat_id)
        bot.restrict_chat_member(target_chat_id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        if target_id in user_violations:
            user_violations[target_id] = 0
        owner_name = html.escape(message.from_user.first_name)
        announcement = bot.send_message(
            target_chat_id,
            f"🔓 <b>عـفـو مـلـكـي / فَـك الـحَـظْـر !</b> 🔓\n\n✨ تم بفضل الله رفع عقوبة الميوت عن العضو بناءً على عفو وسامح من المالك <b>{owner_name}</b>.",
            parse_mode="HTML"
        )
        track_bot_message(target_chat_id, announcement, chat_type='group', delay=14400.0)
        bot.reply_to(message, "✅ تم فك الميوت عن العضو بنجاح!")
    except Exception:
        bot.reply_to(message, "❌ حدث خطأ، تأكد أن البوت يملك صلاحيات كاملة.")

@bot.message_handler(commands=['ban', 'mute'])
def admin_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0].lower()

    if not is_admin(chat_id, user_id):
        return
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ يرجى الرد على رسالة الشخص.")

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    try:
        if command == '/ban':
            bot.ban_chat_member(chat_id, target_id)
            bot.reply_to(message, f"⛔ تم طرد <b>{html.escape(target_name)}</b> من المجموعة.", parse_mode="HTML")
        elif command == '/mute':
            bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=False))
            bot.reply_to(message, f"🔇 تم كتم <b>{html.escape(target_name)}</b>.", parse_mode="HTML")
    except Exception:
        pass

# ================= 3. الترحيب والقوائم =================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        welcome_text = f"⚡ <b>أهلاً بك يا أسطورة</b> ⚡\n\n👤 <b>اللاعب:</b> {mention}\n\nاختر من القائمة أدناه لاكتشاف ميزات البوت 👇"
        sent_msg = bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=create_main_menu())
        track_bot_message(message.chat.id, sent_msg, delay=60.0)

@bot.message_handler(commands=['help', 'start', 'menu'])
def send_menu(message):
    # ✨ الترحيب الخاص بالمالك عند مراسلة البوت في الخاص
    if message.chat.type == 'private' and is_owner(message.from_user.id):
        owner_welcome = (
            "👑 <b>أهلاً بك يا مولاي المالك !</b> 👑\n\n"
            "🌟 تشرفت بحضورك، جميع صلاحيات البوت بين يديك الآن.\n\n"
            "📌 <b>أوامرك الخاصة هنا في الخاص:</b>\n"
            "• <code>/setgroup [آيدي المجموعة]</code> — لتحديد المجموعة التي تريد إضافة التسريبات لها\n"
            "• <code>/setnews</code> (بالرد على صورة أو نص) — لإضافة تسريب جديد لتلك المجموعة\n\n"
            "🫡 بانتظار أوامرك في أي وقت!"
        )
        bot.send_message(message.chat.id, owner_welcome, parse_mode="HTML")
        return

    bot.send_message(message.chat.id, "🕹️ <b>قـائـمـة الـتـحـكـم الـرئـيـسـيـة</b> 🕹️\n\nاختر ما تريد من الأزرار أسفله:", parse_mode="HTML", reply_markup=create_main_menu())
    if message.chat.type != 'private' and is_admin(message.chat.id, message.from_user.id):
        bot.send_message(message.chat.id, "⚙️ <b>أوامـر الإدارة (للمشرفين فقط)</b> ⚙️\nيمكنك الرد على أي شخص بـ:\n- <code>/ban</code> (للطرد)\n- <code>/mute</code> (للكتم)\n- <code>/unmute</code> (لإلغاء الكتم)", parse_mode="HTML", reply_markup=create_admin_menu())

# ================= 4. إضافة التسريبات (تدعم عدة تسريبات) =================
def add_news_item(chat_id, text, photo):
    news_store.setdefault(chat_id, [])
    news_store[chat_id].append({"text": text, "photo": photo})

@bot.message_handler(commands=['setnews'])
def set_news_command(message):
    global last_owner_leak_date

    # الحالة 1: الأمر داخل مجموعة (يتطلب صلاحية أدمن)
    if message.chat.type != 'private':
        if not is_admin(message.chat.id, message.from_user.id):
            return
        if not message.reply_to_message:
            return bot.reply_to(message, "⚠️ أرسل الصورة واكتب في الوصف `/setnews`، أو قم بالرد على صورة/نص واكتب الأمر.")

        reply_msg = message.reply_to_message
        if reply_msg.photo:
            add_news_item(message.chat.id, reply_msg.caption or "🔥 تسريب جديد!", reply_msg.photo[-1].file_id)
        else:
            add_news_item(message.chat.id, reply_msg.text or "🔥 تسريب جديد!", None)

        last_owner_leak_date = date.today()
        bot.reply_to(message, "✅ تم حفظ التسريب بنجاح! يمكن للأعضاء رؤيته عبر /news أو زر آخر التسريبات.")
        return

    # الحالة 2: الأمر في الخاص (خاص بالمالك فقط)
    if not is_owner(message.from_user.id):
        return

    target_group = owner_target_group.get(OWNER_ID)
    if not target_group:
        return bot.reply_to(message, "⚠️ يرجى أولاً تحديد المجموعة عبر: /setgroup [آيدي المجموعة]")

    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ قم بالرد على الصورة أو النص الذي تريد حفظه كتسريب، ثم اكتب /setnews.")

    reply_msg = message.reply_to_message
    if reply_msg.photo:
        add_news_item(target_group, reply_msg.caption or "🔥 تسريب جديد!", reply_msg.photo[-1].file_id)
    else:
        add_news_item(target_group, reply_msg.text or "🔥 تسريب جديد!", None)

    last_owner_leak_date = date.today()
    bot.reply_to(message, f"✅ تم حفظ التسريب في قائمة المجموعة (<code>{target_group}</code>) بنجاح!", parse_mode="HTML")

@bot.message_handler(commands=['setgroup'])
def set_group_command(message):
    if message.chat.type != 'private' or not is_owner(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return bot.reply_to(message, "⚠️ اكتب آيدي المجموعة بعد الأمر، مثال:\n/setgroup -1001234567890")
    try:
        target = int(args[1].strip())
    except ValueError:
        return bot.reply_to(message, "❌ آيدي غير صالح، يجب أن يكون رقماً.")

    owner_target_group[OWNER_ID] = target
    bot.reply_to(message, f"✅ تم تحديد المجموعة الهدف: <code>{target}</code>\nيمكنك الآن استخدام /setnews هنا في الخاص وسيتم الحفظ لهذه المجموعة.", parse_mode="HTML")

@bot.message_handler(commands=['news'])
def news_command(message):
    chat_id = message.chat.id
    items = news_store.get(chat_id, [])

    if not items:
        return bot.reply_to(message, "😔 لا توجد تسريبات محفوظة حالياً لهذه المجموعة.")

    for item in items:
        try:
            text = f"🕵️‍♂️ <b>تـسـريـب</b> 🕵️‍♂️\n\n{html.escape(item['text']) if item['text'] else ''}"
            if item["photo"]:
                sent = bot.send_photo(chat_id, item["photo"], caption=text, parse_mode="HTML")
            else:
                sent = bot.send_message(chat_id, text, parse_mode="HTML")
            # تثبيت تلقائي حتى لا يتم حذفه ضمن التنظيف التلقائي
            try:
                bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
            except Exception:
                pass
            log_group_message(chat_id, sent.message_id)
        except Exception:
            continue

# ================= 5. استخراج ونشر الخرائط (تتطلب /map في الوصف) =================
def extract_map_data(caption):
    match = re.search(r"\[(.*?)\]", caption)
    if match:
        map_type = html.escape(match.group(1).strip())
        raw_body = caption.replace(f"[{match.group(1)}]", "").strip()
    else:
        lines = caption.strip().split('\n')
        map_type = html.escape(lines[0].strip()) if lines else "خريطة"
        raw_body = '\n'.join(lines[1:]).strip() if len(lines) > 1 else caption

    map_code = "غير متوفر"
    code_match = re.search(r"(كود[:：]?\s*([A-Za-z0-9#\-_]+))", raw_body, re.IGNORECASE)
    if code_match:
        map_code = html.escape(code_match.group(2).strip())
        description = html.escape(raw_body.replace(code_match.group(1), "").strip())
    else:
        hash_match = re.search(r"([A-Za-z0-9]*FREEFIRE[A-Za-z0-9#\-_]+)", raw_body, re.IGNORECASE)
        if hash_match:
            map_code = html.escape(hash_match.group(1).strip())
            description = html.escape(raw_body.replace(hash_match.group(1), "").strip())
        else:
            description = html.escape(raw_body)
    return map_type, description, map_code

@bot.message_handler(content_types=["photo"])
def handle_craftland_map(message):
    if not message.caption:
        return

    caption_stripped = message.caption.strip()
    caption_lower = caption_stripped.lower()

    # 🚀 إذا كانت الصورة تحتوي على /setnews، تُحفظ كتسريب ولا تُعامل كخريطة
    if "/setnews" in caption_lower or "setnews/" in caption_lower:
        if is_admin(message.chat.id, message.from_user.id):
            clean_text = message.caption.replace("/setnews", "").replace("setnews/", "").strip()
            add_news_item(message.chat.id, clean_text if clean_text else "🔥 تسريب جديد!", message.photo[-1].file_id)
            bot.reply_to(message, "✅ تم حفظ التسريب بنجاح! (ولن يتم تحويله إلى خريطة)")
        return

    # 🗺️ الخريطة يجب أن تبدأ بـ /map وإلا يتم تجاهلها
    if not caption_lower.startswith("/map"):
        return

    remaining_caption = caption_stripped[len("/map"):].strip()
    if not remaining_caption:
        bot.reply_to(message, "⚠️ يرجى كتابة اسم الخريطة والوصف وكود الخريطة بعد /map")
        return

    add_xp(message.from_user.id, message.from_user.first_name, 50)
    map_type, description_escaped, map_code_escaped = extract_map_data(remaining_caption)
    creator_name = html.escape(message.from_user.first_name)

    base_caption = (
        f"🏷️ <b>الخريطة:</b> {map_type}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 <b>الوصف:</b>\n{description_escaped}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>الكود:</b>\n<code>{map_code_escaped}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 <b>بواسطة:</b> {creator_name}\n"
        f"⭐ <b>التقييمات:</b> "
    )

    try:
        sent_msg = bot.send_photo(message.chat.id, message.photo[-1].file_id, caption=base_caption + "0.0/5 (0 أصوات)", parse_mode="HTML", reply_markup=create_rating_markup())
        delete_message_safe(message.chat.id, message.message_id)
        ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
        log_group_message(message.chat.id, sent_msg.message_id)
    except Exception as e:
        print(f"❌ خطأ: {e}")

# ================= 5.ب استيراد التسريبات تلقائياً من قناة التسريبات =================
@bot.channel_post_handler(func=lambda m: m.chat.id == LEAK_CHANNEL_ID, content_types=['text', 'photo'])
def import_leak_from_channel(message):
    global last_owner_leak_date

    today = date.today()
    # إذا كان المالك قد أضاف تسريباً بنفسه اليوم، لا يأخذ البوت من القناة
    if last_owner_leak_date == today:
        return

    channel_name = message.chat.title or "قناة التسريبات"
    text = message.caption or message.text or "🔥 تسريب جديد!"
    photo = message.photo[-1].file_id if message.photo else None

    # نحفظ التسريب في قائمة المجموعة الهدف المحددة من طرف المالك (إن وُجدت)
    target_group = owner_target_group.get(OWNER_ID)
    if target_group:
        add_news_item(target_group, text, photo)

    # نعتبر أن اليوم أصبح فيه تسريب مأخوذ تلقائياً (لمنع التكرار لنفس اليوم)
    last_owner_leak_date = today

    try:
        notify_text = (
            "📡 <b>تم أخذ تسريب جديد تلقائياً!</b>\n\n"
            f"📢 <b>المصدر:</b> {html.escape(channel_name)}\n"
            f"📝 <b>المحتوى:</b>\n{html.escape(text)}"
        )
        bot.send_message(OWNER_ID, notify_text, parse_mode="HTML")
    except Exception:
        pass

# ================= 6. أوامر أخرى والأزرار التفاعلية =================
@bot.message_handler(commands=['squad'])
def lfg_command(message):
    request = message.text.replace("/squad", "").strip()
    if not request:
        return
    user_name = html.escape(message.from_user.first_name)
    lfg_text = f"🎯 <b>طـلـب انـضـمـام</b> 🎯\n\n👤 <b>اللاعب:</b> {user_name}\n💬 <b>الطلب:</b> {html.escape(request)}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💬 تواصل", url=f"tg://user?id={message.from_user.id}"))
    sent = bot.send_message(message.chat.id, lfg_text, parse_mode="HTML", reply_markup=markup)
    track_bot_message(message.chat.id, sent)
    delete_message_safe(message.chat.id, message.message_id)

@bot.message_handler(commands=['tour'])
def create_tournament(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    tour_name = message.text.replace("/tour", "").strip() or "بطولة كلاش سكواد"
    msg = bot.send_message(
        message.chat.id,
        f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour_name)}\n👥 <b>المسجلين:</b> 0\n\nاضغط على الزر للتسجيل!",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تسجيل", callback_data="tour_join"))
    )
    tournaments[msg.message_id] = {"name": tour_name, "players": {}}
    delete_message_safe(message.chat.id, message.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    if call.data == "menu_squad":
        bot.send_message(chat_id, "للبحث عن فريق، اكتب أمر `/squad` متبوعاً بطلبك.\nمثال: `/squad رانك ماستر`", parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "menu_news":
        items = news_store.get(chat_id, [])
        if not items:
            bot.answer_callback_query(call.id, "😔 لا توجد تسريبات محفوظة حالياً.", show_alert=True)
        else:
            for item in items:
                text = f"🕵️‍♂️ <b>تـسـريـب</b> 🕵️‍♂️\n\n{html.escape(item['text']) if item['text'] else ''}"
                try:
                    if item["photo"]:
                        sent = bot.send_photo(chat_id, item["photo"], caption=text, parse_mode="HTML")
                    else:
                        sent = bot.send_message(chat_id, text, parse_mode="HTML")
                    try:
                        bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
                    except Exception:
                        pass
                    log_group_message(chat_id, sent.message_id)
                except Exception:
                    continue
            bot.answer_callback_query(call.id)

    elif call.data == "menu_top":
        if not user_xp:
            return bot.answer_callback_query(call.id, "📊 لا يوجد تفاعل كافي بعد.", show_alert=True)
        sorted_users = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
        top_text = "🏆 <b>أفـضـل 5 مـتـفـاعـلـيـن</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        for i, (uid, data) in enumerate(sorted_users):
            top_text += f"{medals[i]} <b>{data['name']}</b> - {data['xp']} XP\n"
        sent = bot.send_message(chat_id, top_text, parse_mode="HTML")
        track_bot_message(chat_id, sent, chat_type=call.message.chat.type)
        bot.answer_callback_query(call.id)

    elif call.data == "menu_wiki":
        bot.answer_callback_query(call.id, "اكتب /wiki متبوعاً باسم سلاح أو شخصية.\nمثال: /wiki الوك", show_alert=True)

    elif call.data == "admin_delete":
        if is_admin(chat_id, user_id):
            delete_message_safe(chat_id, msg_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ هذا الزر للمشرفين فقط!", show_alert=True)

    elif call.data == "admin_tour":
        if is_admin(chat_id, user_id):
            bot.send_message(chat_id, "لإنشاء بطولة، اكتب: `/tour اسم البطولة`", parse_mode="Markdown")
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "⚠️ هذا الزر للمشرفين فقط!", show_alert=True)

    elif call.data == "tour_join":
        if msg_id in tournaments:
            tour = tournaments[msg_id]
            if user_id not in tour["players"]:
                tour["players"][user_id] = call.from_user.first_name
                count = len(tour["players"])
                updated_text = f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour['name'])}\n👥 <b>المسجلين:</b> {count}\n\nاضغط على الزر للتسجيل!"
                bot.edit_message_text(text=updated_text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
                bot.answer_callback_query(call.id, "✅ تم تسجيلك بنجاح!")
            else:
                bot.answer_callback_query(call.id, "⚠️ أنت مسجل مسبقاً!")

    elif call.data.startswith("rate_"):
        rating_val = int(call.data.split("_")[1])
        if msg_id not in ratings_data:
            return bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية التقييم!", show_alert=True)

        data = ratings_data[msg_id]
        data["votes"][user_id] = rating_val
        votes = data["votes"]
        total_votes = len(votes)
        avg_rating = round(sum(votes.values()) / total_votes, 1)
        updated_text = f"{data['base_text']}{avg_rating}/5 ({total_votes} أصوات)"

        try:
            if data["is_caption"]:
                bot.edit_message_caption(caption=updated_text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            else:
                bot.edit_message_text(text=updated_text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            bot.answer_callback_query(call.id, f"✅ تم حفظ تقييمك: {rating_val} نجوم")
        except Exception:
            pass


print("⚡ البوت يعمل الآن بكل الميزات الجديدة...")
bot.infinity_polling()
