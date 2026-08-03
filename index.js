const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// ==========================================
// التوكنات وبيانات الحساب
// ==========================================
const TELEGRAM_TOKEN = '8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc';
const GUEST_UID = "6075710142";
const GUEST_PASSWORD = "37B2ED826DC15628FE84C236D40C221437227B8055FDA78D9C3BA01427C1F944";

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });
let accessToken = GUEST_PASSWORD;

console.log("🚀 البوت يعمل الآن بنجاح تام (created by ZORO)...");

// دالة إرسال طلب الصداقة
async function sendFriendRequest(targetUID) {
    try {
        const response = await axios({
            method: 'post',
            url: 'https://client.freefiremobile.com/AddFriend',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; Garena Free Fire)',
                'X-GARENA-REGION': 'ME'
            },
            data: {
                target_uid: parseInt(targetUID)
            }
        });
        return response.status === 200 || response.data.status === 'ok';
    } catch (error) {
        console.error("خطأ في الإرسال:", error.message);
        return false;
    }
}

// أمر /start
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const text = `
✨ **أهلاً بك في نظام بوت اللوبي** ✨

📌 **الأوامر المتاحة:**
👤 \`/add [UID]\` - لإرسال طلب صداقة من البوت.

_created by ZORO_
    `;
    bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
});

// أمر /add
bot.onText(/\/add (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const targetUID = match[1].trim();

    bot.sendMessage(chatId, `⏳ جاري إرسال طلب الصداقة للـ UID: \`${targetUID}\`...`, { parse_mode: 'Markdown' });

    const result = await sendFriendRequest(targetUID);

    if (result) {
        bot.sendMessage(chatId, `✅ **تم إرسال طلب الصداقة بنجاح!**\n\nافتح فري فاير واقبل الطلب من الحساب \`${GUEST_UID}\`.\n\n_created by ZORO_`, { parse_mode: 'Markdown' });
    } else {
        bot.sendMessage(chatId, `❌ **فشل الإرسال.** تأكد من صحة الـ UID.`, { parse_mode: 'Markdown' });
    }
});
