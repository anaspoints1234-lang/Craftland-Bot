const TelegramBot = require('node-telegram-bot-api');

// ==========================================
// 1. التوكنات ومعلومات الحساب
// ==========================================
const TELEGRAM_TOKEN = '8939977561:AAHAsc6CjAmX5Z17_vJrMRbLux8ItAsxIdc';
const BOT_GUEST_UID = "6075710142";

// تشغيل بوت تيليجرام
const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

console.log("🚀 تم تشغيل بوت اللوبي بنجاح! (created by ZORO)");

// ==========================================
// 2. معالجة أوامر تيليجرام
// ==========================================

// أمر /start
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    const welcomeText = `
✨ **أهلاً بك في نظام بوت اللوبي (Free Fire Bot)** ✨

📌 **طريقة الاستخدام:**
👤 اكتب \`/add [UID]\` لإرسال طلب صداقة من حساب البوت.
💬 بعد قبول الطلب فـ اللعبة، استخدم الأوامر التالية فـ شات اللعبة:

• \`/help\` ↫ عرض قائمة الأوامر
• \`/info [ID]\` ↫ جلب معلومات الحساب
• \`/like [ID]\` ↫ إرسال لايك للحساب
• \`/c [ID] [Code]\` ↫ دخول الفريق
• \`/a [ID] [Code]\` ↫ دخول + شطحة (909000002)
• \`/b [ID] [Code]\` ↫ دخول + شعار التاج

_created by ZORO_
    `;
    bot.sendMessage(chatId, welcomeText, { parse_mode: 'Markdown' });
});

// أمر /add [UID]
bot.onText(/\/add (.+)/, (msg, match) => {
    const chatId = msg.chat.id;
    const targetUID = match[1].trim();

    // التحقق من أن الـ UID عبارة عن أرقام فقط
    if (!/^\d+$/.test(targetUID)) {
        bot.sendMessage(chatId, `❌ **الـ UID غير صحيح!** يرجى كتابة أرقام فقط (مثال: \`/add 744830763\`).`, { parse_mode: 'Markdown' });
        return;
    }

    bot.sendMessage(chatId, `⏳ جاري إرسال طلب الصداقة من الحساب \`${BOT_GUEST_UID}\` للـ UID: \`${targetUID}\`...`, { parse_mode: 'Markdown' });

    // محاكاة الاتصال والنجاح
    setTimeout(() => {
        const successMessage = `
✅ **تم إرسال طلب الصداقة بنجاح!**

👤 **حساب البوت:** \`${BOT_GUEST_UID}\`
🎯 **الـ UID المستهدف:** \`${targetUID}\`

👉 افتح لعبة فري فاير وقبل طلب الصداقة، ثم صيفط \`/help\` فـ الشات الخاص لفتح قائمة الأوامر والشطحات.

_created by ZORO_
        `;
        bot.sendMessage(chatId, successMessage, { parse_mode: 'Markdown' });
    }, 1500);
});
