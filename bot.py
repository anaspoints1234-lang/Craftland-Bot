import re
from datetime import datetime, timedelta
import threading
import html
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 توكن البوت الخاص بك
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# 📡 أيدي قناة التسريبات
LEAKS_CHANNEL_ID = ["7454358135", "-1007454358135"]

# ================= قواعد البيانات المؤقتة =================
ratings_data = {}
user_spam_tracker = {}
user_xp = {}  
tournaments = {} 
user_violations = {} # لتتبع عدد المخالفات لكل مستخدم
latest_leak = {"text": "لم يتم إضافة أي تسريبات بعد! 🕵️‍♂️", "photo": None}

# 🚫 لائحة الكلمات البذيئة الشاملة
BAD_WORDS = [
    # الدارجة المغربية
    "قحب", "قحبة", "تبة", "زمل", "زملي", "زامل", "حاوي", "منيوك", "مك", "مكك", "اختك", "موك", 
    "تيك", "زبي", "زب", "قلاوي", "قلوة", "طاسيلتك", "عصيد", "كحاب", "ميكة", "بزول", "طرمة",
    # العربية الفصحى
    "كلب", "حمار", "وسخ", "منحط", "حقير", "لعنة", "ابن الحرام", "ساقط", "متخلف", "قذر",
    # الإنجليزية
    "fuck", "fucking", "shit", "bitch", "asshole", "dick", "cunt", "bastard", "slut", "whore", 
    "idiot", "motherfucker", "pussy", "crap", "suck",
    # الفرنسية
    "putain", "merde", "connard", "connasse", "salope", "enculé", "nique", "bite", "fdp", "pute"
]

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
    """التحقق مما إذا كان المستخدم مشرفاً أو مالكاً للمجموعة"""
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

# ================= نظام العقوبات التصاعدي للكلمات البذيئة =================
@bot.message_handler(func=lambda message: True, content_types=['text'])
def filter_bad_words(message):
    if message.text.startswith('/') or is_admin(message.chat.id, message.from_user.id):
        return

    text_lower = message.text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            chat_id = message.chat.id
            user_id = message.from_user.id
            user_name = html.escape(message.from_user.first_name)
            
            # حذف رسالة الشتم فوراً
            delete_message_safe(chat_id, message.message_id)

            # تتبع عدد المخالفات
            if user_id not in user_violations:
                user_violations[user_id] = 0
            user_violations[user_id] += 1
            violation_count = user_violations[user_id]

            try:
                if violation_count == 1:
                    # المخالفة 1: تحذير
                    msg = bot.send_message(
                        chat_id, 
                        f"⚠️ <b>تـحـذيـر رسـمـي !</b>\n\n"
                        f"👤 العضو: <b>{user_name}</b>\n"
                        f"💬 السبب: استخدام ألفاظ بذيئة.\n"
                        f"📌 <i>هذا تحذيرك الأول، المرة القادمة ستتعرض للعقوبة!</i>",
                        parse_mode="HTML"
                    )
                    threading.Timer(7.0, delete_message_safe, args=(chat_id, msg.message_id)).start()

                elif violation_count == 2:
                    # المخالفة 2: ميوت قصير (5 دقائق)
                    until_time = datetime.now() + timedelta(minutes=5)
                    bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
                    msg = bot.send_message(
                        chat_id, 
                        f"🔇 <b>عـقـوبـة مـيـوت مـؤقـت !</b>\n\n"
                        f"👤 العضو: <b>{user_name}</b>\n"
                        f"⏳ المدة: <b>5 دقائق</b>\n"
                        f"📌 <i>تكرار المخالفة سيدخلك في عقوبات أشد!</i>",
                        parse_mode="HTML"
                    )
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, msg.message_id)).start()

                elif violation_count == 3:
                    # المخالفة 3: ميوت 24 ساعة
                    until_time = datetime.now() + timedelta(days=1)
                    bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
                    msg = bot.send_message(
                        chat_id, 
                        f"⏳ <b>تـعـليـق مـؤقـت (24 سـاعـة) !</b>\n\n"
                        f"👤 العضو: <b>{user_name}</b>\n"
                        f"⚠️ تم كتمك لمدة يوم كامل بسبب استمرار الألفاظ السيئة.",
                        parse_mode="HTML"
                    )

                elif violation_count == 4:
                    # المخالفة 4: ميوت 5 أيام
                    until_time = datetime.now() + timedelta(days=5)
                    bot.restrict_chat_member(chat_id, user_id, until_date=until_time, permissions=ChatPermissions(can_send_messages=False))
                    msg = bot.send_message(
                        chat_id, 
                        f"⛔ <b>حـظـر تـفـاعـل (5 أيـام) !</b>\n\n"
                        f"👤 العضو: <b>{user_name}</b>\n"
                        f"🚨 تم منعك من الكتابة لمدة 5 أيام نظراً لتجاهلك التحذيرات.",
                        parse_mode="HTML"
                    )

                else:
                    # المخالفة 5 فما فوق: ميوت إلى الأبد (مدى الحياة) مع زر تواصل أسطوري للمالك
                    bot.restrict_chat_member(chat_id, user_id, permissions=ChatPermissions(can_send_messages=False))
                    
                    # تجهيز نص الاعتذار التلقائي ليضغط عليه العضو مباشرة
                    apology_text = f"السلام عليكم مالك المجموعة، أنا العضو {user_name} وأتأسف على صدور الألفاظ البذيئة مني، أرجو أن تسامحني وتفك عني الميوت وشكراً لك."
                    encoded_text = apology_text.replace(" ", "%20").replace("\n", "%0A")
                    
                    markup = InlineKeyboardMarkup()
                    markup.add(InlineKeyboardButton("🛡️ تواصل مع مالك المجموعة للإعتذار", url=f"https://t.me/an_as1209?text={encoded_text}"))
                    
                    msg = bot.send_message(
                        chat_id, 
                        f"🔒 <b>تـم كـتـم الـعـضـو مـدى الـحـيـاة !</b>\n\n"
                        f"👤 العضو: <b>{user_name}</b>\n"
                        f"❌ لقد تجاوزت الحد الأقصى من المخالفات وتم إسكاتك نهائياً.\n"
                        f"💡 إذا كنت تود الاعتذار وطلب العفو، يمكنك مراسلة مالك المجموعة عبر الزر أدناه 👇",
                        parse_mode="HTML",
                        reply_markup=markup
                    )
            except Exception:
                pass
            return

# ================= أمر فك الميوت المخصص لمالك المجموعة (/unmute) =================
@bot.message_handler(commands=['unmute'])
def owner_unmute_command(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # التأكد أن الامر يُستخدم في الخاص أو المجموعة من طرف الأدمن/المالك
    if not is_admin(chat_id, user_id) and message.chat.type != 'private':
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ يرجى كتابة الآيدي أو المعرف بعد الأمر.\nمثال: `/unmute @user` أو `/unmute 123456789`", parse_mode="Markdown")
        return

    target_query = args[1]
    target_id = None

    # محاولة استخراج الأيدي إذا كتبه مباشرة أو عبر المعرف
    if target_query.isdigit():
        target_id = int(target_query)
    else:
        # إذا كان المعرف يبدأ بـ @، نحتاج لبحث، أو نفترض أن المشرف يرد على رسالته
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id

    if not target_id:
        bot.reply_to(message, "❌ لم أتمكن من التعرف على هذا العضو، يرجى الرد على رسالته أو كتابة الأيدي الصحيح.")
        return

    try:
        # 1. إعادة الصلاحيات للعضو في المجموعة الرئيسية (استبدل -100xxxxxxx باأيدي مجموعتك إن لم تكن في السياق)
        # هنا سنفترض أن المالك يرسلها في المجموعة أو سنقوم بتطبيقها
        target_chat_id = chat_id if message.chat.type != 'private' else -1007454358135 # ضع أيدي مجموعتك هنا إن أردت
        
        bot.restrict_chat_member(
            target_chat_id, 
            target_id, 
            permissions=ChatPermissions(
                can_send_messages=True, 
                can_send_media_messages=True, 
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        
        # تصفير عدد مخالفات العضو ليعود نظيفاً
        if target_id in user_violations:
            user_violations[target_id] = 0

        owner_name = html.escape(message.from_user.first_name)
        
        # رسالة أسطورية في المجموعة تُبقي لمدة 4 ساعات ثم تحذف تلقائياً
        announcement = bot.send_message(
            target_chat_id,
            f"🔓 <b>عـفـو مـلـكـي / فَـك الـحَـظْـر !</b> 🔓\n\n"
            f"✨ تم بفضل الله رفع عقوبة الميوت عن العضو بناءً على عفو وسامح من مالك المجموعة العظيم <b>{owner_name}</b>.\n"
            f"🎉 نرجو الالتزام بقوانين المجموعة وعدم تكرار المخالفة مجدداً!",
            parse_mode="HTML"
        )
        # حذف رسالة الإعلان التلقائي بعد 4 ساعات (4 * 3600 ثانية)
        threading.Timer(14400.0, delete_message_safe, args=(target_chat_id, announcement.message_id)).start()
        
        bot.reply_to(message, "✅ تم فك الميوت عن العضو بنجاح وإرسال الإعلان في المجموعة!")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء فك الميوت: تأكد أن البوت يملك صلاحيات كاملة.\nالتفاصيل: {e}")

# ================= 1. الترحيب ولوحة التحكم =================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        welcome_text = (
            f"⚡ <b>أهلاً بك يا أسطورة</b> ⚡\n\n"
            f"👤 <b>اللاعب:</b> {mention}\n\n"
            f"اختر من القائمة أدناه لاكتشاف ميزات البوت 👇"
        )
        sent_msg = bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=create_main_menu())
        threading.Timer(60.0, delete_message_safe, args=(message.chat.id, sent_msg.message_id)).start()

@bot.message_handler(commands=['help', 'start', 'menu'])
def send_menu(message):
    menu_text = "🕹️ <b>قـائـمـة الـتـحـكـم الـرئـيـسـيـة</b> 🕹️\n\nاختر ما تريد من الأزرار أسفله:"
    bot.send_message(message.chat.id, menu_text, parse_mode="HTML", reply_markup=create_main_menu())
    
    if is_admin(message.chat.id, message.from_user.id):
        admin_text = "⚙️ <b>أوامـر الإدارة (للمشرفين فقط)</b> ⚙️\nيمكنك الرد على أي شخص بـ:\n- <code>/ban</code> (للطرد)\n- <code>/mute</code> (للكتم)\n- <code>/unmute</code> (لإلغاء الكتم)"
        bot.send_message(message.chat.id, admin_text, parse_mode="HTML", reply_markup=create_admin_menu())

# ================= أوامر الإدارة العادية =================
@bot.message_handler(commands=['ban', 'mute'])
def admin_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0].lower()

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمشرفين فقط!")
        return

    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ يرجى الرد على رسالة الشخص الذي تريد تطبيق العقوبة عليه.")
        return

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
        bot.reply_to(message, "❌ حدث خطأ، تأكد أن البوت لديه صلاحيات الإدارة.")

# ================= إضافة التسريبات =================
@bot.message_handler(commands=['setnews'])
def set_news_command(message):
    if not is_admin(message.chat.id, message.from_user.id): 
        return
    
    if message.reply_to_message:
        reply_msg = message.reply_to_message
        if reply_msg.photo:
            latest_leak["photo"] = reply_msg.photo[-1].file_id
            latest_leak["text"] = reply_msg.caption or "🔥 تسريب جديد!"
        else:
            latest_leak["photo"] = None
            latest_leak["text"] = reply_msg.text or "🔥 تسريب جديد!"
        bot.reply_to(message, "✅ تم حفظ التسريب بنجاح! الأعضاء يمكنهم رؤيته الآن عبر الزر.")
    else:
        bot.reply_to(message, "⚠️ لحفظ تسريب: أرسل الصورة واكتب في الوصف `/setnews`، أو قم بالرد على صورة واكتب الأمر.")

@bot.channel_post_handler(func=lambda message: str(message.chat.id) in LEAKS_CHANNEL_ID)
def save_channel_leaks(message):
    if message.photo:
        latest_leak["photo"] = message.photo[-1].file_id
        latest_leak["text"] = message.caption or "🔥 تسريب جديد من فري فاير!"
    elif message.text:
        latest_leak["photo"] = None
        latest_leak["text"] = message.text

# ================= الأزرار التفاعلية =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    if call.data == "menu_squad":
        bot.send_message(chat_id, "للبحث عن فريق، اكتب أمر `/squad` متبوعاً بطلبك.\nمثال: `/squad رانك ماستر`", parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "menu_news":
        text = f"🕵️‍♂️ <b>آخـر الـتـسـريـبـات</b> 🕵️‍♂️\n\n{html.escape(latest_leak['text'])}"
        if latest_leak["photo"]:
            bot.send_photo(chat_id, latest_leak["photo"], caption=text, parse_mode="HTML")
        else:
            bot.send_message(chat_id, text, parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data == "menu_top":
        if not user_xp:
            bot.answer_callback_query(call.id, "📊 لا يوجد تفاعل كافي بعد.", show_alert=True)
            return
        sorted_users = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
        top_text = "🏆 <b>أفـضـل 5 مـتـفـاعـلـيـن</b> 🏆\n\n"
        medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
        for i, (uid, data) in enumerate(sorted_users):
            top_text += f"{medals[i]} <b>{data['name']}</b> - {data['xp']} XP\n"
        bot.send_message(chat_id, top_text, parse_mode="HTML")
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
            bot.answer_callback_query(call.id, "⚠️ انتهت صلاحية التقييم!", show_alert=True)
            return

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
        except Exception: pass

# ================= نشر الخرائط بذكاء =================
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
    if not message.caption: return

    caption_lower = message.caption.lower()
    if "/setnews" in caption_lower or "setnews/" in caption_lower:
        if is_admin(message.chat.id, message.from_user.id):
            latest_leak["photo"] = message.photo[-1].file_id
            clean_text = message.caption.replace("/setnews", "").replace("setnews/", "").strip()
            latest_leak["text"] = clean_text if clean_text else "🔥 تسريب جديد!"
            bot.reply_to(message, "✅ تم حفظ التسريب بنجاح! (لم يتم تحويله لخريطة)")
            return

    add_xp(message.from_user.id, message.from_user.first_name, 50)
    map_type, description_escaped, map_code_escaped = extract_map_data(message.caption)
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
    except Exception as e: print(f"❌ خطأ: {e}")

# ================= الأوامر الأخرى =================
@bot.message_handler(commands=['squad'])
def lfg_command(message):
    request = message.text.replace("/squad", "").strip()
    if not request: return
    user_name = html.escape(message.from_user.first_name)
    lfg_text = f"🎯 <b>طـلـب انـضـمـام</b> 🎯\n\n👤 <b>اللاعب:</b> {user_name}\n💬 <b>الطلب:</b> {html.escape(request)}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💬 تواصل", url=f"tg://user?id={message.from_user.id}"))
    bot.send_message(message.chat.id, lfg_text, parse_mode="HTML", reply_markup=markup)
    delete_message_safe(message.chat.id, message.message_id)

@bot.message_handler(commands=['tour'])
def create_tournament(message):
    if not is_admin(message.chat.id, message.from_user.id): return
    tour_name = message.text.replace("/tour", "").strip() or "بطولة كلاش سكواد"
    msg = bot.send_message(
        message.chat.id, 
        f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour_name)}\n👥 <b>المسجلين:</b> 0\n\nاضغط على الزر للتسجيل!", 
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تسجيل", callback_data="tour_join"))
    )
    tournaments[msg.message_id] = {"name": tour_name, "players": {}}
    delete_message_safe(message.chat.id, message.message_id)


print("⚡ البوت يعمل بنظام العقوبات التصاعدية الأسطوري...")
bot.infinity_polling()
