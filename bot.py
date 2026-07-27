import re
from datetime import datetime
import threading
import html
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 ضع توكن البوت الخاص بك هنا
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# 📡 أيدي قناة التسريبات (غالباً قنوات التلجرام تبدأ بـ -100، إذا لم يعمل أضف -100 للرقم)
LEAKS_CHANNEL_ID = ["7454358135", "-1007454358135"]

# ================= قواعد البيانات المؤقتة =================
ratings_data = {}
media_groups = {}
user_spam_tracker = {}
user_link_violations = {}
bad_word_violations = {}
user_xp = {}  # نظام المستويات والنقاط
tournaments = {} # تسجيل البطولات
latest_leak = {"text": "لم يتم نشر أي تسريبات جديدة بعد! 🕵️‍♂️", "photo": None}

BAD_WORDS = ["شتمة1", "شتمة2", "كلمة_نابية"]

# ================= دوال المساعدة =================
def delete_message_safe(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def add_xp(user_id, name, amount):
    """إضافة نقاط XP للعضو"""
    if user_id not in user_xp:
        user_xp[user_id] = {"name": name, "xp": 0}
    user_xp[user_id]["xp"] += amount

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

def create_main_menu_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📜 القوانين", callback_data="menu_rules"),
        InlineKeyboardButton("🏆 أفضل اللاعبين", callback_data="menu_top"),
        InlineKeyboardButton("🔥 آخر التسريبات", callback_data="menu_news"),
        InlineKeyboardButton("🛡️ الدعم", url="https://t.me/an_as1209")
    )
    return markup

# ================= 1. الترحيب والأوامر الأساسية =================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        date_today = datetime.now().strftime("%Y-%m-%d")
        welcome_text = (
            f"✧ ━━━━━━━ 👑 <b>تـرحـيـب بـالأبـطـال</b> 👑 ━━━━━━━ ✧\n\n"
            f"👤 <b>أهلاً بك يا أسطورة:</b> {mention}\n"
            f"📅 <b>تاريخ الانضمام:</b> <code>{date_today}</code>\n\n"
            f"شاركنا إبداعك في خرائط Craftland أو ابحث عن سكواد للرانك!\n"
            f"للمساعدة اكتب: <code>/help</code>\n\n"
            f"✧ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ✧"
        )
        sent_msg = bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=create_main_menu_markup())
        threading.Timer(60.0, delete_message_safe, args=(message.chat.id, sent_msg.message_id)).start()

@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    help_text = (
        f"💡 ━━━━━━━ 📖 <b>دليـل بـوت FREE FIRE MAX</b> 📖 ━━━━━━━ 💡\n\n"
        f"🔸 <b>لنشر خريطة:</b> أرسل صورة واكتب الكود والوصف.\n"
        f"🔸 <b>/squad [طلبك]:</b> للبحث عن لاعبين (مثال: /squad رانك ماستر).\n"
        f"🔸 <b>/wiki [اسم]:</b> معلومات عن سلاح أو شخصية (مثال: /wiki الوك).\n"
        f"🔸 <b>/news :</b> لمعرفة آخر تسريبات اللعبة.\n"
        f"🔸 <b>/top :</b> لرؤية أقوى المتفاعلين في المجموعة.\n\n"
        f"💡 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 💡"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

# ================= 2. الميزات الجديدة (MAX Features) =================

# --- أ. نظام البحث عن سكواد (LFG) ---
@bot.message_handler(commands=['squad'])
def lfg_command(message):
    request = message.text.replace("/squad", "").strip()
    if not request:
        bot.reply_to(message, "⚠️ يرجى كتابة طلبك. مثال: `/squad خاصني واحد كيلعب كلاش سكواد`", parse_mode="Markdown")
        return
    
    user_name = html.escape(message.from_user.first_name)
    lfg_text = (
        f"🔥 <b>طـلـب انـضـمـام لـسـكـواد</b> 🔥\n\n"
        f"👤 <b>اللاعب:</b> {user_name}\n"
        f"🎯 <b>الطلب:</b> {html.escape(request)}\n\n"
        f"<i>اضغط على الزر بالأسفل للتواصل معه!</i>"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💬 تواصل مع اللاعب", url=f"tg://user?id={message.from_user.id}"))
    bot.send_message(message.chat.id, lfg_text, parse_mode="HTML", reply_markup=markup)
    delete_message_safe(message.chat.id, message.message_id)

# --- ب. البطولات والرومات (خاص بالأدمنز) ---
@bot.message_handler(commands=['tour'])
def create_tournament(message):
    # يمكنك إضافة تحقق من أن المستخدم أدمن هنا
    tour_name = message.text.replace("/tour", "").strip() or "بطولة فري فاير الكبرى"
    msg = bot.send_message(
        message.chat.id, 
        f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n"
        f"⚔️ <b>البطولة:</b> {html.escape(tour_name)}\n"
        f"👥 <b>المسجلين:</b> 0\n\n"
        f"اضغط على الزر للتسجيل!", 
        parse_mode="HTML", 
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ تسجيل", callback_data="tour_join"))
    )
    tournaments[msg.message_id] = {"name": tour_name, "players": {}}
    delete_message_safe(message.chat.id, message.message_id)

# --- ج. موسوعة اللعبة ---
@bot.message_handler(commands=['wiki'])
def wiki_command(message):
    query = message.text.replace("/wiki", "").strip().lower()
    wiki_data = {
        "الوك": "🟢 **ألوك (Alok):**\nمهارة (Drop the Beat): ينشئ هالة تزيد سرعة الحركة وتعالج HP. ممتاز للرشر!",
        "كيلي": "🏃‍♀️ **كيلي (Kelly):**\nمهارة (Dash): زيادة سرعة الركض. شخصية أساسية في أي كومبو.",
        "m1887": "🔫 **M1887 (شوتغن):**\nدمج أسطوري عن قرب. طلقتين كافيتين لإسقاط الخصم إذا كانت الإيم دقيقة.",
        "mp40": "🔫 **MP40 (رشاش):**\nأسرع سلاح في اللعبة من ناحية معدل إطلاق النار (Rate of Fire). مميت في المدى القريب."
    }
    for key, val in wiki_data.items():
        if key in query:
            bot.reply_to(message, val, parse_mode="Markdown")
            return
    bot.reply_to(message, "⚠️ لم أجد هذه الشخصية أو السلاح. جرب: الوك، كيلي، M1887، MP40.")

# --- د. نظام المستويات والـ Top ---
@bot.message_handler(commands=['top'])
def top_players(message):
    if not user_xp:
        bot.reply_to(message, "📊 لا يوجد تفاعل كافي بعد لعرض التصنيف.")
        return
    sorted_users = sorted(user_xp.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
    top_text = "🏆 <b>أفـضـل 5 لاعـبـيـن فـي الـمـجـمـوعـة</b> 🏆\n\n"
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    for i, (uid, data) in enumerate(sorted_users):
        top_text += f"{medals[i]} <b>{data['name']}</b> - {data['xp']} XP\n"
    bot.send_message(message.chat.id, top_text, parse_mode="HTML")

# --- هـ. نظام التسريبات من القناة ---
@bot.channel_post_handler(func=lambda message: str(message.chat.id) in LEAKS_CHANNEL_ID)
def save_channel_leaks(message):
    """يحفظ آخر تسريب يتم نشره في قناتك"""
    if message.photo:
        latest_leak["photo"] = message.photo[-1].file_id
        latest_leak["text"] = message.caption or "🔥 تسريب جديد من فري فاير!"
    elif message.text:
        latest_leak["photo"] = None
        latest_leak["text"] = message.text

@bot.message_handler(commands=['news'])
def show_news(message):
    text = f"🕵️‍♂️ <b>آخـر تـسـريـبـات فـري فـايـر</b> 🕵️‍♂️\n\n{html.escape(latest_leak['text'])}"
    if latest_leak["photo"]:
        bot.send_photo(message.chat.id, latest_leak["photo"], caption=text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, text, parse_mode="HTML")

# ================= 3. الحماية الذكية (ميوت دقيقة) =================
def check_security(message):
    if not message.from_user or message.chat.type == 'private': return False
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text_content = message.text or message.caption or ""
    text_lower = text_content.lower()
    first_name = html.escape(message.from_user.first_name)

    add_xp(user_id, first_name, 1) # نقطة على كل رسالة عادية

    # 1. فلتر الكلمات البذيئة
    for bad_word in BAD_WORDS:
        if bad_word in text_lower:
            delete_message_safe(chat_id, message.message_id)
            if user_id not in bad_word_violations: bad_word_violations[user_id] = 0
            bad_word_violations[user_id] += 1
            if bad_word_violations[user_id] == 1:
                warn = bot.send_message(chat_id, f"⚠️ <b>⌊ تنبيه أولي ⌉</b> يا {first_name}، يُمنع الشتم.", parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            else:
                try:
                    now = datetime.now().timestamp()
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 60), permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"⛔ تم كتم {first_name} لـ <b>دقيقة</b> بسبب الشتائم.", parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception: pass
            return True

    # 2. فلتر الروابط
    if "http://" in text_content or "https://" in text_content or "www." in text_content:
        allowed = ["t.me", "youtube.com", "youtu.be", "whatsapp.com"]
        if not any(domain in text_content for domain in allowed):
            delete_message_safe(chat_id, message.message_id)
            if user_id not in user_link_violations: user_link_violations[user_id] = 0
            user_link_violations[user_id] += 1
            if user_link_violations[user_id] == 1:
                warn = bot.send_message(chat_id, f"⚠️ <b>⌊ تنبيه أولي ⌉</b> يُمنع نشر الروابط يا {first_name}.", parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            else:
                try:
                    now = datetime.now().timestamp()
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 60), permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"⛔ تم كتم {first_name} لـ <b>دقيقة</b> لتكرار الروابط.", parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception: pass
            return True

    # 3. نظام السبام
    now = datetime.now().timestamp()
    if user_id not in user_spam_tracker: user_spam_tracker[user_id] = {}
    user_data = user_spam_tracker[user_id]
    if not text_content.strip(): return False
    if text_content not in user_data: user_data[text_content] = []
    user_data[text_content] = [t for t in user_data[text_content] if (now - t) < 15.0]
    user_data[text_content].append(now)
    
    if len(user_data[text_content]) >= 4:
        try:
            delete_message_safe(chat_id, message.message_id)
            bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 60), permissions=ChatPermissions(can_send_messages=False))
            warn = bot.send_message(chat_id, f"⛔ تم كتم {first_name} لـ <b>دقيقة</b> بسبب السبام.", parse_mode="HTML")
            threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
        except Exception: pass
        user_data[text_content] = []
        return True
    return False

# ================= 4. استخراج الخرائط (الدالة الذكية الجديدة) =================
def extract_map_data(caption):
    match = re.search(r"\[(.*?)\]", caption)
    if match:
        map_type = html.escape(match.group(1).strip())
        raw_body = caption.replace(f"[{match.group(1)}]", "").strip()
    else:
        lines = caption.strip().split('\n')
        map_type = html.escape(lines[0].strip()) if lines else "خريطة فري فاير"
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
    if check_security(message): return
    if not message.caption: return

    # نعطي صاحب الخريطة 50 نقطة XP
    add_xp(message.from_user.id, message.from_user.first_name, 50)

    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in media_groups: media_groups[mg_id] = {'messages': [], 'timer': None}
        media_groups[mg_id]['messages'].append(message)
        if not media_groups[mg_id]['timer']:
            timer = threading.Timer(2.0, process_media_group, args=[mg_id])
            media_groups[mg_id]['timer'] = timer
            timer.start()
    else:
        process_single_map(message)

def process_media_group(mg_id):
    if mg_id not in media_groups: return
    group = media_groups.pop(mg_id)
    messages = group['messages']
    caption_msg = next((msg for msg in messages if msg.caption), None)
    caption = caption_msg.caption if caption_msg else ""
    if not caption.strip(): return 

    map_type, description_escaped, map_code_escaped = extract_map_data(caption)
    creator_name = html.escape(messages[0].from_user.first_name)

    formatted_text = (
        f"╔══════ 🏷️ <b>اسم الخريطة</b> ══════╗\n  <b>{map_type}</b>\n╚═══════════════════════════╝\n\n"
        f"╔══════ 📝 <b>وصف الخريطة</b> ══════╗\n  {description_escaped}\n╚═══════════════════════════╝\n\n"
        f"╔══════ 🔑 <b>كود الخريطة</b> ══════╗\n  <code>{map_code_escaped}</code>\n╚═══════════════════════════╝\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n👤 <b>بواسطة:</b> {creator_name}"
    )

    media = []
    for i, msg in enumerate(messages):
        photo_id = msg.photo[-1].file_id
        if i == 0: media.append(InputMediaPhoto(photo_id, caption=formatted_text, parse_mode="HTML"))
        else: media.append(InputMediaPhoto(photo_id))
            
    chat_id = messages[0].chat.id
    try:
        sent_messages = bot.send_media_group(chat_id, media)
        base_rate_text = f"⭐ <b>التقييمات:</b> "
        rate_msg = bot.send_message(chat_id, base_rate_text + "0.0/5 (0 أصوات)", reply_to_message_id=sent_messages[0].message_id, parse_mode="HTML", reply_markup=create_rating_markup())
        ratings_data[rate_msg.message_id] = {"base_text": base_rate_text, "votes": {}, "is_caption": False}
        for msg in messages: delete_message_safe(chat_id, msg.message_id)
    except Exception as e: print(f"❌ خطأ: {e}")

def process_single_map(message):
    caption = message.caption or ""
    if not caption.strip(): return 

    map_type, description_escaped, map_code_escaped = extract_map_data(caption)
    creator_name = html.escape(message.from_user.first_name)

    base_caption = (
        f"╔══════ 🏷️ <b>اسم الخريطة</b> ══════╗\n  <b>{map_type}</b>\n╚═══════════════════════════╝\n\n"
        f"╔══════ 📝 <b>وصف الخريطة</b> ══════╗\n  {description_escaped}\n╚═══════════════════════════╝\n\n"
        f"╔══════ 🔑 <b>كود الخريطة</b> ══════╗\n  <code>{map_code_escaped}</code>\n╚═══════════════════════════╝\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n👤 <b>بواسطة:</b> {creator_name}\n⭐ <b>التقييمات:</b> "
    )
    
    try:
        sent_msg = bot.send_photo(message.chat.id, message.photo[-1].file_id, caption=base_caption + "0.0/5 (0 أصوات)", parse_mode="HTML", reply_markup=create_rating_markup())
        delete_message_safe(message.chat.id, message.message_id)
        ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
    except Exception as e: print(f"❌ خطأ: {e}")

# ================= 5. معالجة الأزرار (Callbacks) =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # أزرار القائمة الرئيسية
    if call.data.startswith("menu_"):
        if call.data == "menu_rules":
            bot.answer_callback_query(call.id, "قوانين: لا شتائم، لا روابط، لا سبام. احترام الجميع واجب!", show_alert=True)
        elif call.data == "menu_top":
            bot.answer_callback_query(call.id, "اكتب /top في المجموعة لترى أفضل اللاعبين المتفاعلين!", show_alert=True)
        elif call.data == "menu_news":
            bot.answer_callback_query(call.id, "اكتب /news في المجموعة لرؤية أحدث تسريبات فري فاير!", show_alert=True)
            
    # زر التسجيل في البطولات
    elif call.data == "tour_join":
        msg_id = call.message.message_id
        user_id = call.from_user.id
        user_name = call.from_user.first_name
        if msg_id in tournaments:
            tour = tournaments[msg_id]
            if user_id not in tour["players"]:
                tour["players"][user_id] = user_name
                count = len(tour["players"])
                updated_text = f"🏆 <b>تـسـجـيـل الـبـطـولـة مـفـتـوح</b> 🏆\n\n⚔️ <b>البطولة:</b> {html.escape(tour['name'])}\n👥 <b>المسجلين:</b> {count}\n\nاضغط على الزر للتسجيل!"
                bot.edit_message_text(text=updated_text, chat_id=call.message.chat.id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
                bot.answer_callback_query(call.id, "✅ تم تسجيلك بنجاح في البطولة!")
            else:
                bot.answer_callback_query(call.id, "⚠️ أنت مسجل مسبقاً!")

    # أزرار التقييم
    elif call.data.startswith("rate_"):
        msg_id = call.message.message_id
        user_id = call.from_user.id
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
            if data["is_caption"]: bot.edit_message_caption(caption=updated_text, chat_id=call.message.chat.id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            else: bot.edit_message_text(text=updated_text, chat_id=call.message.chat.id, message_id=msg_id, parse_mode="HTML", reply_markup=call.message.reply_markup)
            bot.answer_callback_query(call.id, f"✅ تم حفظ تقييمك: {rating_val} نجوم")
        except Exception: pass


# تشغيل البوت
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    check_security(message)

print("⚡ بوت FREE FIRE MAX يعمل الآن بكامل الميزات...")
bot.infinity_polling()
