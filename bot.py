import re
from datetime import datetime, timedelta
import threading
import html
import time
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 توكن البوت الخاص بك
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# 👑 أيدي المالك الخاص بك
OWNER_ID = 7454358135

# 📡 أيدي قناة التسريبات الجديدة
LEAKS_CHANNEL_ID = -1003335103713

# ================= قواعد البيانات المؤقتة =================
ratings_data = {}
user_xp = {}  
tournaments = {} 
user_violations = {} 
user_cooldowns = {}      # نظام الـ Cooldown للرسائل (5 ثوانٍ)
message_counter = 0      # عداد الرسائل لحذفها عند 1000
news_list = []           # قائمة لتخزين التسريبات المتعددة
latest_leak = {"text": "لم يتم إضافة أي تسريبات بعد! 🕵️‍♂️", "photo": None}

# 🚫 لائحة الكلمات البذيئة الشاملة
BAD_WORDS = [
    "قحب", "قحبة", "تبة", "زمل", "زملي", "زامل", "حاوي", "منيوك", "مك", "مكك", "اختك", "موك", 
    "تيك", "زبي", "زب", "قلاوي", "قلوة", "طاسيلتك", "عصيد", "كحاب", "ميكة", "بزول", "طرمة",
    "كلب", "حمار", "وسخ", "منحط", "حقير", "لعنة", "ابن الحرام", "ساقط", "متخلف", "قذر",
    "fuck", "fucking", "shit", "bitch", "asshole", "dick", "cunt", "bastard", "slut", "whore", 
    "idiot", "motherfucker", "pussy", "crap", "suck",
    "putain", "merde", "connard", "connasse", "salope", "enculé", "nique", "bite", "fdp", "pute"
]

# ================= دوال المساعدة =================
def delete_message_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def send_self_destruct_message(chat_id, text, parse_mode=None, reply_markup=None):
    """دالة لرسائل البوت التي تختفي تلقائياً بعد 3 دقائق (180 ثانية) لتنظيف المجموعة"""
    try:
        msg = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        threading.Timer(180.0, delete_message_safe, args=(chat_id, msg.message_id)).start()
        return msg
    except Exception:
        return None

def send_self_destruct_photo(chat_id, photo, caption=None, parse_mode=None, reply_markup=None):
    """دالة لصور البوت التي تختفي تلقائياً بعد 3 دقائق (180 ثانية)"""
    try:
        msg = bot.send_photo(chat_id, photo, caption=caption, parse_mode=parse_mode, reply_markup=reply_markup)
        threading.Timer(180.0, delete_message_safe, args=(chat_id, msg.message_id)).start()
        return msg
    except Exception:
        return None

def add_xp(user_id, name, amount):
    if user_id not in user_xp:
        user_xp[user_id] = {"name": name, "xp": 0}
    user_xp[user_id]["xp"] += amount

def is_admin(chat_id, user_id):
    if user_id == OWNER_ID:
        return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

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

# ================= مراقب الرسائل الشامل (حذف 1000 رسالة + Cooldown + السبام + الخرائط) =================
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker', 'animation'])
def global_message_handler(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text or message.caption or ""

    # 1. نظام حذف الرسائل عند 1000 رسالة (تجاهل المثبتة، يشمل الجميع)
    if chat_id < 0:  # مجموعات فقط
        global message_counter
        message_counter += 1
        if message_counter >= 1000:
            message_counter = 0
            # تليجرام يحذف الرسائل عبر الـ ID تنازلياً مع استثناء المثبتة تلقائياً بالبايثون قدر الإمكان
            try:
                for m_id in range(message.message_id - 1000, message.message_id):
                    try:
                        bot.delete_message(chat_id, m_id)
                    except:
                        pass
            except:
                pass

    # 2. نظام الانتظار (Cooldown) لمدة 5 ثوانٍ لكل شخص (حتى المالك والأدمن أو العاديين)
    current_time = time.time()
    if user_id in user_cooldowns:
        elapsed = current_time - user_cooldowns[user_id]
        if elapsed < 5.0:
            delete_message_safe(chat_id, message.message_id)
            return  # تجاهل الرسالة تماماً إذا لم تمر 5 ثوانٍ
    user_cooldowns[user_id] = current_time

    # 3. التحقق من الألفاظ البذيئة (فلتر السبام والشتائم)
    if not text.strip().startswith('/') and not is_admin(chat_id, user_id):
        text_lower = text.lower()
        if any(word in text_lower for word in BAD_WORDS):
            delete_message_safe(chat_id, message.message_id)
            if user_id not in user_violations:
                user_violations[user_id] = 0
            user_violations[user_id] += 1
            v_count = user_violations[user_id]
            user_name = html.escape(message.from_user.first_name)
            
            try:
                if v_count == 1:
                    send_self_destruct_message(chat_id, f"⚠️ <b>تـحـذيـر رسـمـي !</b>\n\n👤 العضو: <b>{user_name}</b>\n💬 السبب: استخدام ألفاظ بذيئة.", parse_mode="HTML")
                elif v_count == 2:
                    until_time = datetime.now() + timedelta(minutes=5)
                    bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
                    send_self_destruct_message(chat_id, f"🔇 <b>ميوت 5 دقائق !</b>\n👤 العضو: <b>{user_name}</b>", parse_mode="HTML")
                elif v_count >= 3:
                    bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                    send_self_destruct_message(chat_id, f"🔒 <b>تم كتم العضو نهائياً لتكرار الشتم.</b>", parse_mode="HTML")
            except:
                pass
            return

    # 4. نظام الخرائط الإلزامي (/map)
    if message.photo and chat_id < 0:
        if not text.lower().startswith('/map'):
            delete_message_safe(chat_id, message.message_id)
            return
        
        add_xp(user_id, message.from_user.first_name, 50)
        clean_caption = text.replace("/map", "").replace("/Map", "").strip()
        map_type, description_escaped, map_code_escaped = extract_map_data(clean_caption)
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
            sent_msg = bot.send_photo(chat_id, message.photo[-1].file_id, caption=base_caption + "0.0/5 (0 أصوات)", parse_mode="HTML", reply_markup=create_rating_markup())
            delete_message_safe(chat_id, message.message_id)
            ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
        except:
            pass

# ================= الجلب التلقائي من القناة المحددة =================
@bot.channel_post_handler(content_types=['photo', 'text'])
def channel_leaks_listener(message):
    if message.chat.id == LEAKS_CHANNEL_ID:
        global latest_leak
        leak_text = message.caption or message.text or "🔥 تسريب جديد!"
        leak_photo = message.photo[-1].file_id if message.photo else None
        
        latest_leak["photo"] = leak_photo
        latest_leak["text"] = leak_text
        news_list.append({"photo": leak_photo, "text": leak_text})

        # إرسال إشعار للمالك بالآيدي الخاص بك
        try:
            channel_name = message.chat.title or "قناة التسريبات"
            bot.send_message(
                OWNER_ID, 
                f"🚨 <b>تنبيه للمالك:</b> تم جلب تسريب جديد تلقائياً من القناة <b>{html.escape(channel_name)}</b> (ID: <code>{message.chat.id}</code>)",
                parse_mode="HTML"
            )
        except:
            pass

# ================= أوامر الإدارة وتطوير /unmute =================
@bot.message_handler(commands=['unmute'])
def owner_unmute_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not is_admin(chat_id, user_id) and chat_id > 0: 
        return

    args = message.text.split()
    target_id = None

    # فك الميوت بـ 3 طرق: الرد على الرسالة، كتابة اليوزر (@username)، أو الآيدي الرقمي
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(args) > 1:
        identifier = args[1]
        if identifier.isdigit():
            target_id = int(identifier)
        elif identifier.startswith('@'):
            try:
                chat_member = bot.get_chat_member(chat_id, identifier)
                target_id = chat_member.user.id
            except:
                pass

    if not target_id:
        return bot.reply_to(message, "⚠️ يرجى الرد على رسالة الشخص، أو كتابة يوزره (@username)، أو آيديه بعد الأمر.")

    try:
        target_chat_id = chat_id if chat_id < 0 else -1003335103713
        bot.restrict_chat_member(target_chat_id, target_id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
        if target_id in user_violations: 
            user_violations[target_id] = 0
        owner_name = html.escape(message.from_user.first_name)
        send_self_destruct_message(
            target_chat_id,
            f"🔓 <b>عـفـو مـلـكـي / فَـك الـحَـظْـر !</b>\n✨ تم رفع عقوبة الميوت عن العضو بواسطة المشرف <b>{owner_name}</b>.",
            parse_mode="HTML"
        )
        bot.reply_to(message, "✅ تم فك الميوت بنجاح!")
    except:
        bot.reply_to(message, "❌ حدث خطأ، تأكد من صلاحيات البوت.")

@bot.message_handler(commands=['ban', 'mute'])
def admin_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0].lower()

    if not is_admin(chat_id, user_id): return
    if not message.reply_to_message: return bot.reply_to(message, "⚠️ يرجى الرد على رسالة الشخص.")

    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    try:
        if command == '/ban':
            bot.ban_chat_member(chat_id, target_id)
            send_self_destruct_message(chat_id, f"⛔ تم طرد <b>{html.escape(target_name)}</b>.", parse_mode="HTML")
        elif command == '/mute':
            bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(can_send_messages=False))
            send_self_destruct_message(chat_id, f"🔇 تم كتم <b>{html.escape(target_name)}</b>.", parse_mode="HTML")
    except: 
        pass

# ================= نظام التسريبات المتعددة (/setnews و /news) =================
@bot.message_handler(commands=['setnews'])
def set_news_command(message):
    if message.from_user.id != OWNER_ID and not is_admin(message.chat.id, message.from_user.id): 
        return

    if message.reply_to_message:
        reply = message.reply_to_message
        photo_id = reply.photo[-1].file_id if reply.photo else None
        text_content = reply.caption or reply.text or "🔥 تسريب جديد!"
        news_list.append({"photo": photo_id, "text": text_content})
        bot.reply_to(message, f"✅ تمت إضافة التسريب للقائمة بنجاح! (العدد الإجمالي: {len(news_list)})")
    else:
        clean_text = message.text.replace("/setnews", "").strip()
        if clean_text or message.photo:
            photo_id = message.photo[-1].file_id if message.photo else None
            news_list.append({"photo": photo_id, "text": clean_text or "🔥 تسريب جديد!"})
            bot.reply_to(message, f"✅ تمت إضافة التسريب للقائمة بنجاح! (العدد الإجمالي: {len(news_list)})")
        else:
            bot.reply_to(message, "⚠️ أرسل التسريب أو رد على صورة بـ `/setnews`.")

@bot.message_handler(commands=['news'])
def send_all_news(message):
    if not news_list:
        return bot.reply_to(message, "📭 لا توجد تسريبات مخزنة حالياً.")
    
    target_chat = message.chat.id
    for item in news_list:
        try:
            if item["photo"]:
                msg = bot.send_photo(target_chat, item["photo"], caption=f"🔥 <b>تـسـريـب:</b>\n{item['text']}", parse_mode="HTML")
            else:
                msg = bot.send_message(target_chat, f"🔥 <b>تـسـريـب:</b>\n{item['text']}", parse_mode="HTML")
            
            # تثبيت التسريبات تلقائياً كي لا تحذف بنظام التنظيف
            bot.pin_chat_message(target_chat, msg.message_id)
        except:
            pass
    bot.reply_to(message, "🚀 تم إرسال جميع التسريبات وتثبيتها تلقائياً!")

# ================= الترحيب والخاص للمالك =================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        welcome_text = f"⚡ <b>أهلاً بك يا أسطورة</b> ⚡\n\n👤 <b>اللاعب:</b> {mention}\n\nاختر من القائمة أدناه لاكتشاف ميزات البوت 👇"
        send_self_destruct_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=create_main_menu())

@bot.message_handler(commands=['help', 'start', 'menu'])
def send_menu(message):
    if message.chat.type == 'private':
        if message.from_user.id == OWNER_ID:
            bot.send_message(message.chat.id, "👑 <b>أهلاً بك يا مالك البوت والمجموعات العظيم!</b>\nتم التعرف عليك بنجاح. يمكنك إرسال أو إضافة التسريبات هنا عبر `/setnews` وسيتم إرسالها للمجموعة المحددة.", parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "👋 <b>أهلاً بك في بوت الخدمة الخاص بنا!</b>", parse_mode="HTML")
    
    send_self_destruct_message(message.chat.id, "🕹️ <b>قـائـمـة الـتـحـكـم الـرئـيـسـيـة</b> 🕹️", parse_mode="HTML", reply_markup=create_main_menu())

# ================= استخراج بيانات الخرائط =================
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

# ================= الألعاب والأزرار التفاعلية =================
@bot.message_handler(commands=['squad'])
def lfg_command(message):
    request = message.text.replace("/squad", "").strip()
    if not request: return
    user_name = html.escape(message.from_user.first_name)
    lfg_text = f"🎯 <b>طـلـب انـضـمـام</b> 🎯\n\n👤 <b>اللاعب:</b> {user_name}\n💬 <b>الطلب:</b> {html.escape(request)}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💬 تواصل", url=f"tg://user?id={message.from_user.id}"))
    send_self_destruct_message(message.chat.id, lfg_text, parse_mode="HTML", reply_markup=markup)
    delete_message_safe(message.chat.id, message.message_id)

@bot.message_handler(commands=['tour'])
def create_tournament(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    tour_name = message.text.replace("/tour", "").strip() or "بطولة كلاش سكواد"
    msg = send_self_destruct_message(
        message.chat.id, 
        f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour_name)}\n👥 <b>المسجلين:</b> 0", 
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تسجيل", callback_data="tour_join"))
    )
    if msg:
        tournaments[msg.message_id] = {"name": tour_name, "players": {}}
    delete_message_safe(message.chat.id, message.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    if call.data == "menu_squad":
        bot.answer_callback_query(call.id, "للبحث عن فريق، اكتب أمر /squad متبوعاً بطلبك.", show_alert=True)
        
    elif call.data == "menu_news":
        if news_list:
            for item in news_list:
                try:
                    if item["photo"]:
                        m = bot.send_photo(chat_id, item["photo"], caption=f"🔥 <b>تـسـريـب:</b>\n{item['text']}", parse_mode="HTML")
                    else:
                        m = bot.send_message(chat_id, f"🔥 <b>تـسـريـب:</b>\n{item['text']}", parse_mode="HTML")
                    bot.pin_chat_message(chat_id, m.message_id)
                except:
                    pass
            bot.answer_callback_query(call.id, "✅ تم إرسال وتثبيت جميع التسريبات!")
        else:
            text = f"🕵️‍♂️ <b>آخـر الـتـسـريـبـات</b> 🕵️‍♂️\n\n{html.escape(latest_leak['text'])}"
            if latest_leak["photo"]:
                send_self_destruct_photo(chat_id, latest_leak["photo"], caption=text, parse_mode="HTML")
            else:
                send_self_destruct_message(chat_id, text, parse_mode="HTML")
            bot.answer_callback_query(call.id)

    elif call.data == "menu_top":
        if not user_xp:
            return bot.answer_callback_query(call.id, "📊 لا يوجد تفاعل كافي بعد.", show_alert=True)
        sorted_users = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
        top_text = "🏆 <b>أفـضـل 5 مـتـفـاعـلـيـن</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        for i, (uid, data) in enumerate(sorted_users):
            top_text += f"{medals[i]} <b>{data['name']}</b> - {data['xp']} XP\n"
        send_self_destruct_message(chat_id, top_text, parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data == "menu_wiki":
        bot.answer_callback_query(call.id, "اكتب /wiki متبوعاً باسم العنصر.", show_alert=True)

    elif call.data == "admin_delete":
        if is_admin(chat_id, user_id): delete_message_safe(chat_id, msg_id)
        else: bot.answer_callback_query(call.id, "⚠️ للمشرفين فقط!", show_alert=True)

    elif call.data == "admin_tour":
        if is_admin(chat_id, user_id):
            bot.answer_callback_query(call.id, "لإنشاء بطولة اكتب /tour اسم البطولة")
        else: bot.answer_callback_query(call.id, "⚠️ للمشرفين فقط!", show_alert=True)

    elif call.data == "tour_join":
        if msg_id in tournaments:
            tour = tournaments[msg_id]
            if user_id not in tour["players"]:
                tour["players"][user_id] = call.from_user.first_name
                count = len(tour["players"])
                updated_text = f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour['name'])}\n👥 <b>المسجلين:</b> {count}"
                try:
                    bot.edit_message_text(text=updated_text, chat_id=chat_id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
                except:
                    pass
                bot.answer_callback_query(call.id, "✅ تم تسجيلك بنجاح!")
            else: bot.answer_callback_query(call.id, "⚠️ أنت مسجل مسبقاً!")

    elif call.data.startswith("rate_"):
        rating_val = int(call.data.split("_")[1])
        if msg_id not in ratings_data: return bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية التقييم!", show_alert=True)

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
        except: 
            pass


print("⚡ البوت يعمل بكامل الخصائص والميزات الجديدة بنجاح...")
bot.infinity_polling()
