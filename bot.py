    import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

# ==========================================
# 1. إعدادات البوت الأساسية
# ==========================================
BOT_TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"
CHANNEL_ID = -1003947857086  # ID القناة ديالك
OWNER_USERNAME = "@an_as1209" # ⚠️ حط اليوزرنيم ديالك هنا (مثلا @anas) باش الناس تواصل معاك
BOT_USERNAME = "@anas_craftland_bot" # معرف البوت ديالك

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ==========================================
# 2. قواعد البيانات (في الذاكرة المؤقتة)
# ==========================================
tournaments_db = {}
active_registrations = {}
tournament_counter = 0

# ==========================================
# 3. حالات الفارم (FSM) لتتبع خطوات إنشاء البطولة
# ==========================================
class TournamentCreationStates(StatesGroup):
    setting_game_mode = State()
    setting_max_players = State()
    setting_map_name = State()
    setting_start_time = State()
    # إعدادات YES/NO
    setting_ammo = State()
    setting_gloowall = State()
    setting_char_skill = State()
    setting_pet_skill = State()
    setting_airdrop = State()
    setting_vehicles = State()

# ==========================================
# 4. دوال مساعدة لإنشاء الأزرار
# ==========================================
def get_yes_no_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="YES ✅", callback_data="set_YES"),
            InlineKeyboardButton(text="NO ❌", callback_data="set_NO")
        ]
    ])

async def ask_setting(message_or_call, state: FSMContext, next_state: State, text: str):
    await state.set_state(next_state)
    kb = get_yes_no_kb()
    msg_text = f"⚙️ **إعدادات الروم:** {text}"
    
    if isinstance(message_or_call, Message):
        await message_or_call.answer(msg_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    elif isinstance(message_or_call, CallbackQuery):
        await message_or_call.message.edit_text(msg_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 5. أمر البداية /start
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 إنشاء بطولة جديدة", callback_data="create_tour")],
        [InlineKeyboardButton(text="💬 تواصل مع الإدارة", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
    ])
    
    welcome_text = (
        "👋 **أهلاً بك في بوت إدارة بطولات Craftland!**\n\n"
        "⚡ ابحث عن سكواد للعب معك\n"
        "🗺️ شارك خرائطك المخصصة وقيم خرائط الآخرين\n"
        "🏆 شارك في البطولات واصعد في قائمة أفضل اللاعبين\n"
        "🛡️ حماية تلقائية للمجموعة\n\n"
        "👇 أضفني إلى مجموعتك وابدأ التجربة أو قم بإنشاء بطولة الآن!"
    )
    await message.answer(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 6. خطوات إنشاء البطولة (الأسئلة النصية)
# ==========================================
@router.callback_query(F.data == "create_tour")
async def start_tournament_creation(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(TournamentCreationStates.setting_game_mode)
    await call.message.edit_text("🎮 أرسل **نمط اللعب** (مثلاً: سكواد، دو، سولو):", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_game_mode))
async def get_game_mode(message: Message, state: FSMContext):
    await state.update_data(game_mode=message.text)
    await state.set_state(TournamentCreationStates.setting_max_players)
    await message.answer("👥 أرسل **الحد الأقصى للاعبين** (رقم):", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_max_players))
async def get_max_players(message: Message, state: FSMContext):
    await state.update_data(max_players=message.text)
    await state.set_state(TournamentCreationStates.setting_map_name)
    await message.answer("🗺️ أرسل **اسم الخريطة**:", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_map_name))
async def get_map_name(message: Message, state: FSMContext):
    await state.update_data(map_name=message.text)
    await state.set_state(TournamentCreationStates.setting_start_time)
    await message.answer("⏰ أرسل **موعد الانطلاق** (مثلاً: 22:00 بتوقيت المغرب):", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 7. خطوات الإعدادات (أزرار YES / NO)
# ==========================================
@router.message(StateFilter(TournamentCreationStates.setting_start_time))
async def get_start_time(message: Message, state: FSMContext):
    await state.update_data(start_time=message.text)
    await ask_setting(message, state, TournamentCreationStates.setting_ammo, "ذخيرة محدودة؟")

@router.callback_query(StateFilter(TournamentCreationStates.setting_ammo), F.data.startswith("set_"))
async def set_ammo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(ammo=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_gloowall, "ثلج محدود؟")

@router.callback_query(StateFilter(TournamentCreationStates.setting_gloowall), F.data.startswith("set_"))
async def set_gloowall(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(gloowall=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_char_skill, "مهارة الشخصيات؟")

@router.callback_query(StateFilter(TournamentCreationStates.setting_char_skill), F.data.startswith("set_"))
async def set_char_skill(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(char_skill=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_pet_skill, "مهارة الحيوان الأليف؟")

@router.callback_query(StateFilter(TournamentCreationStates.setting_pet_skill), F.data.startswith("set_"))
async def set_pet_skill(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(pet_skill=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_airdrop, "دروب جوي؟")

@router.callback_query(StateFilter(TournamentCreationStates.setting_airdrop), F.data.startswith("set_"))
async def set_airdrop(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(airdrop=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_vehicles, "سيارات؟")

# ==========================================
# 8. حفظ البطولة ونشرها في القناة
# ==========================================
@router.callback_query(StateFilter(TournamentCreationStates.setting_vehicles), F.data.startswith("set_"))
async def finalize_tournament(call: CallbackQuery, state: FSMContext):
    await call.answer() 
    await state.update_data(vehicles=call.data.split("_")[1])
    
    data = await state.get_data()
    await state.clear()

    global tournament_counter
    tournament_counter += 1
    tour_id = tournament_counter

    data["organizer_id"] = call.from_user.id
    data["organizer_name"] = call.from_user.username or call.from_user.first_name
    tournaments_db[tour_id] = data
    active_registrations[tour_id] = []

    # صياغة إعلان البطولة (تمت إضافة معلومات الاستفسار هنا)
    announce_text = (
        f"🔥 **إعلان بطولة جديدة #{tour_id}** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ **النمط:** {data.get('game_mode', 'غير محدد')}\n"
        f"👥 **الحد الأقصى:** {data.get('max_players', 'غير محدد')} لاعب\n"
        f"🗺️ **الخريطة:** {data.get('map_name', 'غير محدد')}\n"
        f"⏰ **موعد الانطلاق:** {data.get('start_time', 'غير محدد')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ **شروط وإعدادات المباراة:**\n"
        f"• ذخيرة محدودة: {data.get('ammo', 'NO')} | ثلج محدود: {data.get('gloowall', 'NO')}\n"
        f"• مهارة شخصيات: {data.get('char_skill', 'YES')} | مهارة بيت: {data.get('pet_skill', 'YES')}\n"
        f"• دروب جوي: {data.get('airdrop', 'YES')} | سيارات: {data.get('vehicles', 'NO')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **المنظم:** @{data['organizer_name']}\n"
        f"💬 **لأي استفسار تواصل مع مالك القناة:** {OWNER_USERNAME}\n"
        f"🤖 **للتسجيل والتفاعل:** {BOT_USERNAME}\n\n"
        f"سارع بالتسجيل قبل اكتمال المقاعد! 🚀"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="إضغط للتسجيل 📝", callback_data=f"reg_{tour_id}")]
        ]
    )

    try:
        # نشر في القناة
        msg = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=announce_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb,
        )
        tournaments_db[tour_id]["channel_msg_id"] = msg.message_id

        await call.message.edit_text(
            f"✅ **تم إنشاء البطولة ونشرها بنجاح في القناة!**\n(معرف البطولة: #{tour_id})",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await call.message.edit_text(
            f"⚠️ تم حفظ الإعدادات بنجاح، لكن لم أتمكن من النشر في القناة.\nالمرجو التأكد أن البوت **مشرف (Admin)** في القناة التي أضفتها.\nالخطأ: {e}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# 9. زر التسجيل في البطولة
# ==========================================
@router.callback_query(F.data.startswith("reg_"))
async def register_player(call: CallbackQuery):
    tour_id = int(call.data.split("_")[1])
    
    if tour_id not in tournaments_db:
        await call.answer("❌ هذه البطولة لم تعد موجودة أو انتهت.", show_alert=True)
        return

    player_id = call.from_user.id
    
    if player_id in active_registrations[tour_id]:
        await call.answer("⚠️ أنت مسجل بالفعل في هذه البطولة!", show_alert=True)
    else:
        active_registrations[tour_id].append(player_id)
        # رسالة تأكيد للمستخدم
        await call.answer("✅ تم تسجيلك بنجاح في البطولة! سيتم إشعارك بالجديد.", show_alert=True)
        # يمكن للمنظم أن يتوصل بإشعار هنا إذا أردت مستقبلاً

# ==========================================
# 10. التشغيل الرئيسي
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 البوت شغال الآن...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
