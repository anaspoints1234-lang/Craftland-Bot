import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ================= 1. البيانات الأساسية =================
BOT_TOKEN = "8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc"  # ضع توكن البوت الخاص بك هنا
CHANNEL_ID = -1003947857086
DEVELOPER_ID = 7454358135

logging.basicConfig(level=logging.INFO)

# ================= 2. قواعد البيانات (في الذاكرة) =================
users_db: Dict[int, str] = {}  # user_id -> nickname
tournaments_db: Dict[int, dict] = {}  # tour_id -> details
active_registrations: Dict[int, List[int]] = {}  # tour_id -> [user_ids]
tournament_counter = 0

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# ================= 3. حالات الحوار (FSM States) =================
class RegistrationStates(StatesGroup):
    waiting_for_nickname = State()


class TournamentCreationStates(StatesGroup):
    game_mode = State()
    squad_count = State()
    start_time = State()
    map_selection = State()
    setting_ammo = State()
    setting_gloowall = State()
    setting_char_skill = State()
    setting_pet_skill = State()
    setting_airdrop = State()
    setting_vehicles = State()


class RoomDataStates(StatesGroup):
    tour_id = State()
    room_id_code = State()


class ResultStates(StatesGroup):
    tour_id = State()
    photo = State()


# ================= 4. دوال الفحص والحماية =================
async def is_admin(user_id: int) -> bool:
    if user_id == DEVELOPER_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


# ================= 5. الترحيب والملف الشخصي (خاص بالأعضاء) =================
@router.chat_member()
def on_user_join(event: ChatMemberUpdated):
    # معالجة دخول عضو جديد للقناة
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        welcome_text = (
            f"⚔️ **مرحباً بك يا أسطورة {user.first_name} في ساحة البطولات!** ⚔️\n\n"
            f"جهّز عتادك ولقبك واعتلِ عرش الصدارة. اختر من القائمة أسفله للبدء 👇"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="البطولات المنظمة حالياً 🏆",
                        callback_data="list_tournaments",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="تسجيل اللقب / الاسم 🆔",
                        url=f"https://t.me/{(asyncio.run(bot.get_me())).username}?start=set_nick",
                    )
                ],
            ]
        )
        asyncio.create_task(
            bot.send_message(
                chat_id=CHANNEL_ID,
                text=welcome_text,
                parse_mode="Markdown",
                reply_markup=kb,
            )
        )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # سيناريو المشرف
    if await is_admin(user_id):
        admin_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="إيقاد بطولة جديدة ⚔️", callback_data="create_tour"
                    )
                ]
            ]
        )
        await message.answer(
            f"مرحباً بك أيتها القائد @{username}! جاهز لتنظيم البطولة القادمة؟",
            reply_markup=admin_kb,
        )
        return

    # سيناريو العضو العادي
    if "set_nick" in message.text:
        await state.set_state(RegistrationStates.waiting_for_nickname)
        await message.answer(
            "🆔 **يرجى كتابة وحفظ لقبتك داخل اللعبة الآن:**\n(سوف نعتمد هذا اللقب في كشوفات البطولات)"
        )
    else:
        await message.answer(
            "🔒 هذا البوت مخصص فقط لتسجيل الألقاب وإدارة البطولات. لا يمكن التفاعل بحرية هنا."
        )


@router.message(StateFilter(RegistrationStates.waiting_for_nickname))
async def save_nickname(message: Message, state: FSMContext):
    user_id = message.from_user.id
    nickname = message.text.strip()
    users_db[user_id] = nickname
    await state.clear()
    await message.answer(
        f"✅ **تم حفظ لقبتك بنجاح!**\nاللقب المعتمد: `{nickname}`\nيمكنك الآن المشاركة في بطولات القناة بكل سهولة.",
        parse_mode="Markdown",
    )


# ================= 6. معالج إنشاء البطولة (المشرفين) =================
@router.callback_query(F.data == "create_tour")
async def start_tour_creation(call: CallbackQuery, state: FSMContext):
    if not await is_admin(call.from_user.id):
        return await call.answer("❌ هذا الأمر للمشرفين فقط!", show_alert=True)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="كلاش سكواد (Clash Squad)", callback_data="mode_CS"
                )
            ],
            [
                InlineKeyboardButton(
                    text="باتل رويال (Battle Royale)", callback_data="mode_BR"
                )
            ],
        ]
    )
    await state.set_state(TournamentCreationStates.game_mode)
    await call.message.edit_text(
        "🏆 **خطوة 1:** اختر نوع الروم للبطولة:", reply_markup=kb
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.game_mode), F.data.startswith("mode_")
)
async def process_mode(call: CallbackQuery, state: FSMContext):
    mode = "كلاش سكواد" if call.data == "mode_CS" else "باتل رويال"
    await state.update_data(game_mode=mode)

    if mode == "باتل رويال":
        kb_buttons = [
            [
                InlineKeyboardButton(
                    text=f"{i} سكوادات ({i*4} لاعب)", callback_data=f"squad_{i}"
                )
            ]
            for i in range(4, 11)
        ]
        await state.set_state(TournamentCreationStates.squad_count)
        await call.message.edit_text(
            "👥 **خطوة 2:** اختر عدد السكوادات المشاركة:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        )
    else:
        await state.update_data(squad_count=2, max_players=8)
        await ask_start_time(call.message, state)


@router.callback_query(
    StateFilter(TournamentCreationStates.squad_count),
    F.data.startswith("squad_"),
)
async def process_squads(call: CallbackQuery, state: FSMContext):
    squads = int(call.data.split("_")[1])
    max_players = squads * 4
    await state.update_data(squad_count=squads, max_players=max_players)
    await ask_start_time(call.message, state)


async def ask_start_time(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="بعد 30 دقيقة", callback_data="time_30"
                ),
                InlineKeyboardButton(
                    text="بعد 1 ساعة", callback_data="time_60"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="بعد 2 ساعتين", callback_data="time_120"
                ),
                InlineKeyboardButton(
                    text="بعد 3 ساعات", callback_data="time_180"
                ),
            ],
        ]
    )
    await state.set_state(TournamentCreationStates.start_time)
    await message.edit_text(
        "⏰ **خطوة 3:** حدد موعد انطلاق البطولة:", reply_markup=kb
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.start_time),
    F.data.startswith("time_"),
)
async def process_time(call: CallbackQuery, state: FSMContext):
    minutes = int(call.data.split("_")[1])
    start_dt = datetime.now() + timedelta(minutes=minutes)
    time_str = start_dt.strftime("%I:%M %p")
    await state.update_data(start_time=time_str, start_dt=start_dt)

    maps = [
        "برمودا",
        "كالاهاري",
        "بيرغاتوري",
        "نيكستيريا",
        "سولارا",
    ]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=m, callback_data=f"map_{m}"
                )
            ]
            for m in maps
        ]
    )
    await state.set_state(TournamentCreationStates.map_selection)
    await call.message.edit_text(
        "🗺️ **خطوة 4:** اختر خريطة الروم:", reply_markup=kb
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.map_selection),
    F.data.startswith("map_"),
)
async def process_map(call: CallbackQuery, state: FSMContext):
    map_name = call.data.split("_")[1]
    await state.update_data(map_name=map_name)
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_ammo,
        "ذخيرة محدودة؟",
    )


async def ask_setting(message: Message, state: FSMContext, next_state, text):
    await state.set_state(next_state)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="YES ✅", callback_data="set_YES"),
                InlineKeyboardButton(text="NO ❌", callback_data="set_NO"),
            ]
        ]
    )
    await message.edit_text(f"⚙️ **إعدادات الروم:** {text}", reply_markup=kb)


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_ammo),
    F.data.startswith("set_"),
)
async def set_ammo(call: CallbackQuery, state: FSMContext):
    await state.update_data(ammo=call.data.split("_")[1])
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_gloowall,
        "تلج محدود؟",
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_gloowall),
    F.data.startswith("set_"),
)
async def set_gloo(call: CallbackQuery, state: FSMContext):
    await state.update_data(gloowall=call.data.split("_")[1])
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_char_skill,
        "مهارة الشخصيات؟",
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_char_skill),
    F.data.startswith("set_"),
)
async def set_char(call: CallbackQuery, state: FSMContext):
    await state.update_data(char_skill=call.data.split("_")[1])
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_pet_skill,
        "مهارة الحيوان الأليف؟",
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_pet_skill),
    F.data.startswith("set_"),
)
async def set_pet(call: CallbackQuery, state: FSMContext):
    await state.update_data(pet_skill=call.data.split("_")[1])
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_airdrop,
        "إنزال جوي؟",
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_airdrop),
    F.data.startswith("set_"),
)
async def set_drop(call: CallbackQuery, state: FSMContext):
    await state.update_data(airdrop=call.data.split("_")[1])
    await ask_setting(
        call.message,
        state,
        TournamentCreationStates.setting_vehicles,
        "سيارات؟",
    )


@router.callback_query(
    StateFilter(TournamentCreationStates.setting_vehicles),
    F.data.startswith("set_"),
)
async def finalize_tournament(call: CallbackQuery, state: FSMContext):
    await state.update_data(vehicles=call.data.split("_")[1])
    data = await state.get_data()
    await state.clear()

    global tournament_counter
    tournament_counter += 1
    tour_id = tournament_counter

    data["organizer_id"] = call.from_user.id
    data["organizer_name"] = (
        call.from_user.username or call.from_user.first_name
    )
    tournaments_db[tour_id] = data
    active_registrations[tour_id] = []

    # صياغة إعلان البطولة
    announce_text = (
        f"🔥 **إعلان بطولة جديدة #{tour_id}** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ **النمط:** {data['game_mode']}\n"
        f"👥 **الحد الأقصى:** {data['max_players']} لاعب\n"
        f"🗺️ **الخريطة:** {data['map_name']}\n"
        f"⏰ **موعد الانطلاق:** {data['start_time']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ **شروط وإعدادات المباراة:**\n"
        f"• ذخيرة محدودة: {data['ammo']} | تلج محدود: {data['gloowall']}\n"
        f"• مهارة شخصيات: {data['char_skill']} | مهارة بيت: {data['pet_skill']}\n"
        f"• دروب جوي: {data['airdrop']} | سيارات: {data['vehicles']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **المنظم:** @{data['organizer_name']}\n\n"
        f"سارع بالتسجيل قبل اكتمال المقاعد! 🚀"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="إضغط للتسجيل 📝", callback_data=f"reg_{tour_id}"
                )
            ]
        ]
    )

    # نشر في القناة
    msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=announce_text,
        parse_mode="Markdown",
        reply_markup=kb,
    )
    tournaments_db[tour_id]["channel_msg_id"] = msg.message_id

    await call.message.edit_text(
        f"✅ **تم نشر البطولة بنجاح في القناة!** (معرف البطولة: #{tour_id})"
    )

    # إشعارات المشتركين وتطبيق التقرير وجدولة الإشعارات
    asyncio.create_task(broadcast_new_tour(tour_id, data['organizer_id']))
    asyncio.create_task(schedule_reports_and_reminders(tour_id))


# ================= 7. إدارة التسجيل والإشعارات =================
async def broadcast_new_tour(tour_id: int, organizer_id: int):
    for uid in users_db.keys():
        if uid != organizer_id:
            try:
                await bot.send_message(
                    chat_id=uid,
                    text=f"🚀 **بطولة جديدة أُطلقت الآن!**\nسجل اسمك في القناة قبل اكتمال العدد.",
                )
            except Exception:
                pass


@router.callback_query(F.data.startswith("reg_"))
async def register_player(call: CallbackQuery):
    tour_id = int(call.data.split("_")[1])
    user_id = call.from_user.id

    if user_id not in users_db:
        return await call.answer(
            "⚠️ يجب عليك تسجيل لقبك أولاً عبر البوت في الخاص!",
            show_alert=True,
        )

    tour = tournaments_db.get(tour_id)
    registered = active_registrations.get(tour_id, [])

    if len(registered) >= tour["max_players"]:
        return await call.answer(
            "❌ اكتمل العدد المسموح به لهذه البطولة!", show_alert=True
        )

    if user_id in registered:
        return await call.answer(
            "⚠️ أنت مسجل بالفعل في هذه البطولة!", show_alert=True
        )

    registered.append(user_id)
    await call.answer("✅ تم تسجيلك بنجاح في البطولة!", show_alert=True)

    # إغلاق التسجيل إذا اكتمل العدد
    if len(registered) >= tour["max_players"]:
        closed_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔒 اكتمل التسجيل", callback_data="closed"
                    )
                ]
            ]
        )
        await bot.edit_message_reply_markup(
            chat_id=CHANNEL_ID,
            message_id=tour["channel_msg_id"],
            reply_markup=closed_kb,
        )


async def schedule_reports_and_reminders(tour_id: int):
    tour = tournaments_db[tour_id]
    org_id = tour["organizer_id"]

    # تقرير كل 10 دقائق للمنظم
    async def periodic_report():
        while True:
            await asyncio.sleep(600)  # 10 دقائق
            registered = active_registrations.get(tour_id, [])
            players_fmt = "\n".join(
                [
                    f"• {users_db.get(uid, 'بدون لقب')} (@{(await bot.get_chat(uid)).username or 'بدون_معرف'})"
                    for uid in registered
                ]
            )
            report = (
                f"📊 **تقرير المسجلين الحالي لبطولة #{tour_id}:**\n"
                f"العدد: {len(registered)} / {tour['max_players']}\n\n"
                f"قائمة المسجلين:\n{players_fmt if players_fmt else 'لا يوجد مسجلين بعد.'}"
            )
            try:
                await bot.send_message(
                    chat_id=org_id, text=report, parse_mode="Markdown"
                )
            except Exception:
                pass
            if len(registered) >= tour["max_players"]:
                break

    asyncio.create_task(periodic_report())

    # إشعار قبل 20 دقيقة
    now = datetime.now()
    start_dt = tour["start_dt"]
    time_to_remind = (start_dt - timedelta(minutes=20)) - now

    if time_to_remind.total_seconds() > 0:
        await asyncio.sleep(time_to_remind.total_seconds())

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="إدخال الـ ID والكود 🔑",
                    callback_data=f"enter_room_{tour_id}",
                )
            ]
        ]
    )
    try:
        await bot.send_message(
            chat_id=org_id,
            text=f"⏰ **حان وقت تجهيز الروم لبطولة #{tour_id}!**\nاضغط على الزر أدناه لإرسال بيانات الدخول.",
            reply_markup=kb,
        )
    except Exception:
        pass


# ================= 8. إدخال وتوزيع بيانات الروم والنتائج =================
@router.callback_query(F.data.startswith("enter_room_"))
async def start_room_input(call: CallbackQuery, state: FSMContext):
    tour_id = int(call.data.split("_")[2])
    await state.update_data(tour_id=tour_id)
    await state.set_state(RoomDataStates.room_id_code)
    await call.message.answer(
        "📝 أرسل الآن بيانات الروم بهذا الشكل:\n`الآيدي: 123456 | الكود: 777`",
        parse_mode="Markdown",
    )


@router.message(StateFilter(RoomDataStates.room_id_code))
async def send_room_data_to_players(message: Message, state: FSMContext):
    data = await state.get_data()
    tour_id = data["tour_id"]
    room_info = message.text
    await state.clear()

    registered_users = active_registrations.get(tour_id, [])

    # إرسال للخاص للمسجلين
    for uid in registered_users:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"🔑 **بيانات روم البطولة #{tour_id}:**\n\n{room_info}\n\nبالتوفيق للجميع!",
                parse_mode="Markdown",
            )
        except Exception:
            pass

    # إعلان القناة
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f"📢 **تم إرسال بيانات الروم لبطولة #{tour_id} للمسجلين في الخاص!**\nتوجهوا للخاص فوراً.",
    )

    # طلب رفع الصورة والنتيجة
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="رفع صورة النتيجة 📸",
                    callback_data=f"upload_res_{tour_id}",
                )
            ]
        ]
    )
    await message.answer(
        "✅ تم التوزيع. بعد نهاية المباراة، اضغط الزر أدناه لنشر النتيجة.",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("upload_res_"))
async def start_result_upload(call: CallbackQuery, state: FSMContext):
    tour_id = int(call.data.split("_")[2])
    await state.update_data(tour_id=tour_id)
    await state.set_state(ResultStates.photo)
    await call.message.answer("📸 قم بإرسال صورة نتيجة المباراة الآن:")


@router.message(StateFilter(ResultStates.photo), F.photo)
async def publish_result(message: Message, state: FSMContext):
    data = await state.get_data()
    tour_id = data["tour_id"]
    tour = tournaments_db[tour_id]
    registered = active_registrations.get(tour_id, [])
    await state.clear()

    photo_id = message.photo[-1].file_id

    players_list = "\n".join(
        [
            f"• {users_db.get(uid, 'لاعب')} (@{(await bot.get_chat(uid)).username or 'بدون_معرف'})"
            for uid in registered
        ]
    )

    caption_text = (
        f"🏆 **نتائج بطولة #{tour_id}** 🏆\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **المنظم:** @{tour['organizer_name']}\n"
        f"⚔️ **المشاركون:**\n{players_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ **قيم جودة الروم والتنظيم:**"
    )

    rating_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ 1", callback_data=f"rate_1_{tour_id}"
                ),
                InlineKeyboardButton(
                    text="⭐ 2", callback_data=f"rate_2_{tour_id}"
                ),
                InlineKeyboardButton(
                    text="⭐ 3", callback_data=f"rate_3_{tour_id}"
                ),
                InlineKeyboardButton(
                    text="⭐ 4", callback_data=f"rate_4_{tour_id}"
                ),
                InlineKeyboardButton(
                    text="⭐ 5", callback_data=f"rate_5_{tour_id}"
                ),
            ]
        ]
    )

    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo_id,
        caption=caption_text,
        parse_mode="Markdown",
        reply_markup=rating_kb,
    )
    await message.answer("✅ تم نشر نتائج البطولة والتقييم بنجاح في القناة!")


@router.callback_query(F.data.startswith("rate_"))
async def process_rating(call: CallbackQuery):
    rating = call.data.split("_")[1]
    await call.answer(f"شكرًا لك! تم تسجيل تقييمك: {rating} نجوم ⭐", show_alert=True)


# ================= 9. تشغيل البوت =================
async def main():
    print("⚡ البوت يعمل الآن بنجاح ومستعد لإدارة البطولات...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
