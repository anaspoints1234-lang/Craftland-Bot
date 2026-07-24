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


# ==========================================
# 1. الترحيب الأسطوري بالأعضاء الجدد (شكل هندسي جديد)
# ==========================================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        time_now = datetime.now().strftime("%I:%M %p")

        welcome_text = (
            f"╭─── 👑 <b>تَـرْحِـيـب بـَصُـنَّـاعِ الـحَـرَفْ</b> ───╮\n"
            f"│\n"
            f"│ 👤 <b>أهلاً بك:</b> {mention}\n"
            f"│ ⏰ <b>الوقت:</b> <code>{time_now}</code>\n"
            f"│\n"
            f"┝──────── 📌 <b>طريقة النشر</b> ────────┥\n"
            f"│ <code>[اسم الخريطة]</code>\n"
            f"│ \n"
            f"│ <code>وصف الخريطة</code>\n"
            f"│ <code>كود: 12345678</code>\n"
            f"╰─────────────────────────╯\n"
            f"⏳ <i>(ستُحذف هذه الرسالة تلقائياً)</i>"
        )

        sent_msg = bot.send_message(
            message.chat.id,
            welcome_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        threading.Timer(60.0, delete_message_safe, args=(message.chat.id, sent_msg.message_id)).start()


# ==========================================
# 2. الأوامر المساعدة (/help, /rules, /stats)
# ==========================================
@bot.message_handler(commands=['help', 'start'])
def send_help(message):
    help_text = (
        f"╭─── 📖 <b>دَلِيلُ صُنّاعْ أرْضِ الحَرَفْ</b> ───╮\n"
        f"│\n"
        f"│ 1️⃣ جهز صورة لخريطتك.\n"
        f"│ 2️⃣ اكتب التفاصيل بهذا الشكل الدقيق:\n"
        f"│\n"
        f"│ <code>[اسم الخريطة]</code>\n"
        f"│ \n"
        f"│ <code>وصف الخريطة</code>\n"
        f"│ <code>كود: 123456</code>\n"
        f"│\n"
        f"│ 3️⃣ أرسلها وسيقوم البوت بتنسيقها!\n"
        f"╰───────────────────────╯"
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📌 عرض طريقة النشر السريعة", callback_data="show_guide"))
    bot.send_message(message.chat.id, help_text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=['rules'])
def send_rules(message):
    rules_text = (
        f"╭─── 📜 <b>قَوَانِينُ المَجْمُوعَةِ</b> ───╮\n"
        f"│\n"
        f"│ 🚫 يمنع نشر الروابط الخارجية المخالفة.\n"
        f"│ 🚫 يمنع السبام والتكرار (يعاقب بالميوت).\n"
        f"│ 🤝 احترام جميع الأعضاء وصناع الخرائط.\n"
        f"│ 🎮 الالتزام بنشر خرائط Free Fire فقط.\n"
        f"│\n"
        f"╰───────────────────╯"
    )
    bot.send_message(message.chat.id, rules_text, parse_mode="HTML")


@bot.message_handler(commands=['stats'])
def send_stats(message):
    stats_text = (
        f"╭─── 📊 <b>إِحْصَائِياتُ نِظَامِ البُوتِ</b> ───╮\n"
        f"│\n"
        f"│ 🟢 <b>الحالة:</b> Online 24/7\n"
        f"│ 🛡️ <b>الحماية:</b> Anti-Spam & Anti-Link\n"
        f"│ ⚡ <b>الاستجابة:</b> فورية\n"
        f"│\n"
        f"╰─────────────────────╯"
    )
    bot.send_message(message.chat.id, stats_text, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "show_guide")
def callback_guide(call):
    guide_alert = (
        "[اسم الخريطة]\n\n"
        "وصف الخريطة\n"
        "كود: 12345678"
    )
    bot.answer_callback_query(call.id, guide_alert, show_alert=True)


# ==========================================
# 3. نظام الحماية الذكي
# ==========================================
def check_security(message):
    if not message.from_user or message.chat.type == 'private':
        return False
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text_content = message.text or message.caption or ""
    
    # فحص الروابط الخارجية
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
                warn = bot.send_message(chat_id, f"⚠️ تنبيه يا {message.from_user.first_name}! ممنوع نشر الروابط الخارجية. (التحذير الأول)", parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            elif violations_count == 2:
                try:
                    now = datetime.now().timestamp()
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 600), permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"🚫 تم كتم العضو {message.from_user.first_name} لمدة 10 دقائق لتكراره إرسال روابط مخالفة!", parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception:
                    pass
            else:
                try:
                    bot.restrict_chat_member(chat_id, user_id, until_date=0, permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"⛔ تم كتم العضو {message.from_user.first_name} **مدى الحياة** لتكراره إرسال الروابط المخالفة!", parse_mode="HTML")
                except Exception:
                    pass
            return True

    # نظام السبايم والتكرار
    now = datetime.now().timestamp()
    if user_id not in user_spam_tracker:
        user_spam_tracker[user_id] = {'text': text_content, 'count': 1, 'time': now}
        return False
    
    data = user_spam_tracker[user_id]
    if data['text'] == text_content and (now - data['time']) < 10:
        data['count'] += 1
        data['time'] = now
        
        if data['count'] >= 5:
            try:
                delete_message_safe(chat_id, message.message_id)
                bot.restrict_chat_member(
                    chat_id, 
                    user_id, 
                    until_date=int(now + 60),
                    permissions=ChatPermissions(can_send_messages=False)
                )
                warning_msg = bot.send_message(
                    chat_id, 
                    f"⚠️ <b>تنبيه سبام!</b> تم كتم العضو {message.from_user.first_name} دقيقة واحدة.",
                    parse_mode="HTML"
                )
                threading.Timer(10.0, delete_message_safe, args=(chat_id, warning_msg.message_id)).start()
            except Exception:
                pass
                
            user_spam_tracker[user_id] = {'text': "", 'count': 0, 'time': now}
            return True
    else:
        user_spam_tracker[user_id] = {'text': text_content, 'count': 1, 'time': now}
        
    return False


# ==========================================
# 4. معالجة ونشر الخرائط (بالتصميم الاحترافي الجديد)
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
    # استخراج الوصف والكود بالكامل مع الحفاظ على الفواصل الأصلية
    description_and_code = html.escape(caption.replace(f"[{match.group(1)}]", "").strip())
    
    creator_name = html.escape(messages[0].from_user.first_name)
    username = f"@{messages[0].from_user.username}" if messages[0].from_user.username else ""

    formatted_text = (
        f"<b>[{map_type}]</b>\n\n"
        f"{description_and_code}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
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
    # استخراج الوصف والكود بالكامل مع الحفاظ على الفواصل الأصلية
    description_and_code = html.escape(caption.replace(f"[{match.group(1)}]", "").strip())
    
    creator_name = html.escape(message.from_user.first_name)
    username = f"@{message.from_user.username}" if message.from_user.username else ""

    base_caption = (
        f"<b>[{map_type}]</b>\n\n"
        f"{description_and_code}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
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
        bot.answer_callback_query(call.id, "✅ تم الحفظ!")


print("⚡ البوت المطور بالتصميم الاحترافي يعمل الآن...")
bot.infinity_polling()

