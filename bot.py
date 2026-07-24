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
user_link_violations = {}  # لتتبع مخالفات الروابط لكل مستخدم


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
# 1. الترحيب الأسطوري بالأعضاء الجدد
# ==========================================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        mention = f'<a href="tg://user?id={new_member.id}">{html.escape(new_member.first_name)}</a>'
        time_now = datetime.now().strftime("%I:%M %p")

        welcome_text = (
            f"👑 <b>أهلاً بك يا {mention} في مَمعْقَلْ صُنّاعْ أرْضِ الحَرَفْ!</b> 👑\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>وَقْتُ الدُّخُولْ:</b> <code>{time_now}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔥 <b>طَرِيقَةُ نَشْرِ خَرِيطَتِكَ هُنَا:</b>\n"
            f"أرسل صورة أو عدة صور للخريطة، واكتب في <b>شرح الصورة (Caption)</b> هكذا:\n"
            f"<code>[نوع الخريطة]</code>\n"
            f"<code>وصف الخريطة الخاصة بك مع الكود</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ <i>(تنبيه: سيتم حذف هذه الرسالة بعد دقيقة للحفاظ على نظافة الجروب)</i>"
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
        f"📖 <b>دَلِيلُ مَمعْقَلْ صُنّاعْ أرْضِ الحَرَفْ</b> 📖\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>كيف تنشر خريطتك بطريقة صحيحة؟</b>\n"
        f"1️⃣ جهز صورة أو ألبوم صور لخريطتك.\n"
        f"2️⃣ في خانة الوصف (Caption) ضع نوع الخريطة بين أقواس هكذا: <code>[تصميم]</code> أو <code>[رعب]</code>.\n"
        f"3️⃣ أرسل الصورة وسيقوم البوت بإعادة نشرها بتصميم فخم مع أزرار التقييم!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>ملاحظة: البوت يتجاهل أي رسائل نصية عادية لا تحتوي على خريطة أو أقواس.</i>"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📌 اضغط هنا لمعرفة طريقة النشر", callback_data="show_guide"))
    
    bot.send_message(message.chat.id, help_text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(commands=['rules'])
def send_rules(message):
    rules_text = (
        f"📜 <b>قَوَانِينُ وَشُرُوطُ المَجْمُوعَةِ</b> 📜\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ مسموح فقط روابط (تليجرام، يوتيوب، واتساب، انستغرام، تيك توك).\n"
        f"2️⃣ الروابط الخارجية المخالفة تعرض صاحبها للتنبيه ثم الميوت التدريجي.\n"
        f"3️⃣ احترم جميع الأعضاء وصناع الخرائط.\n"
        f"4️⃣ يمنع سبام الرسائل أو تكرارها.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, rules_text, parse_mode="HTML")


@bot.message_handler(commands=['stats'])
def send_stats(message):
    stats_text = (
        f"📊 <b>إِحْصَائِياتُ نِظَامِ البُوتِ</b> 📊\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 <b>الحالة:</b> يعمل بكفاءة 24/7 (Online)\n"
        f"🛡️ <b>الحماية:</b> مفعلة (Anti-Spam & Smart Anti-Link)\n"
        f"⚡ <b>السرعة:</b> استجابة فورية للخرائط والألبومات\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.send_message(message.chat.id, stats_text, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "show_guide")
def callback_guide(call):
    guide_alert = (
        "طريقة النشر:\n"
        "أرسل صورة الخريطة مع الكود واكتب نوعها بين أقواس هكذا:\n"
        "[اسم النوع]\n"
        "وصف الخريطة والكود"
    )
    bot.answer_callback_query(call.id, guide_alert, show_alert=True)


# ==========================================
# 3. نظام الحماية الذكي (روابط مستثناة + عقوبات تدريجية + سبام)
# ==========================================
def check_security(message):
    if not message.from_user or message.chat.type == 'private':
        return False
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    text_content = message.text or message.caption or ""
    
    # فحص الروابط الخارجية
    if "http://" in text_content or "https://" in text_content or "www." in text_content:
        # الكلمات أو المواقع المسموح بها
        allowed_domains = ["t.me", "youtube.com", "youtu.be", "whatsapp.com", "wa.me", "instagram.com", "tiktok.com"]
        is_allowed = any(domain in text_content for domain in allowed_domains)
        
        if not is_allowed:
            # رابط مخالف غير مسموح به
            delete_message_safe(chat_id, message.message_id)
            
            if user_id not in user_link_violations:
                user_link_violations[user_id] = 0
            
            user_link_violations[user_id] += 1
            violations_count = user_link_violations[user_id]
            
            if violations_count == 1:
                # التحذير الأول
                warn = bot.send_message(chat_id, f"⚠️ تنبيه يا {message.from_user.first_name}! ممنوع نشر الروابط الخارجية غير المسموحة. هذا هو التحذير الأول.", parse_mode="HTML")
                threading.Timer(7.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
            elif violations_count == 2:
                # التحذير الثاني: ميوت 10 دقائق (600 ثانية)
                try:
                    now = datetime.now().timestamp()
                    bot.restrict_chat_member(chat_id, user_id, until_date=int(now + 600), permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"🚫 تم كتم العضو {message.from_user.first_name} لمدة 10 دقائق لتكراره إرسال روابط مخالفة!", parse_mode="HTML")
                    threading.Timer(10.0, delete_message_safe, args=(chat_id, warn.message_id)).start()
                except Exception:
                    pass
            else:
                # التحذير الثالث فما فوق: ميوت مدى الحياة (حتى يفك عنه المشرف)
                try:
                    bot.restrict_chat_member(chat_id, user_id, until_date=0, permissions=ChatPermissions(can_send_messages=False))
                    warn = bot.send_message(chat_id, f"⛔ تم كتم العضو {message.from_user.first_name} **مدى الحياة** لتكراره إرسال الروابط المخالفة!", parse_mode="HTML")
                except Exception:
                    pass
            return True

    # نظام السبايم والتكرار العادي
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
                    f"⚠️ <b>تنبيه سبام!</b> تم كتم العضو {message.from_user.first_name} لمدة دقيقة واحدة لتكراره الرسائل.",
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
# 4. معالجة ونشر الخرائط
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
    raw_desc = caption.replace(f"[{match.group(1)}]", "").strip()
    description_and_code = html.escape(raw_desc)
    
    creator_name = html.escape(messages[0].from_user.first_name)
    username = f"@{messages[0].from_user.username}" if messages[0].from_user.username else "بدون يوزر"

    formatted_text = (
        f"🗺️ <b>خَرِيطَةُ أرْضِ الحَرَفِ جَدِيدَةٌ!</b> 🗺️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>نَوْعُ الْخَرِيطَةِ:</b> ✨ <code>{map_type}</code> ✨\n"
        f"📝 <b>الْوَصْفُ وَالْكُودُ:</b>\n{description_and_code}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>CREATED BY:</b> {creator_name} ({username})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
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
        
        base_rate_text = f"⭐ <b>تَقْيِيمَاتُ الأَعْضَاءِ (لخريطة {creator_name}):</b> "
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
        print(f"❌ خطأ في معالجة الألبوم: {e}")


def process_single_map(message):
    caption = message.caption or ""
    match = re.search(r"\[(.*?)\]", caption)
    
    if not match: return

    map_type = html.escape(match.group(1).strip())
    raw_desc = caption.replace(f"[{match.group(1)}]", "").strip()
    description_and_code = html.escape(raw_desc)
    
    creator_name = html.escape(message.from_user.first_name)
    username = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"

    base_caption = (
        f"🗺️ <b>خَرِيطَةُ أرْضِ الحَرَفِ جَدِيدَةٌ!</b> 🗺️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎮 <b>نَوْعُ الْخَرِيطَةِ:</b> ✨ <code>{map_type}</code> ✨\n"
        f"📝 <b>الْوَصْفُ وَالْكُودُ:</b>\n{description_and_code}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>CREATED BY:</b> {creator_name} ({username})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ <b>تَقْيِيمَاتُ الأَعْضَاءِ:</b> "
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
        print(f"❌ خطأ في معالجة الصورة الواحدة: {e}")


# ==========================================
# 5. معالجة التقييمات
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating(call):
    msg_id = call.message.message_id
    user_id = call.from_user.id
    rating_val = int(call.data.split("_")[1])

    if msg_id not in ratings_data:
        bot.answer_callback_query(call.id, "⚠️ لا يمكن تقييم هذه الخريطة حالياً!", show_alert=True)
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
        bot.answer_callback_query(call.id, f"✅ تم تسجيل تقييمك: {rating_val} نجوم!")
    except Exception:
        bot.answer_callback_query(call.id, "✅ تم حفظ التقييم!")


print("⚡ البوت المطور يعمل الآن بنظام حماية الروابط الذكي...")
bot.infinity_polling()

