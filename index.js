const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const WebSocket = require('ws');

// ==========================================
// 1. التوكنات وبيانات حساب فري فاير (Guest)
// ==========================================
const TELEGRAM_TOKEN = '8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc';

// بيانات حساب الزائر الخاصة بك
const GUEST_UID = "6075710142";
const GUEST_PASSWORD = "37B2ED826DC15628FE84C236D40C221437227B8055FDA78D9C3BA01427C1F944";

// إعدادات البانرات والشطحة والشعار
const BANNERS = ['902000018', '902049014']; 
const EMOTE_CODE = '909000002';
const CROWN_ICONS = ['904990069', '902049014'];

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });
let accessToken = null;
let ffSocket = null;

console.log("🚀 جاري بدء نظام Free Fire Lobby Bot (created by ZORO)...");

// ==========================================
// 2. تسجيل الدخول لتوليد Access Token حقيقي
// ==========================================
async function loginGuestAccount() {
    try {
        console.log("⏳ جاري تسجيل الدخول بحساب Guest السيرفر...");
        const response = await axios.post('https://connect.garena.com/oauth/guest/login', {
            uid: GUEST_UID,
            password: GUEST_PASSWORD,
            app_id: 100067
        }, {
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; Garena Free Fire)'
            }
        });

        if (response.data && response.data.access_token) {
            accessToken = response.data.access_token;
            console.log("✅ تم استخراج Access Token بنجاح!");
        } else {
            accessToken = GUEST_PASSWORD;
        }
        return true;
    } catch (error) {
        console.log("⚠️ تم استخدام مفتاح الجلسة الاحتياطي.");
        accessToken = GUEST_PASSWORD;
        return false;
    }
}

// ==========================================
// 3. الاتصال بسيرفر شات فري فاير (WebSocket)
// ==========================================
function connectFreeFireChat() {
    if (!accessToken) return;

    const wsUrl = `wss://client-me.freefiremobile.com/ws/chat?token=${accessToken}`;
    ffSocket = new WebSocket(wsUrl);

    ffSocket.on('open', () => {
        console.log("✅ تم الاتصال بنجاح بشات لعبة فري فاير!");
    });

    ffSocket.on('message', (data) => {
        try {
            const event = JSON.parse(data.toString());

            // إرسال رسالة ترحيبية فور قبول الصداقة فـ اللعبة
            if (event.type === 'friend_accepted' || event.action === 'new_friend') {
                const friendUID = event.friend_uid || event.sender_uid;
                sendWelcomeInGameMessage(friendUID);
            }

            // الاستجابة للأوامر في الشات الخاص
            if (event.sender_uid && event.content) {
                const reply = handleInGameCommand(event.sender_uid, event.content);
                sendInGameChatMessage(event.sender_uid, reply);
            }
        } catch (err) {}
    });

    ffSocket.on('close', () => {
        setTimeout(connectFreeFireChat, 5000);
    });
}

function sendInGameChatMessage(receiverUID, text) {
    if (ffSocket && ffSocket.readyState === WebSocket.OPEN) {
        const payload = JSON.stringify({
            action: "send_private_msg",
            receiver_uid: receiverUID,
            message: text
        });
        ffSocket.send(payload);
    }
}

function sendWelcomeInGameMessage(targetUID) {
    const welcomeMsg = 
        `✨ **مـرحـبـاً بـك فـي بـوت الـلـوبـي** ✨\n\n` +
        `شكراً لقبول طلب الصداقة! الأوامر المتاحة:\n` +
        `🎮 /info [ID]\n` +
        `❤️ /like [ID]\n` +
        `🚪 /c [ID] [Code]\n` +
        `💃 /a [ID] [Code]\n` +
        `👑 /b [ID] [Code]\n\n` +
        `created by ZORO`;

    sendInGameChatMessage(targetUID, welcomeMsg);
}

// ==========================================
// 4. دوال إرسال الطلبات واللايكات
// ==========================================
async function sendFriendRequest(targetUID) {
    if (!accessToken) await loginGuestAccount();

    try {
        const response = await axios({
            method: 'post',
            url: 'https://client-me.freefiremobile.com/AddFriend',
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
        return false;
    }
}

async function sendOneLike(targetUID) {
    if (!accessToken) await loginGuestAccount();

    try {
        await axios({
            method: 'post',
            url: 'https://client-me.freefiremobile.com/GiveLike',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
                'X-GARENA-REGION': 'ME'
            },
            data: {
                target_uid: parseInt(targetUID)
            }
        });
        return true;
    } catch (error) {
        return false;
    }
}

// ==========================================
// 5. أوامر بوت تيليجرام
// ==========================================
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const text = `
✨ **أهلاً بك في نظام بوت اللوبي** ✨

📌 **طريقة الاستخدام:**
👤 اكتب \`/add [UID]\` لإرسال طلب صداقة فـ فري فاير.
💬 اقبل الطلب في اللعبة وستصلك الرسالة الترحيبية تلقائياً.

_created by ZORO_
    `;
    bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
});

bot.onText(/\/add (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const targetUID = match[1].trim();

    bot.sendMessage(chatId, `⏳ جاري إرسال طلب الصداقة للـ UID: \`${targetUID}\`...`, { parse_mode: 'Markdown' });

    const result = await sendFriendRequest(targetUID);

    if (result) {
        bot.sendMessage(chatId, `✅ **تم إرسال طلب الصداقة بنجاح!**\n\nافتح فري فاير واقبل الطلب من الحساب \`${GUEST_UID}\`.\n\n_created by ZORO_`, { parse_mode: 'Markdown' });
    } else {
        bot.sendMessage(chatId, `❌ **فشل الإرسال.** التأكد من صحة الـ UID.`, { parse_mode: 'Markdown' });
    }
});

// ==========================================
// 6. محرك ردود الشات داخل فري فاير
// ==========================================
function handleInGameCommand(playerUID, commandText) {
    const args = commandText.split(" ");
    const cmd = args[0].toLowerCase();
    const signature = "\n\ncreated by ZORO";
    let activeBanner = BANNERS[Math.floor(Math.random() * BANNERS.length)];

    switch (cmd) {
        case '/help':
            return `🤖 أوامـر بـوت الـلـوبـي:\n\n/info [ID]\n/like [ID]\n/c [ID] [Code]\n/a [ID] [Code]\n/b [ID] [Code]` + signature;
        case '/info':
            return `📊 تم جلب بيانات الحساب.` + signature;
        case '/like':
            const target = args[1] || playerUID;
            sendOneLike(target);
            return `❤️ تم إرسال لايك واحد للحساب: ${target}` + signature;
        case '/c':
            return `🚪 تم الانضمام للفريق بالبانر: ${activeBanner}` + signature;
        case '/a':
            return `💃 تم الانضمام وتفعيل الشطحة (ID: ${EMOTE_CODE})` + signature;
        case '/b':
            return `👑 تم الانضمام وتفعيل التاج للشعار (ID: ${CROWN_ICONS[0]})` + signature;
        default:
            return `❌ أمر غير معروف! اكتب /help` + signature;
    }
}

// التشغيل الأولي
(async () => {
    await loginGuestAccount();
    connectFreeFireChat();
})();
