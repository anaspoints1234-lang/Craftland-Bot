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
CHANNEL_ID = -1003947857086  
OWNER_USERNAME = "https://t.me/its_me_zoro_2010" # ⚠️ حط اليوزرنيم ديالك هنا
BOT_USERNAME = "https://t.me/anas_craftland_bot" # ⚠️ بدل هادي باليوزرنيم الجديد ديال البوت يلا بدلتيه

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
            InlineKeyboardButton(text="تفعيل ✅", callback_data="set_YES"),
            InlineKeyboardButton(text="إلغاء ❌", callback_data="set_NO")
        ]
    ])

async def ask_setting(message_or_call, state: FSMContext, next_state: State, text: str):
    await state.set_state(next_state)
    kb = get_yes_no_kb()
    msg_text = f"⚙️ **تخصيص الإعدادات:**\n\nهل ترغب في تفعيل **[ {text} ]**؟"
    
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
        [InlineKeyboardButton(text="🏆 بدء إعداد بطولة جديدة", callback_data="create_tour")],
        [InlineKeyboardButton(text="💬 تواصل مع الدعم والإدارة", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}")]
    ])
    
    welcome_text = (
        "✧ ─── ❖ ── ✦ ── ❖ ─── ✧\n"
        "👑 **أهـلاً بـك فـي نـظـام الإدارة الاحـتـرافـي** 👑\n"
        "✧ ─── ❖ ── ✦ ── ❖ ─── ✧\n\n"
        "أنا المساعد الذكي الخاص بك، مصمم خصيصاً للارتقاء بمستوى تنظيم الرومات والبطولات إلى أقصى درجات الاحترافية. 💎\n\n"
        "📌 **مـاذا أقـدم لـك؟**\n"
        "🏆 ↫ تنظيم بطولات متكاملة بضغطة زر.\n"
        "👥 ↫ إدارة تسجيل اللاعبين والفرق بسلاسة.\n"
        "📊 ↫ نشر إعلانات احترافية ومباشرة في قناتك.\n\n"
        "👇🏻 **اخـتـر مـن الـقـائـمـة أدنـاه لـتـبـدأ رحـلـتـك:**"
    )
    await message.answer(welcome_text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 6. خطوات إنشاء البطولة (الأسئلة النصية)
# ==========================================
@router.callback_query(F.data == "create_tour")
async def start_tournament_creation(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.set_state(TournamentCreationStates.setting_game_mode)
    await call.message.edit_text("🎮 **الخطوة الأولى:**\nيرجى إرسال **نمط اللعب** الخاص بالبطولة (مثلاً: سكواد، دو، سولو):", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_game_mode))
async def get_game_mode(message: Message, state: FSMContext):
    await state.update_data(game_mode=message.text)
    await state.set_state(TournamentCreationStates.setting_max_players)
    await message.answer("👥 **الخطوة الثانية:**\nيرجى إرسال **الحد الأقصى للاعبين** (أرقام فقط):", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_max_players))
async def get_max_players(message: Message, state: FSMContext):
    await state.update_data(max_players=message.text)
    await state.set_state(TournamentCreationStates.setting_map_name)
    await message.answer("🗺️ **الخطوة الثالثة:**\nيرجى تحديد **اسم الخريطة** التي ستُلعب عليها البطولة:", parse_mode=ParseMode.MARKDOWN)

@router.message(StateFilter(TournamentCreationStates.setting_map_name))
async def get_map_name(message: Message, state: FSMContext):
    await state.update_data(map_name=message.text)
    await state.set_state(TournamentCreationStates.setting_start_time)
    await message.answer("⏰ **الخطوة الرابعة:**\nيرجى إرسال **توقيت انطلاق البطولة** (مثال: 22:00 بتوقيت المغرب):", parse_mode=ParseMode.MARKDOWN)

# ==========================================
# 7. خطوات الإعدادات (أزرار YES / NO)
# ==========================================
@router.message(StateFilter(TournamentCreationStates.setting_start_time))
async def get_start_time(message: Message, state: FSMContext):
    await state.update_data(start_time=message.text)
    await ask_setting(message, state, TournamentCreationStates.setting_ammo, "الذخيرة المحدودة")

@router.callback_query(StateFilter(TournamentCreationStates.setting_ammo), F.data.startswith("set_"))
async def set_ammo(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(ammo=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_gloowall, "الثلج المحدود")

@router.callback_query(StateFilter(TournamentCreationStates.setting_gloowall), F.data.startswith("set_"))
async def set_gloowall(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(gloowall=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_char_skill, "مهارة الشخصيات")

@router.callback_query(StateFilter(TournamentCreationStates.setting_char_skill), F.data.startswith("set_"))
async def set_char_skill(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(char_skill=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_pet_skill, "مهارة الحيوان الأليف")

@router.callback_query(StateFilter(TournamentCreationStates.setting_pet_skill), F.data.startswith("set_"))
async def set_pet_skill(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(pet_skill=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_airdrop, "الدروب الجوي")

@router.callback_query(StateFilter(TournamentCreationStates.setting_airdrop), F.data.startswith("set_"))
async def set_airdrop(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(airdrop=call.data.split("_")[1])
    await ask_setting(call, state, TournamentCreationStates.setting_vehicles, "السيارات")

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

    # صياغة إعلان البطولة الفخم
    announce_text = (
        f"✧ ─── ❖ ── ✦ ── ❖ ─── ✧\n"
        f"🏆 **إعــلان عــن بـطـولـة جـديـدة [ #{tour_id} ]** 🏆\n"
        f"✧ ─── ❖ ── ✦ ── ❖ ─── ✧\n\n"
        f"⚔️ **نـظـام الـلـعـب:** {data.get('game_mode', 'غير محدد')}\n"
        f"👥 **الـعـدد الأقـصـى:** {data.get('max_players', 'غير محدد')} لاعب\n"
        f"🗺️ **الـخـريـطـة:** {data.get('map_name', 'غير محدد')}\n"
        f"⏰ **تـوقـيـت الانـطـلاق:** {data.get('start_time', 'غير محدد')}\n\n"
        f"⚙️ **شــروط وإعــدادات الـمـبـاراة:**\n"
        f"🔸 ذخيرة محدودة: {data.get('ammo', 'NO')} | ثلج محدود: {data.get('gloowall', 'NO')}\n"
        f"🔸 مهارة شخصيات: {data.get('char_skill', 'YES')} | مهارة حيوان: {data.get('pet_skill', 'YES')}\n"
        f"🔸 دروب جوي: {data.get('airdrop', 'YES')} | سيارات: {data.get('vehicles', 'NO')}\n\n"
        f"👑 **تـنـظـيـم الـقـائـد:** @{data['organizer_name']}\n"
        f"💬 **للاستفسار والتواصل:** {OWNER_USERNAME}\n"
        f"🤖 **للتسجيل الآلي عبر البوت:** {BOT_USERNAME}\n\n"
        f"⚠️ **المقاعد محدودة، سارع بحجز مكانك الآن!** 🚀"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 إضـغـط هـنـا لـلـتـسـجـيـل", callback_data=f"reg_{tour_id}")]
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
            f"✅ **تـمـت الـعـمـلـيـة بـنـجـاح!** 💎\n\n"
            f"تم إنشاء البطولة وإرسال الإعلان الرسمي إلى القناة المحددة.\n"
            f"(معرف البطولة: #{tour_id})",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await call.message.edit_text(
            f"⚠️ **عذراً، حدث خطأ أثناء النشر:**\nتم حفظ الإعدادات، لكن لم أتمكن من إرسال الإعلان للقناة.\nالمرجو التأكد أن البوت **مشرف (Admin)** ويمتلك صلاحيات النشر.\n\nتفاصيل الخطأ: {e}",
            parse_mode=ParseMode.MARKDOWN
        )

# ==========================================
# 9. زر التسجيل في البطولة
# ==========================================
@router.callback_query(F.data.startswith("reg_"))
async def register_player(call: CallbackQuery):
    tour_id = int(call.data.split("_")[1])
    
    if tour_id not in tournaments_db:
        await call.answer("❌ عذراً، هذه البطولة لم تعد متاحة أو تم إنهاؤها.", show_alert=True)
        return

    player_id = call.from_user.id
    
    if player_id in active_registrations[tour_id]:
        await call.answer("⚠️ لقد قمت بالتسجيل مسبقاً في هذه البطولة!", show_alert=True)
    else:
        active_registrations[tour_id].append(player_id)
        # رسالة تأكيد فخمة للمستخدم
        await call.answer("✅ تم تأكيد تسجيلك بنجاح! استعد للمنافسة وحظاً موفقاً. 🏆", show_alert=True)

# ==========================================
# 10. التشغيل الرئيسي
# ==========================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 النظام يعمل الآن بكفاءة...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
