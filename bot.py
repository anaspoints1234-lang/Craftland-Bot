import re
from datetime import datetime
import threading
import html
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 ضع توكن البوت الخاص بك هنا
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# 📡 أيدي قناة التسريبات
LEAKS_CHANNEL_ID = ["7454358135", "-1007454358135"]

# ================= قواعد البيانات المؤقتة =================
ratings_data = {}
media_groups = {}
user_spam_tracker = {}
user_xp = {}  
tournaments = {} 
latest_leak = {"text": "لم يتم إضافة أي تسريبات بعد! 🕵️‍♂️", "photo": None}

BAD_WORDS = ["شتمة1", "شتمة2", "كلمة_نابية"]

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

# ================= لوحات الأزرار (القوائم) =================
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
        InlineKeyboardButton("🛡️ دعم المجموعة", url="https://t.me/YourSupportUsername")
    )
    return markup

def create_admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🏆 إنشاء بطولة", callback_data="admin_tour"),
        InlineKeyboardButton("🗑️ حذف الرسالة", callback_data="admin_delete")
    )
    return markup

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
    
    # إذا كان المستخدم أدمن، نرسل له أزرار الإدارة المخفية
    if is_admin(message.chat.id, message.from_user.id):
        admin_text = "⚙️ <b>أوامـر الإدارة (للمشرفين فقط)</b> ⚙️\nيمكنك الرد على أي شخص بـ:\n- <code>/ban</code> (للطرد)\n- <code>/mute</code> (للكتم)\n- <code>/unmute</code> (لإلغاء الكتم)"
        bot.send_message(message.chat.id, admin_text, parse_mode="HTML", reply_markup=create_admin_menu())

# ================= 2. أوامر الإدارة (للمشرفين فقط) =================
@bot.message_handler(commands=['ban', 'mute', 'unmute', 'setnews'])
def admin_commands(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    command = message.text.split()[0].lower()

    if not is_admin(chat_id, user_id):
        bot.reply_to(message, "⚠️ هذا الأمر مخصص للمشرفين فقط!")
        return

    # أمر تحديد التسريبات يدوياً
    if command == '/setnews':
        if not message.reply_to_message:
            bot.reply_to(message, "⚠️ قم بالرد على رسالة أو صورة واكتب `/setnews` لجعلها التسريب الحالي.", parse_mode="Markdown")
            return
        
        reply_msg = message.reply_to_message
        if reply_msg.photo:
            latest_leak["photo"] = reply_msg.photo[-1].file_id
            latest_leak["text"] = reply_msg.caption or "🔥 تسريب جديد!"
        else:
            latest_leak["photo"] = None
            latest_leak["text"] = reply_msg.text
        bot.reply_to(message, "✅ تم تحديث التسريبات بنجاح! يمكن للأعضاء رؤيتها الآن عبر الأزرار.")
        return

    # أوامر العقوبات (تتطلب الرد على رسالة العضو)
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
            
        elif command == '/unmute':
            bot.restrict_chat_member(chat_id, target_id, permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True))
            bot.reply_to(message, f"🔊 تم إلغاء كتم <b>{html.escape(target_name)}</b>.", parse_mode="HTML")
            
    except Exception as e:
        bot.reply_to(message, "❌ حدث خطأ، تأكد أن البوت لديه صلاحيات الإدارة.")

# ================= 3. استقبال التسريبات من القناة =================
@bot.channel_post_handler(func=lambda message: str(message.chat.id) in LEAKS_CHANNEL_ID)
def save_channel_leaks(message):
    if message.photo:
        latest_leak["photo"] = message.photo[-1].file_id
        latest_leak["text"] = message.caption or "🔥 تسريب جديد من فري فاير!"
    elif message.text:
        latest_leak["photo"] = None
        latest_leak["text"] = message.text

# ================= 4. الاستجابة للأزرار (القوائم التفاعلية) =================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    user_id = call.from_user.id

    # أزرار قائمة الأعضاء
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

    # أزرار الإدارة
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

    # زر التسجيل في البطولات
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

    # أزرار التقييم
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

# ================= 5. استخراج ونشر الخرائط =================
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

# ================= أوامر باقية (البحث عن سكواد والبطولات) =================
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


print("⚡ البوت يعمل الآن بنظام الأزرار والأدمن...")
bot.infinity_polling()
