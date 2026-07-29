import re
import time
from datetime import datetime, timedelta
import threading
import html
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telebot.handler_backends import BaseMiddleware, CancelUpdate

# 🔑 توكن البوت الخاص بك
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# 📡 أيدي القنوات والمالك
LEAKS_CHANNEL_ID = "-1003335103713"
OWNER_ID = 7454358135

# ================= قواعد البيانات المؤقتة =================
ratings_data = {}
user_xp = {}  
tournaments = {} 
user_violations = {} 

saved_leaks = []  # قائمة لحفظ التسريبات المتعددة
last_owner_leak_date = None # تتبع تاريخ آخر تسريب للمالك

# قواعد بيانات التتبع والسبام
user_cooldowns = {} # وقت آخر رسالة للعضو (للـ 5 ثواني)
username_cache = {} # حفظ المعرفات لتسهيل أمر unmute

# 🚫 لائحة الكلمات البذيئة الشاملة
BAD_WORDS = [
    "قحب", "قحبة", "تبة", "زمل", "زملي", "زامل", "حاوي", "منيوك", "مك", "مكك", "اختك", "موك", 
    "تيك", "زبي", "زب", "قلاوي", "قلوة", "طاسيلتك", "عصيد", "كحاب", "ميكة", "بزول", "طرمة",
    "كلب", "حمار", "وسخ", "منحط", "حقير", "لعنة", "ابن الحرام", "ساقط", "متخلف", "قذر",
    "fuck", "fucking", "shit", "bitch", "asshole", "dick", "cunt", "bastard", "slut", "whore", 
    "idiot", "motherfucker", "pussy", "crap", "suck"
]

# ================= دوال المساعدة =================
def delete_message_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def send_and_schedule(chat_id, text, **kwargs):
    """إرسال رسالة وحذفها تلقائياً بعد 3 دقائق ما لم يطلب تثبيتها"""
    pin = kwargs.pop('pin', False)
    try:
        msg = bot.send_message(chat_id, text, **kwargs)
        if pin:
            try: bot.pin_chat_message(chat_id, msg.message_id)
            except: pass
        else:
            threading.Timer(180.0, delete_message_safe, args=(chat_id, msg.message_id)).start()
        return msg
    except: return None

def add_xp(user_id, name, amount):
    if user_id not in user_xp: user_xp[user_id] = {"name": name, "xp": 0}
    user_xp[user_id]["xp"] += amount

def is_admin(chat_id, user_id):
    if user_id == OWNER_ID: return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except: return False

# ================= لوحات الأزرار =================
def create_rating_markup():
    markup = InlineKeyboardMarkup(row_width=5)
    markup.add(
        InlineKeyboardButton("⭐ 1", callback_data="rate_1"), InlineKeyboardButton("⭐ 2", callback_data="rate_2"),
        InlineKeyboardButton("⭐ 3", callback_data="rate_3"), InlineKeyboardButton("⭐ 4", callback_data="rate_4"),
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

# ================= 0. نظام التتبع المتقدم (Middleware) =================
class BotMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_types = ['message']

    def pre_process(self, message, data):
        if not message: return
        chat_id = message.chat.id
        user_id = message.from_user.id

        # تحديث ذاكرة المعرفات (Usernames)
        if message.from_user.username:
            username_cache["@" + message.from_user.username.lower()] = user_id

        # تنفيذ الأوامر داخل المجموعة
        if message.chat.type in ['group', 'supergroup']:
            # 1. نظام الـ 5 ثواني (السبام)
            if not is_admin(chat_id, user_id):
                now = time.time()
                last_time = user_cooldowns.get(user_id, 0)
                if now - last_time < 5:
                    delete_message_safe(chat_id, message.message_id)
                    return CancelUpdate()
                user_cooldowns[user_id] = now

    def post_process(self, message, data, exception):
        pass

bot.setup_middleware(BotMiddleware())

# ================= 1. نظام العقوبات الذكي =================
def is_bad_message(message):
    text = message.text or message.caption
    if not text or text.strip().startswith('/'): return False
    if is_admin(message.chat.id, message.from_user.id): return False
    
    text_lower = text.lower()
    return any(word in text_lower for word in BAD_WORDS)

@bot.message_handler(func=is_bad_message, content_types=['text', 'photo', 'video'])
def filter_bad_words(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    user_name = html.escape(message.from_user.first_name)
    delete_message_safe(chat_id, message.message_id)

    user_violations[user_id] = user_violations.get(user_id, 0) + 1
    v_count = user_violations[user_id]

    try:
        if v_count == 1:
            send_and_schedule(chat_id, f"⚠️ <b>تـحـذيـر رسـمـي !</b>\n\n👤 العضو: <b>{user_name}</b>\n💬 السبب: استخدام ألفاظ بذيئة.\n📌 <i>هذا تحذيرك الأول!</i>", parse_mode="HTML")
        elif v_count == 2:
            bot.restrict_chat_member(chat_id, user_id, until_date=datetime.now() + timedelta(minutes=5), permissions=ChatPermissions(can_send_messages=False))
            send_and_schedule(chat_id, f"🔇 <b>عـقـوبـة مـيـوت مـؤقـت !</b>\n\n👤 العضو: <b>{user_name}</b>\n⏳ المدة: <b>5 دقائق</b>", parse_mode="HTML")
        elif v_count == 3:
            bot.restrict_chat_member(chat_id, user_id, until_date=datetime.now() + timedelta(days=1), permissions=ChatPermissions(can_send_messages=False))
            send_and_schedule(chat_id, f"⏳ <b>تـعـليـق مـؤقـت (24 سـاعـة) !</b>\n\n👤 العضو: <b>{user_name}</b>\n⚠️ تم كتمك لمدة يوم كامل.", parse_mode="HTML")
        elif v_count == 4:
            bot.restrict_chat_member(chat_id, user_id, until_date=datetime.now() + timedelta(days=5), permissions=ChatPermissions(can_send_messages=False))
            send_and_schedule(chat_id, f"⛔ <b>حـظـر تـفـاعـل (5 أيـام) !</b>\n\n👤 العضو: <b>{user_name}</b>\n🚨 تم منعك من الكتابة لمدة 5 أيام.", parse_mode="HTML")
        else:
            bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛡️ تواصل للإعتذار", url=f"https://t.me/an_as1209"))
            send_and_schedule(chat_id, f"🔒 <b>تـم كـتـم الـعـضـو مـدى الـحـيـاة !</b>\n\n👤 العضو: <b>{user_name}</b>\n❌ تم إسكاتك نهائياً.", parse_mode="HTML", reply_markup=markup)
    except: pass

# ================= 2. أوامر الإدارة وتحديث /delmsg =================
@bot.message_handler(commands=['delmsg'])
def delete_all_messages_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_admin(chat_id, user_id): 
        return
    
    # إرسال رسالة التقدم وحفظ الآيدي الخاص بها لكي لا يتم مسحها
    status_msg = bot.send_message(chat_id, "🧹 <b>جاري تنظيف رسائل المجموعة...</b>\n[░░░░░░░░░░] 0%", parse_mode="HTML")
    
    def clear_history():
        current_id = message.message_id
        pinned_id = None
        try:
            c = bot.get_chat(chat_id)
            if c.pinned_message: pinned_id = c.pinned_message.message_id
        except: pass

        # كمية الرسائل التي سيتم البحث عنها ومسحها
        limit = 3000
        start_id = current_id
        end_id = max(0, current_id - limit)
        total_steps = max(1, limit // 100)
        
        # تقسيم الحذف لدفعات من 100 رسالة
        for step, start in enumerate(range(start_id, end_id, -100)):
            # استثناء الرسالة المثبتة ورسالة شريط التقدم
            batch = [i for i in range(start, max(end_id, start - 100), -1) if i != pinned_id and i != status_msg.message_id]
            
            try:
                # محاولة مسح الدفعة كاملة (وهذا يتطلب صلاحية مسح الرسائل للبوت)
                bot.delete_messages(chat_id, batch)
            except:
                # إذا فشل المسح الجماعي، يتم مسحها واحدة تلو الأخرى
                for m_id in batch:
                    try: bot.delete_message(chat_id, m_id)
                    except: pass
            
            # تحديث شريط التقدم كل 10%
            progress = int((step / total_steps) * 100)
            if progress % 10 == 0 or progress == 100:
                filled = progress // 10
                empty = 10 - filled
                bar = "▓" * filled + "░" * empty
                try:
                    bot.edit_message_text(
                        f"🧹 <b>جاري تنظيف رسائل المجموعة...</b>\n[{bar}] {progress}%", 
                        chat_id, 
                        status_msg.message_id, 
                        parse_mode="HTML"
                    )
                except: pass
                
        # إكمال شريط التقدم وإنهاء العملية
        try:
            bot.edit_message_text(
                "✅ <b>تم تنظيف المجموعة بالكامل بنجاح!</b>\n[▓▓▓▓▓▓▓▓▓▓] 100%", 
                chat_id, 
                status_msg.message_id, 
                parse_mode="HTML"
            )
            # مسح رسالة إشعار النجاح بعد دقيقة
            threading.Timer(60.0, delete_message_safe, args=(chat_id, status_msg.message_id)).start()
        except: pass

    # استخدام Thread حتى لا يتوقف البوت أثناء المسح
    threading.Thread(target=clear_history).start()


@bot.message_handler(commands=['unmute'])
def owner_unmute_command(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    if not is_admin(chat_id, user_id) and message.chat.type != 'private': return
    
    args = message.text.split()
    target_id = None
    
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1:
        if args[1].isdigit(): target_id = int(args[1])
        elif args[1].startswith('@'): target_id = username_cache.get(args[1].lower())

    if not target_id: return send_and_schedule(chat_id, "❌ لم أتمكن من التعرف على هذا العضو. تأكد من الرد عليه أو كتابة الآيدي/المعرف الصحيح.")

    try:
        # البحث عن أيدي الجروب إذا تم إرساله في الخاص
        target_chat_id = chat_id if message.chat.type != 'private' else -1007454358135
        bot.restrict_chat_member(target_chat_id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        if target_id in user_violations: user_violations[target_id] = 0
        owner_name = html.escape(message.from_user.first_name)
        send_and_schedule(target_chat_id, f"🔓 <b>عـفـو مـلـكـي / فَـك الـحَـظْـر !</b> 🔓\n\n✨ تم بفضل الله رفع عقوبة الميوت بناءً على عفو من المالك <b>{owner_name}</b>.", parse_mode="HTML")
        send_and_schedule(chat_id, "✅ تم فك الميوت عن العضو بنجاح!")
    except: send_and_schedule(chat_id, "❌ حدث خطأ، تأكد أن البوت يملك صلاحيات أو أنك أرسلت الأمر في المجموعة.")

@bot.message_handler(commands=['ban', 'mute'])
def admin_commands(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    if not is_admin(chat_id, user_id): return
    if not message.reply_to_message: return send_and_schedule(chat_id, "⚠️ يرجى الرد على رسالة الشخص.")

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    try:
        if message.text.startswith('/ban'):
            bot.ban_chat_member(chat_id, target_id)
            send_and_schedule(chat_id, f"⛔ تم طرد <b>{html.escape(target_name)}</b> من المجموعة.", parse_mode="HTML")
        elif message.text.startswith('/mute'):
            bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=False))
            send_and_schedule(chat_id, f"🔇 تم كتم <b>{html.escape(target_name)}</b>.", parse_mode="HTML")
    except: pass

# ================= 3. ترحيب المالك والأعضاء =================
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id == OWNER_ID, commands=['start'])
def welcome_owner_private(message):
    send_and_schedule(message.chat.id, "👑 <b>أهلاً بك سيدي المالك!</b> يسعدني خدمتك دوماً.\nيمكنك إضافة التسريبات هنا مباشرة عبر أمر `/setnews` مع الصور.", parse_mode="HTML")

@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        send_and_schedule(message.chat.id, f"⚡ <b>أهلاً بك يا أسطورة</b> ⚡\n\n👤 <b>اللاعب:</b> {mention}\n\nاختر من القائمة أدناه لاكتشاف ميزات البوت 👇", parse_mode="HTML", reply_markup=create_main_menu())

@bot.message_handler(commands=['help', 'start', 'menu'])
def send_menu(message):
    if message.chat.type == 'private' and message.from_user.id != OWNER_ID: return
    send_and_schedule(message.chat.id, "🕹️ <b>قـائـمـة الـتـحـكـم الـرئـيـسـيـة</b> 🕹️\n\nاختر ما تريد من الأزرار أسفله:", parse_mode="HTML", reply_markup=create_main_menu())

# ================= 4. الجلب التلقائي والتسريبات المتعددة =================
@bot.channel_post_handler(func=lambda m: str(m.chat.id) == LEAKS_CHANNEL_ID)
def auto_fetch_leaks(message):
    global last_owner_leak_date
    today = datetime.now().date()
    if last_owner_leak_date != today:
        leak = {"text": message.text or message.caption or "🔥 تسريب جديد!", "photo": message.photo[-1].file_id if message.photo else None}
        saved_leaks.append(leak)
        try: bot.send_message(OWNER_ID, f"🔔 <b>تم أخذ تسريب جديد تلقائياً من القناة!</b>\n📌 القناة: {message.chat.title}\n🆔 الأيدي: {message.chat.id}", parse_mode="HTML")
        except: pass

@bot.message_handler(commands=['setnews'], content_types=['text', 'photo'])
def set_news_command(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    global last_owner_leak_date
    
    leak_data = {"text": "🔥 تسريب جديد!", "photo": None}
    
    if message.reply_to_message:
        reply_msg = message.reply_to_message
        leak_data["photo"] = reply_msg.photo[-1].file_id if reply_msg.photo else None
        leak_data["text"] = reply_msg.caption or reply_msg.text or leak_data["text"]
    else:
        leak_data["photo"] = message.photo[-1].file_id if message.photo else None
        text = (message.caption or message.text).replace('/setnews', '').replace('setnews/', '').strip()
        leak_data["text"] = text if text else leak_data["text"]

    saved_leaks.append(leak_data)
    last_owner_leak_date = datetime.now().date()
    
    send_and_schedule(message.chat.id, f"✅ تم حفظ التسريب بنجاح! (العدد الحالي: {len(saved_leaks)})")

@bot.message_handler(commands=['news'])
def send_all_news(message):
    if not saved_leaks:
        return send_and_schedule(message.chat.id, "لم يتم إضافة أي تسريبات بعد! 🕵️‍♂️")
    
    send_and_schedule(message.chat.id, "🔥 <b>إليكم أحدث التسريبات:</b>", parse_mode="HTML")
    for leak in saved_leaks:
        try:
            if leak['photo']:
                msg = bot.send_photo(message.chat.id, leak['photo'], caption=f"🕵️‍♂️ <b>تسريب</b> 🕵️‍♂️\n\n{html.escape(leak['text'])}", parse_mode="HTML")
            else:
                msg = bot.send_message(message.chat.id, f"🕵️‍♂️ <b>تسريب</b> 🕵️‍♂️\n\n{html.escape(leak['text'])}", parse_mode="HTML")
            bot.pin_chat_message(message.chat.id, msg.message_id)
        except: pass

# ================= 5. استخراج ونشر الخرائط =================
@bot.message_handler(content_types=["photo"])
def handle_craftland_map(message):
    if not message.caption: return
    caption_lower = message.caption.lower()

    if "/setnews" in caption_lower: return set_news_command(message)

    if "/map" not in caption_lower:
        send_and_schedule(message.chat.id, "⚠️ <b>خطأ!</b>\nلنشر خريطة، يجب أن تكتب `/map` في الوصف أولاً، ثم مسافة وتكتب الإسم والوصف والكود!", parse_mode="Markdown")
        return

    add_xp(message.from_user.id, message.from_user.first_name, 50)
    
    clean_caption = message.caption.replace("/map", "", 1).strip()
    
    map_type = "خريطة"
    map_code = "غير متوفر"
    lines = clean_caption.split('\n')
    if lines: map_type = html.escape(lines[0].strip())
    
    code_match = re.search(r"(كود[:：]?\s*([A-Za-z0-9#\-_]+))", clean_caption, re.IGNORECASE)
    hash_match = re.search(r"([A-Za-z0-9]*FREEFIRE[A-Za-z0-9#\-_]+)", clean_caption, re.IGNORECASE)
    
    if code_match:
        map_code = html.escape(code_match.group(2).strip())
        description_escaped = html.escape(clean_caption.replace(code_match.group(1), "").strip())
    elif hash_match:
        map_code = html.escape(hash_match.group(1).strip())
        description_escaped = html.escape(clean_caption.replace(hash_match.group(1), "").strip())
    else:
        description_escaped = html.escape(clean_caption)

    creator_name = html.escape(message.from_user.first_name)
    base_caption = (
        f"🏷️ <b>الخريطة:</b> {map_type}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 <b>الوصف:</b>\n{description_escaped}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>الكود:</b>\n<code>{map_code}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 <b>بواسطة:</b> {creator_name}\n"
        f"⭐ <b>التقييمات:</b> "
    )
    
    try:
        sent_msg = bot.send_photo(message.chat.id, message.photo[-1].file_id, caption=base_caption + "0.0/5 (0 أصوات)", parse_mode="HTML", reply_markup=create_rating_markup())
        delete_message_safe(message.chat.id, message.message_id)
        ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
    except: pass

# ================= 6. الأزرار التفاعلية والأوامر الأخرى =================
@bot.message_handler(commands=['squad'])
def lfg_command(message):
    request = message.text.replace("/squad", "").strip()
    if not request: return
    user_name = html.escape(message.from_user.first_name)
    lfg_text = f"🎯 <b>طـلـب انـضـمـام</b> 🎯\n\n👤 <b>اللاعب:</b> {user_name}\n💬 <b>الطلب:</b> {html.escape(request)}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💬 تواصل", url=f"tg://user?id={message.from_user.id}"))
    send_and_schedule(message.chat.id, lfg_text, parse_mode="HTML", reply_markup=markup)
    delete_message_safe(message.chat.id, message.message_id)

@bot.message_handler(commands=['tour'])
def create_tournament(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    tour_name = message.text.replace("/tour", "").strip() or "بطولة كلاش سكواد"
    msg = send_and_schedule(
        message.chat.id, 
        f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour_name)}\n👥 <b>المسجلين:</b> 0\n\nاضغط على الزر للتسجيل!", 
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تسجيل", callback_data="tour_join")),
        pin=True
    )
    if msg: tournaments[msg.message_id] = {"name": tour_name, "players": {}}
    delete_message_safe(message.chat.id, message.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id, msg_id, user_id = call.message.chat.id, call.message.message_id, call.from_user.id

    if call.data == "menu_squad":
        send_and_schedule(chat_id, "للبحث عن فريق، اكتب أمر `/squad` متبوعاً بطلبك.\nمثال: `/squad رانك ماستر`", parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "menu_news":
        send_all_news(call.message)
        bot.answer_callback_query(call.id)

    elif call.data == "menu_top":
        if not user_xp: return bot.answer_callback_query(call.id, "📊 لا يوجد تفاعل كافي بعد.", show_alert=True)
        sorted_users = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
        top_text = "🏆 <b>أفـضـل 5 مـتـفـاعـلـيـن</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        for i, (uid, data) in enumerate(sorted_users): top_text += f"{medals[i]} <b>{data['name']}</b> - {data['xp']} XP\n"
        send_and_schedule(chat_id, top_text, parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data == "admin_delete":
        if is_admin(chat_id, user_id): delete_message_safe(chat_id, msg_id)
        else: bot.answer_callback_query(call.id, "⚠️ هذا الزر للمشرفين فقط!", show_alert=True)

    elif call.data == "tour_join":
        if msg_id in tournaments:
            tour = tournaments[msg_id]
            if user_id not in tour["players"]:
                tour["players"][user_id] = call.from_user.first_name
                count = len(tour["players"])
                bot.edit_message_text(text=f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour['name'])}\n👥 <b>المسجلين:</b> {count}\n\nاضغط على الزر للتسجيل!", chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
                bot.answer_callback_query(call.id, "✅ تم تسجيلك بنجاح!")
            else: bot.answer_callback_query(call.id, "⚠️ أنت مسجل مسبقاً!")

    elif call.data.startswith("rate_"):
        rating_val = int(call.data.split("_")[1])
        if msg_id not in ratings_data: return bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية التقييم!", show_alert=True)

        data = ratings_data[msg_id]
        data["votes"][user_id] = rating_val
        votes, total_votes = data["votes"], len(data["votes"])
        avg_rating = round(sum(votes.values()) / total_votes, 1)
        updated_text = f"{data['base_text']}{avg_rating}/5 ({total_votes} أصوات)"

        try:
            if data["is_caption"]: bot.edit_message_caption(caption=updated_text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            bot.answer_callback_query(call.id, f"✅ تم حفظ تقييمك: {rating_val} نجوم")
        except: pass

print("⚡ البوت المتطور يعمل الآن بميزات (المسح بالشريط / بدون حذف عند 30 / حذف للجميع)...")
bot.infinity_polling()
