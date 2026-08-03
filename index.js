const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// التوكنات محطوطين مباشرة (تأكد أن المستودع Private ⚠️)
const TELEGRAM_TOKEN = '8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc';
const FREEFIRE_TOKEN = '37B2ED826DC15628FE84C236D40C221437227B8055FDA78D9C3BA01427C1F944';

// إعدادات البانرات والشعار
const BANNERS = ['902000018']; 
const EMOTE_CODE = '909000002';
const CROWN_ICONS = ['904990069', '902049014'];

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

console.log("🚀 البوت خدام دابا... (created by ZORO)");

function getRandomBanner() {
    const randomIndex = Math.floor(Math.random() * BANNERS.length);
    return BANNERS[randomIndex];
}

async function sendFriendRequest(targetUID) {
    try {
        await axios.post('https://client.freefiremobile.com/AddFriend', {
            target_uid: targetUID
        }, {
            headers: {
                'Authorization': `Bearer ${FREEFIRE_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });
        return true;
    } catch (error) {
        return false;
    }
}

async function sendOneLike(targetUID) {
    try {
        await axios.post('https://client.freefiremobile.com/GiveLike', {
            target_uid: targetUID
        }, {
            headers: {
                'Authorization': `Bearer ${FREEFIRE_TOKEN}`,
                'Content-Type': 'application/json'
            }
        });
        return true;
    } catch (error) {
        return false;
    }
}

// أمر /start في تيليجرام
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const text = `
✨ **أهلاً بك في نظام بوت اللوبي** ✨

📌 **طريقة الاستخدام:**
👤 اكتب \`/add [UID]\` لإرسال طلب صداقة.
💬 بعد قبول الطلب، ادخل للعبة واكتب \`/help\` في الشات الخاص مع البوت.

_created by ZORO_
    `;
    bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
});

// أمر /add في تيليجرام
bot.onText(/\/add (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const targetUID = match[1].trim();

    bot.sendMessage(chatId, `⏳ جاري إرسال طلب الصداقة للـ UID: \`${targetUID}\`...`, { parse_mode: 'Markdown' });

    const result = await sendFriendRequest(targetUID);
    
    if (result) {
        bot.sendMessage(chatId, `✅ **تم الإرسال بنجاح!**\nاقبل الطلب في اللعبة واكتب \`/help\` في المحادثة.\n\n_created by ZORO_`, { parse_mode: 'Markdown' });
    } else {
        bot.sendMessage(chatId, `❌ **فشل الإرسال.** تأكد من الـ UID أو صلاحية التوكن.`, { parse_mode: 'Markdown' });
    }
});

// ==========================================
// محاكاة أوامر اللعبة
// ==========================================
function handleInGameCommand(playerUID, commandText) {
    const args = commandText.split(" ");
    const cmd = args[0].toLowerCase();
    const signature = "\n\ncreated by ZORO";
    let activeBanner = getRandomBanner();

    switch (cmd) {
        case '/help':
            return `🤖 أوامـر بـوت الـلـوبـي:\n\n/info [ID]\n/like [ID]\n/c [ID] [Code]\n/a [ID] [Code]\n/b [ID] [Code]` + signature;
        case '/info':
            return `📊 معلومات الحساب تم جلبها بنجاح.` + signature;
        case '/like':
            const likeID = args[1];
            sendOneLike(likeID);
            return `❤️ تم إرسال لايك واحد للحساب.` + signature;
        case '/c':
            return `🚪 جاري الانضمام للفريق... (البانر النشط: ${activeBanner})` + signature;
        case '/a':
            return `💃 تم الانضمام وتفعيل الشطحة (ID: ${EMOTE_CODE})` + signature;
        case '/b':
            return `👑 تم الانضمام وتفعيل الشعار فوق الرأس (ID: ${CROWN_ICONS[0]})` + signature;
        default:
            return `❌ أمر خاطئ! اكتب /help` + signature;
    }
}
