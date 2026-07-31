import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ----------------------------------------------------
# 1. إعدادات البوت والبيانات الأساسية
# ----------------------------------------------------
BOT_TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
CHANNEL_ID = -1003947857086
DEVELOPER_ID = 7454358135

# قاعدة بيانات مؤقتة في الذاكرة (Memory DB)
user_nicknames = {}  # {user_id: nickname}
registered_players = {}  # {user_id: user_obj}
tournaments_db = {}  # مؤقت لحفظ معطيات البطولة أثناء الإنشاء

# مراحل الـ Conversation Handler
SET_NICKNAME = 1
ROOM_ID_PASS = 2
RESULT_IMAGE = 3

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------------------------------------------
# 2. الترحيب بعضو جديد في القناة
# ----------------------------------------------------
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members:
        name = member.full_name
        welcome_text = (
            f"⚔️ **مرحباً بك يا {name} في ساحة النخبة والتكتيك!** ⚔️\n\n"
            f"أهلاً بك في أكاديميتنا الخاصة بـ **Free Fire E-Sports**.\n"
            f"هنا لا مكان للعشوائية؛ نسعى لصناعة قادة الفرق وتحليل التكتيكات الوصول للقمة.\n\n"
            f"🎯 *جاهز لاختبار مهاراتك والتنافس بشرف؟*"
        )
        keyboard = [
            [InlineKeyboardButton("🏆 البطولات المنظمة حالياً", callback_query_data="current_tournaments")],
            [InlineKeyboardButton("👤 تسجيل اللقب / التواصل مع البوت", url=f"https://t.me/{context.bot.username}?start=register")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ----------------------------------------------------
# 3. أمر /start والتسجيل للمستخدمين والمشرفين
# ----------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_type = update.effective_chat.type

    if chat_type != 'private':
        return

    # فحص ما إذا كان المستخدم مشرفاً أو المطور
    is_admin = False
    if user.id == DEVELOPER_ID:
        is_admin = True
    else:
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
            if member.status in ['administrator', 'creator']:
                is_admin = True
        except Exception:
            is_admin = False

    # 🟢 مسار المشرفين
    if is_admin:
        admin_text = (
            f"🛡️ **مرحباً بك أيها المشرف القائد @{user.username or user.first_name}**\n\n"
            f"منصة التحكم في بطولات E-Sports جاهزة تحت إمرتك.\n"
            f"يمكنك الآن إنشاء روم تكتيكية جديدة وتنظيم التسجيل آلياً."
        )
        keyboard = [[InlineKeyboardButton("🎮 إنشاء بطولة جديدة", callback_data="create_tournament")]]
        await update.message.reply_text(
            admin_text, 
            parse_mode="Markdown", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    # 🔵 مسار المتابعين (حفظ اللقب)
    if user.id in user_nicknames:
        await update.message.reply_text(
            f"مرحباً بك مجدداً يا **{user_nicknames[user.id]}**!\n"
            f"بياناتك مسجلة لدينا مسبقاً. ستتلقى إشعارات البطولات هنا فور إطلاقها.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "⚔️ **مرحباً بك في البوت التنظيمي للبطولات!**\n\n"
            "من فضلك أرسل **لقبك أو اسمك داخل لعبة Free Fire** للتحقق وحفظ بياناتك:"
        )
        return SET_NICKNAME

async def save_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nickname = update.message.text.strip()
    user_nicknames[user.id] = nickname
    registered_players[user.id] = user

    await update.message.reply_text(
        f"✅ **تم حفظ لقبك بنجاح:** `{nickname}`\n\n"
        f"سيتم إشعاراتك بكل البطولات والتفاصيل هنا عبر الخاص بانتظام.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ----------------------------------------------------
# 4. لوحة بناء البطولة للمشرفين
# ----------------------------------------------------
async def tournament_builder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "create_tournament":
        tournaments_db[user_id] = {
            "mode": None, "squads": None, "map": None, 
            "ammo": "YES", "gloo": "YES", "character": "YES", 
            "pet": "YES", "airdrop": "YES", "vehicles": "YES", 
            "time": "20:00", "registered": []
        }
        await show_main_builder_menu(query)

    elif query.data == "set_mode_menu":
        kb = [
            [InlineKeyboardButton("كلاش سكواد (Clash Squad)", callback_data="mode_CS")],
            [InlineKeyboardButton("باتل رويال (Battle Royale)", callback_data="mode_BR")]
        ]
        await query.edit_message_text("🎮 **اختر نوع الروم:**", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("mode_"):
        mode = "كلاش سكواد" if "CS" in query.data else "باتل رويال"
        tournaments_db[user_id]["mode"] = mode
        await show_main_builder_menu(query)

    elif query.data == "set_squads_menu":
        kb = []
        for i in range(4, 11):
            kb.append([InlineKeyboardButton(f"{i} سكوادات", callback_data=f"squads_{i}")])
        await query.edit_message_text("👥 **حدد عدد السكوادات المشاركة:**", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("squads_"):
        count = int(query.data.split("_")[1])
        tournaments_db[user_id]["squads"] = count
        await show_main_builder_menu(query)

    elif query.data == "set_map_menu":
        kb = [
            [InlineKeyboardButton("1. برمودا", callback_data="map_برمودا")],
            [InlineKeyboardButton("2. كالاهاري", callback_data="map_كالاهاري")],
            [InlineKeyboardButton("3. بيرغاتوري", callback_data="map_بيرغاتوري")],
            [InlineKeyboardButton("4. نيكستيريا", callback_data="map_نيكستيريا")],
            [InlineKeyboardButton("5. سولارا", callback_data="map_سولارا")]
        ]
        await query.edit_message_text("🗺️ **اختر خريطة الروم:**", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data.startswith("map_"):
        map_name = query.data.split("_")[1]
        tournaments_db[user_id]["map"] = map_name
        await show_main_builder_menu(query)

    elif query.data.startswith("toggle_"):
        key = query.data.split("_")[1]
        current = tournaments_db[user_id].get(key, "YES")
        tournaments_db[user_id][key] = "NO" if current == "YES" else "YES"
        await show_main_builder_menu(query)

    elif query.data == "publish_tournament":
        await publish_tournament_to_channel(query, context)

async def show_main_builder_menu(query):
    user_id = query.from_user.id
    t = tournaments_db[user_id]

    text = (
        "⚙️ **إعداد معطيات روم البطولة الاحترافية:**\n\n"
        f"• **نوع الروم:** {t['mode'] or 'غير محدد'}\n"
        f"• **عدد السكوادات:** {t['squads'] or 'غير محدد'}\n"
        f"• **الخريطة:** {t['map'] or 'غير محدد'}\n"
        f"• **ذخيرة محدودة:** {t['ammo']} | **تلج محدود:** {t['gloo']}\n"
        f"• **مهارة الشخصيات:** {t['character']} | **مهارة الحيوان:** {t['pet']}\n"
        f"• **إنزال جوي:** {t['airdrop']} | **سيارات:** {t['vehicles']}\n"
    )

    kb = [
        [InlineKeyboardButton("🎮 نوع الروم", callback_data="set_mode_menu")]
    ]
    if t["mode"] == "باتل رويال":
        kb.append([InlineKeyboardButton("👥 عدد السكوادات", callback_data="set_squads_menu")])

    kb.extend([
        [InlineKeyboardButton("🗺️ خريطة الروم", callback_data="set_map_menu")],
        [InlineKeyboardButton(f"ذخيرة محدودة: {t['ammo']}", callback_data="toggle_ammo")],
        [InlineKeyboardButton(f"تلج محدود: {t['gloo']}", callback_data="toggle_gloo")],
        [InlineKeyboardButton(f"مهارة الشخصيات: {t['character']}", callback_data="toggle_character")],
        [InlineKeyboardButton(f"مهارة الحيوانات: {t['pet']}", callback_data="toggle_pet")],
        [InlineKeyboardButton(f"الإنزال الجوي: {t['airdrop']}", callback_data="toggle_airdrop")],
        [InlineKeyboardButton(f"سيارات: {t['vehicles']}", callback_data="toggle_vehicles")],
        [InlineKeyboardButton("🚀 نشر البطولة الآن", callback_data="publish_tournament")]
    ])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ----------------------------------------------------
# 5. نشر البطولة والإشعار العام
# ----------------------------------------------------
async def publish_tournament_to_channel(query, context: ContextTypes.DEFAULT_TYPE):
    user = query.from_user
    t = tournaments_db[user.id]

    # حساب الحد الأقصى للاعبين
    max_players = (t['squads'] * 4) if t['mode'] == "باتل رويال" and t['squads'] else 8

    t_text = (
        f"🏆 **بطولة E-SPORTS جديدة اعلنت رسمياً!** 🏆\n\n"
        f"👤 **منظم البطولة:** @{user.username or user.first_name}\n"
        f"🎮 **النمط:** {t['mode']}\n"
        f"🗺️ **الخريطة:** {t['map']}\n\n"
        f"📌 **شروط وإعدادات الروم:**\n"
        f"• ذخيرة محدودة: {t['ammo']} | تلج محدود: {t['gloo']}\n"
        f"• مهارة شخصيات: {t['character']} | مهارة حيوان: {t['pet']}\n"
        f"• إنزال جوي: {t['airdrop']} | سيارات: {t['vehicles']}\n\n"
        f"⏳ **المقاعد المتاحة:** {max_players} لاعب فقط لتجنب الاكتظاظ!"
    )

    kb = [[InlineKeyboardButton("📝 إضغط هنا للدخول والتسجيل", url=f"https://t.me/{context.bot.username}?start=register")]]
    
    # 1. نشر في القناة
    await context.bot.send_message(
        chat_id=CHANNEL_ID, 
        text=t_text, 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(kb)
    )

    # 2. إعادة النشر للجميع بالخاص (ما عدا المنظم)
    broadcast_msg = (
        f"📢 **بطولة جديدة تم إنشاؤها بواسطة @{user.username or user.first_name}!**\n\n"
        f"سارع بالتسجيل الآن من خلال القناة قبل اكتمال العدد."
    )
    for p_id in registered_players:
        if p_id != user.id:
            try:
                await context.bot.send_message(chat_id=p_id, text=broadcast_msg, reply_markup=InlineKeyboardMarkup(kb))
            except Exception:
                pass

    await query.edit_message_text("✅ **تم نشر البطولة بنجاح في القناة وتوجيه الإشعارات بالخاص!**")

# ----------------------------------------------------
# 6. التشغيل الرئيسي للبوت
# ----------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation Handler لخطوات التسجيل والتفاعل
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            SET_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_nickname)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(tournament_builder_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    print("🤖 البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == '__main__':
    main()
