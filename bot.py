import re
from datetime import datetime
import html
import threading
import telebot
from telebot.types import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup

# 🔑 ضع توكن البوت الخاص بك هنا
TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
bot = telebot.TeleBot(TOKEN)

# قاعدة بيانات مصغرة
ratings_data = {}
media_groups = {}


def delete_message_safe(chat_id, message_id):
    """دالة لحذف الرسائل بأمان لتفادي الأخطاء"""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def create_rating_markup():
    """دالة لإنشاء أزرار التقييم"""
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
# 1. الترحيب الأسطوري (منشن + طريقة النشر + حذف بعد دقيقة)
# ==========================================
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        # عمل منشن (Tag) للعضو
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
        # مؤقت لحذف الرسالة بعد 60 ثانية
        threading.Timer(60.0, delete_message_safe, args=(message.chat.id, sent_msg.message_id)).start()


# ==========================================
# 2. استلام الخرائط (دعم الصور المتعددة والمفردة)
# ==========================================
@bot.message_handler(content_types=["photo"])
def handle_craftland_map(message):
    # إذا كانت مجموعة صور (ألبوم)
    if message.media_group_id:
        mg_id = message.media_group_id
        if mg_id not in media_groups:
            media_groups[mg_id] = {'messages': [], 'timer': None}
        
        media_groups[mg_id]['messages'].append(message)
        
        # ننتظر ثانيتين لتجميع كل صور الألبوم قبل المعالجة
        if not media_groups[mg_id]['timer']:
            timer = threading.Timer(2.0, process_media_group, args=[mg_id])
            media_groups[mg_id]['timer'] = timer
            timer.start()
    else:
        # إذا كانت صورة واحدة
        process_single_map(message)


def process_media_group(mg_id):
    """معالجة الألبومات (عدة صور)"""
    if mg_id not in media_groups: return
    group = media_groups.pop(mg_id)
    messages = group['messages']
    
    # البحث عن النص في إحدى صور الألبوم
    caption_msg = next((msg for msg in messages if msg.caption), None)
    caption = caption_msg.caption if caption_msg else ""
    
    match = re.search(r"\[(.*?)\]", caption)
    
    # [شرط صارم]: إذا لم يجد الأقواس [] يتجاهل الرسالة تماماً
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
        # 1. إرسال الألبوم الجديد
        sent_messages = bot.send_media_group(chat_id, media)
        
        # 2. إرسال أزرار التقييم في رسالة ملحقة بالألبوم
        base_rate_text = f"⭐ <b>تَقْيِيمَاتُ الأَعْضَاءِ (لخريطة {creator_name}):</b> "
        full_rate_text = base_rate_text + "0.0/5 (0 أصوات)"
        
        rate_msg = bot.send_message(
            chat_id,
            full_rate_text,
            reply_to_message_id=sent_messages[0].message_id,
            parse_mode="HTML",
            reply_markup=create_rating_markup()
        )
        
        # 3. حفظ بيانات التقييم للألبوم
        ratings_data[rate_msg.message_id] = {"base_text": base_rate_text, "votes": {}, "is_caption": False}
        
        # 4. حذف جميع صور الألبوم الأصلية للعضو
        for msg in messages:
            delete_message_safe(chat_id, msg.message_id)
            
    except Exception as e:
        print(f"❌ خطأ في معالجة الألبوم: {e}")


def process_single_map(message):
    """معالجة خريطة بصورة واحدة"""
    caption = message.caption or ""
    match = re.search(r"\[(.*?)\]", caption)
    
    # [شرط صارم]: إذا لم يجد الأقواس [] يتجاهل الرسالة تماماً ولا يستجيب
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
        # 1. إرسال الصورة المصممة
        sent_msg = bot.send_photo(
            message.chat.id,
            message.photo[-1].file_id,
            caption=full_caption,
            parse_mode="HTML",
            reply_markup=create_rating_markup()
        )
        
        # 2. حذف رسالة العضو
        delete_message_safe(message.chat.id, message.message_id)
        
        # 3. حفظ بيانات التقييم
        ratings_data[sent_msg.message_id] = {"base_text": base_caption, "votes": {}, "is_caption": True}
        
    except Exception as e:
        print(f"❌ خطأ في معالجة الصورة الواحدة: {e}")


# ==========================================
# 3. معالجة التقييمات بشفافية تامة
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


print("⚡ البوت يعمل الآن بكامل قوته (منشن، حذف مؤقت، دعم صور متعددة)...")
bot.infinity_polling()
