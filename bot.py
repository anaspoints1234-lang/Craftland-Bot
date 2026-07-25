import re
from datetime import datetime
import html
import threading
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions

# 🔑 ضع توكن البوت الخاص بك هنا
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# قواعد بيانات مؤقتة
ratings_data = {}
media_groups = {}
user_spam_tracker = {}
user_link_violations = {}
bad_word_violations = {}

# قائمة الكلمات الممنوعة (يمكنك التعديل عليها)
BAD_WORDS = ["شتمة1", "شتمة2", "كلمة_نابية"]

def delete_message_safe(chat_id, message_id):
    """دالة لحذف الرسائل بأمان"""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def create_rating_markup():
    """أزرار التقييم"""
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
    """أزرار تفاعلية رئيسية تظهر مع الرسائل"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📜 قوانين المجموعة", callback_data="menu_rules"),
        InlineKeyboardButton("📌 طريقة النشر", callback_data="menu_guide"),
        InlineKeyboardButton("📊 إحصائيات البوت", callback_data="menu_stats"),
        InlineKeyboardButton("🛡️ دعم المجموعة", url="@an_as1209")
    )
    return markup

# ==========================================
# 1. الترحيب الأسطوري بالأعضاء الجدد (التاريخ بدلاً من الوقت)
# ==========================================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        date_today = datetime.now().strftime("%Y-%m-%d")

        welcome_text = (
            f"✧ ━━━━━━━ 👑 <b>تـرحـيـب بـصـنـاع الـحـرف</b> 👑 ━━━━━━━ ✧\n\n"
            f"👤 <b>أهلاً بك يا مبدعنا:</b> {mention}\n"
            f"📅 <b>تاريخ الانضمام:</b> <code>{date_today}</code>\n\n"
            f"لتنشر خريطتك بكل احترافية، نرجو منك اتباع هذا النمط:\n\n"
            f"<code>[اسم الخريطة هنا]</code>\n"
            f"<code>وصف مختصر وواضح لخريطتك</code>\n"
            f"<code>كود: 12345678</code>\n\n"
            f"<i>نتمنى لك وقتاً ممتعاً وإبداعاً لا حدود له!</i>\n"
            f"✧ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ✧"
        )

        sent_msg = bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=create_main_menu_markup()
        )
        threading.Timer(60.0, delete_message_safe, args=(message.chat.id, sent_msg.message_id)).start()

# ==========================================
# 2. الأوامر الجديدة والمساعدة (بهندسة مريحة للعين)
# ==========================================
@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    help_text = (
        f"💡 ━━━━━━━ 📖 <b>دليـلك الشـامـل للنـشـر</b> 📖 ━━━━━━━ 💡\n\n"
        f"خطوات بسيطة لنشر خريطتك لتظهر بأفضل شكل ممكن:\n\n"
        f"1️⃣ قم باختيار أو التقاط <b>صورة واضحة</b> لخريطتك.\n"
        f"2️⃣ انسخ النمط التالي وضعه في وصف الصورة (Caption):\n\n"
        f"<code>[اسم الخريطة]</code>\n"
        f"<code>اكتب وصفاً جذاباً لخريطتك هنا.</code>\n"
        f"<code>كود: 12345678</code>\n\n"
        f"3️⃣ أرسلها وسيتولى البوت ترتيبها وإضافة التقييمات تلقائياً!\n"
        f"💡 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 💡"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="HTML", reply_markup=create_main_menu_markup())

@bot.message_handler(commands=['rules'])
def send_rules(message):
    rules_text = (
        f"⚖️ ━━━━━━━ 📜 <b>دسـتـور الـمـجـمـوعـة</b> 📜 ━━━━━━━ ⚖️\n\n"
        f"أهلاً بك في مجتمعنا، لضمان بيئة رائعة للجميع نرجو الالتزام:\n\n"
        f"🚫 يُمنع منعاً باتاً نشر <b>الروابط الخارجية</b>.\n"
        f"🚫 يُمنع التلفظ بـ <b>الشتائم والكلمات النابية</b>.\n"
        f"🚫 يُمنع <b>التكرار المزعج (السبام)</b> للرسائل.\n"
        f"🎮 المجموعة مخصصة فقط لخرائط لعبة <b>Free Fire</b>.\n"
        f"🤝 <b>الاحترام المتبادل</b> بين الأعضاء هو أساسنا.\n\n"
        f"<i>⚠️ تنويه: مخالفة القوانين تعرضك للكتم التلقائي (الميوت).</i>\n"
        f"⚖️ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ⚖️"
    )
    bot.send_message(message.chat.id, rules_text, parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def send_stats(message):
    stats_text = (
        f"📊 ━━━━━━━ ⚙️ <b>إحـصـائـيـات الـنـظـام</b> ⚙️ ━━━━━━━ 📊\n\n"
        f"🟢 <b>حالة البوت:</b> نشط (Online 24/7)\n"
        f"🛡️ <b>نظام الحماية:</b> فعال (ضد الروابط، السبام، الشتائم)\n"
        f"⚡ <b>سرعة الاستجابة:</b> فورية\n\n"
        f"<i>نعمل دائماً لتقديم أفضل تجربة لصناع الخرائط!</i>\n"
        f"📊 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 📊"
    )
    bot.send_message(message.chat.id, stats_text, parse_mode="HTML")

@bot.message_handler(commands=['admin', 'admins'])
def send_admins(message):
    admin_text = (
        f"🛡️ ━━━━━━━ 👑 <b>إدارة الـمـجـمـوعـة</b> 👑 ━━━━━━━ 🛡️\n\n"
        f"للإبلاغ عن مشكلة، اقتراح، أو استفسار..\n"
        f"يرجى التواصل مع مشرفي المجموعة المتواجدين في قائمة الأعضاء.\n"
        f"نحن هنا دائماً لخدمتكم!\n\n"
        f"🛡️ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🛡️"
    )
    bot.send_message(message.chat.id, admin_text, parse_mode="HTML")

@bot.message_handler(commands=['id'])
def send_user_id(message):
    user = message.from_user
    id_text = (
        f"🆔 <b>بطاقتك الشخصية:</b>\n\n"
        f"👤 <b>الاسم:</b> {html.escape(user.first_name)}\n"
        f"🔢 <b>الأيدي:</b> <code>{user.id}</code>"
    )
    bot.reply_to(message, id_text, parse_mode="HTML")

# معالجة الأزرار التفاعلية الجديدة
@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def callback_menu(call):
    if call.data == "menu_rules":
        rules_alert = "قوانين المجموعة باختصار:\n1. لا روابط خارجية.\n2. لا للشتائم والسبام.\n3. احترام الجميع."
        bot.answer_callback_query(call.id, rules_alert, show_alert=True)
    elif call.data == "menu_guide":
        guide_alert = "نموذج النشر:\n\n[اسم الخريطة]\nوصف الخريطة\nكود: 12345678"
        bot.answer_callback_query(call.id, guide_alert, show_alert=True)
    elif call.data == "menu_stats":
        bot.answer_callback_query(call.id, "✅ البوت يعمل بكفاءة تامة وحماية قصوى لحمايتكم!", show_alert=True)

# ==========================================
# 3. نظام الحماية الذكي الشامل (ميوت دقيقة واحدة للجميع)
# ==========================================
def check_security(message):
    if not message.from_user or message.chat.type == 'private':
        return False
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text_content = message.text or message.caption or ""
    text_lower = text_content.lower()
    first_name = html.escape(message.from_user.first_name)

    # أ. فلتر الكلمات البذيئة والشتائم
    for bad_word in BAD_WORDS:
        if bad_word in text_lower:
            delete_message_safe(chat_id, message.message_id)
            if user_id not in bad_word_violations:
                bad_word_violations[user_id] = 0
            bad_word_violations[user_id] += 1
            
            if bad_word_violations[user_id] == 1:
                warn_text = f"⚠️ <b>⌊ تنبيه أولي ⌉</b> يا {first_name}، يُمنع استخدام الكلمات غير اللائقة هنا."
                warn = bot.send_message(chat_id, warn_text, parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            else:
                try:
                    now = datetime.now().timestamp()
                    # ميوت لمدة دقيقة (60 ثانية)
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 60), permissions=ChatPermissions(can_send_messages=False))
                    warn_text = f"⛔ <b>⌊ تـم الـكـتـم ⌉</b> تم كتم العضو {first_name} لمدة <b>دقيقة واحدة</b> لتكراره الألفاظ النابية."
                    warn = bot.send_message(chat_id, warn_text, parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception:
                    pass
            return True

    # ب. فحص الروابط الخارجية
    if "http://" in text_content or "https://" in text_content or "www." in text_content:
        allowed_domains = ["t.me", "youtube.com", "youtu.be", "whatsapp.com", "wa.me", "instagram.com", "tiktok.com"]
        is_allowed = any(domain in text_content for domain in allowed_domains)
        
        if not is_allowed:
            delete_message_safe(chat_id, message.message_id)
            
            if user_id not in user_link_violations:
                user_link_violations[user_id] = 0
            
            user_link_violations[user_id] += 1
            violations_count = user_link_violations[user_id]
            
            if violations_count == 1:
                warn_text = f"⚠️ <b>⌊ تنبيه أولي ⌉</b> يا {first_name}، يُمنع نشر الروابط الخارجية."
                warn = bot.send_message(chat_id, warn_text, parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            elif violations_count == 2:
                try:
                    now = datetime.now().timestamp()
                    # ميوت لمدة دقيقة (60 ثانية)
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 60), permissions=ChatPermissions(can_send_messages=False))
                    warn_text = f"⛔ <b>⌊ تـم الـكـتـم ⌉</b> تم كتم العضو {first_name} لمدة <b>دقيقة واحدة</b> لتكرار نشر الروابط المخالفة."
                    warn = bot.send_message(chat_id, warn_text, parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception:
                    pass
            else:
                try:
                    # باند / كتم نهائي في المرة الثالثة
                    bot.restrict_chat_member(chat_id, user_id, until_date=0, permissions=ChatPermissions(can_send_messages=False))
                    warn_text = f"🚫 <b>⌊ حـظـر نـهـائـي ⌉</b> تم كتم العضو {first_name} <b>مدى الحياة</b> لإصراره على نشر الروابط!"
                    bot.send_message(chat_id, warn_text, parse_mode="HTML")
                except Exception:
                    pass
            return True

    # ج. نظام السبام: تكرار نفس الرسالة 4 مرات في مدة 15 ثانية
    now = datetime.now().timestamp()
    if user_id not in user_spam_tracker:
        user_spam_tracker[user_id] = {}
    
    user_data = user_spam_tracker[user_id]
    
    if not text_content.strip():
        return False

    if text_content not in user_data:
        user_data[text_content] = []
    
    user_data[text_content] = [t for t in user_data[text_content] if (now - t) < 15.0]
    user_data[text_content].append(now)
    
    if len(user_data[text_content]) >= 4:
        try:
            delete_message_safe(chat_id, message.message_id)
            # ميوت لمدة دقيقة (60 ثانية)
            bot.restrict_chat_member(
                chat_id, 
                user_id, 
                until_date=int(now + 60),
                permissions=ChatPermissions(can_send_messages=False)
            )
            warn_text = f"⛔ <b>⌊ تـم الـكـتـم ⌉</b> تم كتم العضو {first_name} لمدة <b>دقيقة واحدة</b> بسبب التكرار المزعج (سبام)."
            warning_msg = bot.send_message(chat_id, warn_text, parse_mode="HTML")
            threading.Timer(10.0, delete_message_safe, args=(chat_id, warning_msg.message_id)).start()
        except Exception:
            pass
            
        user_data[text_content] = []
        return True
        
    return False

# ==========================================
# 4. معالجة ونشر الخرائط بالتصميم المقسم الجديد
# ==========================================
@bot.message_handler(content_types=["photo"])
def handle_craftland_map(message):
    if check_security(message):
        return

    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in media_groups:
            media_groups[mg_id] = {'messages': [], 'timer': None}
        
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
    
    match = re.search(r"\[(.*?)\]", caption)
    if not match: return

    map_type = html.escape(match.group(1).strip())
    raw_body = caption.replace(f"[{match.group(1)}]", "").strip()
    
    code_match = re.search(r"(كود[:：]?\s*([A-Za-z0-9#\-_]+))", raw_body, re.IGNORECASE)
    if code_match:
        map_code = code_match.group(2).strip()
        description = raw_body.replace(code_match.group(1), "").strip()
    else:
        map_code = "غير متوفر"
        description = raw_body

    description_escaped = html.escape(description)
    map_code_escaped = html.escape(map_code)

    creator_name = html.escape(messages[0].from_user.first_name)
    username = f"@{messages[0].from_user.username}" if messages[0].from_user.username else ""

    formatted_text = (
        f"╔══════ 🏷️ <b>اسم الخريطة</b> ══════╗\n"
        f"  <b>{map_type}</b>\n"
        f"╚═══════════════════════════╝\n\n"
        f"╔══════ 📝 <b>وصف الخريطة</b> ══════╗\n"
        f"  {description_escaped}\n"
        f"╚═══════════════════════════╝\n\n"
        f"╔══════ 🔑 <b>كود الخريطة</b> ══════╗\n"
        f"  <code>{map_code_escaped}</code>\n"
        f"╚═══════════════════════════╝\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>بواسطة:</b> {creator_name} {username}"
    )

    media = []
    for i, msg in enumerate(messages):
        photo_id = msg.photo[-1].file_id
        if i == 0:
            media.append(InputMediaPhoto(photo_id, caption=formatted_text, parse_mode="HTML"))
        else:
            media.append(InputMediaPhoto(photo_id))
            
    chat_id = messages[0].chat.id
    
    try:
        sent_messages = bot.send_media_group(chat_id, media)
        
        base_rate_text = f"⭐ <b>التقييمات:</b> "
        full_rate_text = base_rate_text + "0.0/5 (0 أصوات)"
        
        rate_msg = bot.send_message(
            chat_id,
            full_rate_text,
            reply_to_message_id=sent_messages[0].message_id,
            parse_mode="HTML",
            reply_markup=create_rating_markup()
        )
        
        ratings_data[rate_msg.message_id] = {"base_text": base_rate_text, "votes": {}, "is_caption": False}
        
        for msg in messages:
            delete_message_safe(chat_id, msg.message_id)
            
    except Exception as e:
        print(f"❌ خطأ: {e}")

def process_single_map(message):
    caption = message.caption or ""
    match = re.search(r"\[(.*?)\]", caption)
    
    if not match: return

    map_type = html.escape(match.group(1).strip())
    raw_body = caption.replace(f"[{match.group(1)}]", "").strip()
    
    code_match = re.search(r"(كود[:：]?\s*([A-Za-z0-9#\-_]+))", raw_body, re.IGNORECASE)
    if code_match:
        map_code = code_match.group(2).strip()
        description = raw_body.replace(code_match.group(1), "").strip()
    else:
        map_code = "غير متوفر"
        description = raw_body

    description_escaped = html.escape(description)
    map_code_escaped = html.escape(map_code)

    creator_name = html.escape(message.from_user.first_name)
    username = f"@{message.from_user.username}" if message.from_user.username else ""

    base_caption = (
        f"╔══════ 🏷️ <b>اسم الخريطة</b> ══════╗\n"
        f"  <b>{map_type}</b>\n"
        f"╚═══════════════════════════╝\n\n"
        f"╔══════ 📝 <b>وصف الخريطة</b> ══════╗\n"
        f"  {description_escaped}\n"
        f"╚═══════════════════════════╝\n\n"
        f"╔══════ 🔑 <b>كود الخريطة</b> ══════╗\n"
        f"  <code>{map_code_escaped}</code>\n"
        f"╚═══════════════════════════╝\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>بواسطة:</b> {creator_name} {username}\n"
        f"⭐ <b>التقييمات:</b> "
    )
    
    full_caption = base_caption + "0.0/5 (0 أصوات)"
    
    try:
        sent_msg = bot.send_photo(
            message.chat.id,
            message.photo[-1].file_id,
            caption=full_caption,
            parse_mode="HTML",
            reply_markup=create_rating_markup()
        )
        
        delete_message_safe(message.chat.id, message.message_id)
        ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

# ==========================================
# 5. معالجة التقييمات
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating(call):
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
        if data["is_caption"]:
            bot.edit_message_caption(
                caption=updated_text,
                chat_id=call.message.chat.id,
                message_id=msg_id,
                parse_mode="HTML",
                reply_markup=call.message.reply_markup
            )
        else:
            bot.edit_message_text(
                text=updated_text,
                chat_id=call.message.chat.id,
                message_id=msg_id,
                parse_mode="HTML",
                reply_markup=call.message.reply_markup
            )
        bot.answer_callback_query(call.id, f"✅ تم حفظ تقييمك: {rating_val} نجوم")
    except Exception:
        bot.answer_callback_query(call.id, f"✅ تم الحفظ!")

print("⚡ البوت المطور بالأشكال الأسطورية والميوت المنظم يعمل الآن...")
bot.infinity_polling()
