const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const path = require('path');
const chalk = require('chalk');
const moment = require('moment-timezone');

// Load config
const config = require('./config');
const token = config.BOT_TOKEN;
const developers = config.allowedDevelopers.map(id => String(id));

// Inisialisasi bot
const bot = new TelegramBot(token, { polling: true });

// Folder media
const mediaPath = path.join(__dirname, 'lib');
const menuVideo = path.join(mediaPath, 'menu.mp4');
const menuAudio = path.join(mediaPath, 'menu.mp3');
const qrisImage = path.join(mediaPath, 'qris.png');
const successImage = path.join(mediaPath, 'success.png');

// State management
const userStates = new Map(); // userId -> { step, product, price, paymentMethod, paymentId, total }

// Product database
const products = {
    // Suntik Sosmed
    "Suntik Tiktok (Followers)": 5000,
    "Suntik Tiktok (Like + Views)": 5000,
    "Suntik Instagram (Followers)": 7000,
    "Suntik Instagram (Likes)": 4000,
    "WhatsApp (React Saluran)": 7000,
    "WhatsApp (Followers Saluran)": 12000,
    // HACK
    "Surya Panel RAT Control": 50000,
    "Jasa Bug": 4000,
    // Host (1GB-10GB + Unli)
    "Pterodactyl Panel 1GB": 1000,
    "Pterodactyl Panel 2GB": 2000,
    "Pterodactyl Panel 3GB": 3000,
    "Pterodactyl Panel 4GB": 4000,
    "Pterodactyl Panel 5GB": 5000,
    "Pterodactyl Panel 6GB": 6000,
    "Pterodactyl Panel 7GB": 7000,
    "Pterodactyl Panel 8GB": 8000,
    "Pterodactyl Panel 9GB": 9000,
    "Pterodactyl Panel 10GB": 10000,
    "Pterodactyl Panel Unli": 12000,
};

// Helper: cari produk berdasarkan teks user
function findProduct(text) {
    const normalized = text.trim().toLowerCase();
    for (let [product, price] of Object.entries(products)) {
        if (normalized.includes(product.toLowerCase())) {
            return { product, price };
        }
    }
    return null;
}

// Helper: format rupiah
function formatRupiah(amount) {
    return `Rp. ${amount.toLocaleString('id-ID')}`;
}

// Helper: generate payment ID
function generatePaymentId() {
    const date = moment().tz('Asia/Jakarta').format('DDMMYYYY');
    return `PAY-${date}`;
}

// Helper: log masuk chat
function logNewChat(user) {
    console.log(
        chalk.blue('╭─────❒ ') + chalk.magenta('「 𝔑𝔢𝔴 ℭ𝔥𝔞𝔱! 」') + '\n' +
        chalk.blue('│') + chalk.green(' Nama: ') + chalk.red(user.first_name || 'Unknown') + '\n' +
        chalk.blue('│') + chalk.green(' ID: ') + chalk.red(user.id) + '\n' +
        chalk.blue('│') + '\n' +
        chalk.blue('│') + chalk.white('© ') + chalk.magenta('Powered by Zetz') + '\n' +
        chalk.blue('└──────────❒')
    );
}

// Handler untuk /start
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const user = msg.from;
    logNewChat(user);

    // Reset state user
    userStates.delete(chatId);

    // Kirim video menu
    try {
        await bot.sendVideo(chatId, menuVideo);
    } catch (err) {
        console.error('Gagal kirim video menu:', err.message);
        await bot.sendMessage(chatId, '⚠️ Video menu tidak ditemukan.');
    }

    // Kirim teks dengan tombol inline
    const inlineKeyboard = {
        inline_keyboard: [
            [
                { text: '🛒 𝕺𝖗𝖉𝖊𝖗 𝕭𝖆𝖗𝖆𝖓𝖌', callback_data: 'order' },
                { text: '🎮 𝕱𝖚𝖓 𝕸𝖊𝖓𝖚', callback_data: 'funmenu' }
            ],
            [
                { text: '🧐 𝕺𝕾𝕴𝕹𝕿 𝕸𝕰𝕹𝖀', callback_data: 'osintmenu' },
                { text: '🦠 𝕽𝕬𝕿 𝕸𝕰𝕹𝖀', callback_data: 'ratmenu' }
            ]
        ]
    };

    await bot.sendMessage(chatId,
        '( 👋 ) Halo! Saya adalah bot ZetzMD. Saya dibuat oleh DimzSelole. Terimakasih sudah menggunakan bot saya , silahkan pilih menu dibawah ini! 🔽',
        { reply_markup: inlineKeyboard }
    );

    // Kirim audio menu
    try {
        await bot.sendAudio(chatId, menuAudio, { title: 'Welcome To My BOTZ!' });
    } catch (err) {
        console.error('Gagal kirim audio menu:', err.message);
    }
});

// Handler callback query (tombol inline)
bot.on('callback_query', async (callbackQuery) => {
    const msg = callbackQuery.message;
    const chatId = msg.chat.id;
    const data = callbackQuery.data;
    const user = callbackQuery.from;

    // Acknowledge callback
    await bot.answerCallbackQuery(callbackQuery.id);

    if (data === 'order') {
        // Kirim video menu (sama seperti start)
        try {
            await bot.sendVideo(chatId, menuVideo);
        } catch (err) {
            console.error('Gagal kirim video order:', err.message);
        }

        // Kirim daftar produk
        const productList = `
╭─────❒ 「 Suntik Sosmed 」
│
│1. Suntik Tiktok (Followers) - Rp. 5k/100F
│2. Suntik Tiktok (Like + Views) - Rp. 5k/1000L
│3. Suntik Instagram (Followers) - Rp. 7k/1000F
│4. Suntik Instagram (Likes) - Rp. 4k/1000L
│5. WhatsApp (React Saluran) - Rp. 7k/100RS
│6. WhatsApp (Followers Saluran) - Rp. 12k/100FS
│
└──────────❒

╭─────❒ 「 HACK  」
│
│1. Surya Panel RAT Control - Rp. 50k/account
│2. Prompt JailBreak Premium (blm dijual)
│3. Otax Tools APK (blm dijual)
│4. Jasa Bug - Rp. 4k/nomor
│
└──────────❒

╭─────❒ 「 Host  」
│
│1. Pterodactyl Panel 1GB - Rp. 1k/account
│2. Pterodactyl Panel 2GB - Rp. 2k/account
│3. Pterodactyl Panel 3GB - Rp. 3k/account
│4. Pterodactyl Panel 4GB - Rp. 4k/account
│5. Pterodactyl Panel 5GB - Rp. 5k/account
│6. Pterodactyl Panel 6GB - Rp. 6k/account
│7. Pterodactyl Panel 7GB - Rp. 7k/account
│8. Pterodactyl Panel 8GB - Rp. 8k/account
│9. Pterodactyl Panel 9GB - Rp. 9k/account
│10. Pterodactyl Panel 10GB - Rp. 10k/account
│11. Pterodactyl Panel Unli - Rp. 12k/account
│
└──────────❒

Silahkan ketik tipe/namaproduk... 
Example: Hack/JasaBug
        `;
        await bot.sendMessage(chatId, productList);
        // Set state menunggu produk
        userStates.set(chatId, { step: 'awaiting_product' });
    }
    else if (data === 'funmenu') {
        await bot.sendVideo(chatId, menuVideo);
        await bot.sendMessage(chatId, `
╭─────❒ 「 𝕱𝖀𝕹 𝕸𝕰𝕹𝖀 」
│Lom Rilis lgi cape
└──────────❒
        `);
    }
    else if (data === 'osintmenu') {
        await bot.sendVideo(chatId, menuVideo);
        await bot.sendMessage(chatId, `
╭─────❒ 「 𝕺𝕾𝕴𝕹𝕿 𝕸𝕰𝕹𝖀 」
│Lom Rilis lgi cape
└──────────❒
        `);
    }
    else if (data === 'ratmenu') {
        await bot.sendVideo(chatId, menuVideo);
        await bot.sendMessage(chatId, `
╭─────❒ 「 𝕽𝕬𝕿 𝕸𝕰𝕹𝖀 」
│Lom Rilis lgi cape
└──────────❒
        `);
    }
    else if (data === 'qris') {
        const state = userStates.get(chatId);
        if (!state || state.step !== 'awaiting_payment') return;

        state.paymentMethod = 'QRIS';
        const paymentId = generatePaymentId();
        state.paymentId = paymentId;
        const total = state.price + 1000; // admin fee 1000
        state.total = total;

        // Kirim QRIS image dan instruksi
        try {
            await bot.sendPhoto(chatId, qrisImage);
        } catch (err) {
            console.error('Gagal kirim QRIS image:', err.message);
        }

        const qrisText = `
🏦 QRIS PAYMENT MANUAL 🏦
━━━━━━━━━━━━━━━━━━━━━
🧾 ID Pembayaran: ${paymentId}
💰 Jumlah Harga: ${formatRupiah(state.price)}
🧾 Biaya Admin: Rp. 1000
💳 Total Pembayaran: ${formatRupiah(total)}
⏰ Status: Menunggu Bukti

• 🧩 Item: ${state.product}

💡 Panduan Pembayaran:
1. Scan kode QR di atas
2. Bayar PAS sesuai nominal total
3. Kirim Foto Bukti Transfer ke bot ini
4. Admin akan memproses pesananmu segera

⚠️ Catatan:
• Simpan ID Pembayaran untuk referensi
• Transaksi diproses manual oleh Admin
• Klik tombol di bawah jika ingin membatalkan
        `;

        const cancelKeyboard = {
            inline_keyboard: [
                [{ text: '❎ Batalkan Pesanan', callback_data: 'cancel_order' }]
            ]
        };
        await bot.sendMessage(chatId, qrisText, { reply_markup: cancelKeyboard });
        state.step = 'awaiting_proof';
        userStates.set(chatId, state);
    }
    else if (data === 'nope') {
        const state = userStates.get(chatId);
        if (!state || state.step !== 'awaiting_payment') return;

        state.paymentMethod = 'NOPE';
        const paymentId = generatePaymentId();
        state.paymentId = paymentId;
        const total = state.price + 1000;
        state.total = total;

        const nopeText = `
💳 NOPE PAYMENT 💳
━━━━━━━━━━━━━━━━━━━━━
🧾 ID Pembayaran: ${paymentId}
💰 Jumlah Harga: ${formatRupiah(state.price)}
🧾 Biaya Admin: Rp. 1000
💳 Total Pembayaran: ${formatRupiah(total)}
⏰ Status: Menunggu Bukti

• 🧩 Item: ${state.product}

💰 List Nope:
1. 6285815977478 (Gopay)
2. 6285815977478 (Ovo)
3. 6285815977478 (Shopee Pay)

⚠️ Catatan:
• Simpan ID Pembayaran untuk referensi
• Transaksi diproses manual oleh Admin
• Klik tombol di bawah jika ingin membatalkan
        `;

        const cancelKeyboard = {
            inline_keyboard: [
                [{ text: '❎ Batalkan Pesanan', callback_data: 'cancel_order' }]
            ]
        };
        await bot.sendMessage(chatId, nopeText, { reply_markup: cancelKeyboard });
        state.step = 'awaiting_proof';
        userStates.set(chatId, state);
    }
    else if (data === 'cancel_order') {
        userStates.delete(chatId);
        await bot.sendMessage(chatId, '✅ Pesanan dibatalkan.');
    }
    else if (data.startsWith('approve_') || data.startsWith('reject_')) {
        // Handle approve/reject dari developer
        const orderId = data.split('_')[1];
        const order = pendingOrders.get(orderId);
        if (!order) {
            await bot.answerCallbackQuery(callbackQuery.id, { text: 'Order tidak ditemukan.' });
            return;
        }

        if (data.startsWith('approve_')) {
            // Kirim sukses ke user
            const userChatId = order.userId;
            await bot.sendMessage(userChatId, '[ ✅ ] Pembayaran telah berhasil, Cek pv lain untuk melihat hasil! ');

            // Kirim ke group -1003620990124
            const groupId = -1003620990124;
            const now = moment().tz('Asia/Jakarta').format('DD/MM/YYYY | HH:mm') + ' WIB';
            const caption = `
⚡ TRANSAKSI BERHASIL ⚡
──────────────────────

👤 𝗣𝗘𝗟𝗔𝗡𝗚𝗚𝗔𝗡
├ Nama : ${order.userName}
└ ID   : ${order.userId}

📦 𝗣𝗘𝗦𝗔𝗡𝗔𝗡
├ Item : ${order.product}
└ Via  : ${order.paymentMethod}

💰 𝗣𝗘𝗠𝗕𝗔𝗬𝗔𝗥𝗔𝗡
├ Harga: ${formatRupiah(order.price)}
├ Biaya Admin: Rp. 1000
└ Total: ${formatRupiah(order.total)}

✅ 𝗩𝗔𝗟𝗜𝗗𝗔𝗦𝗜
├ Waktu: ${now}
└ Stat : BERHASIL (SUCCESS)

──────────────────────
Sistem Otomatis
            `;

            try {
                await bot.sendPhoto(groupId, successImage, { caption });
            } catch (err) {
                console.error('Gagal kirim ke group:', err.message);
            }

            // Hapus order dari pending
            pendingOrders.delete(orderId);
            await bot.answerCallbackQuery(callbackQuery.id, { text: 'Pembayaran disetujui!' });
        }
        else if (data.startsWith('reject_')) {
            // Kirim penolakan ke user
            const userChatId = order.userId;
            await bot.sendMessage(userChatId, '[ ❎ ] Pembayaran tidak diterima...');
            pendingOrders.delete(orderId);
            await bot.answerCallbackQuery(callbackQuery.id, { text: 'Pembayaran ditolak.' });
        }
    }
});

// Handler untuk pesan teks (produk dari /order)
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    const user = msg.from;

    // Jika bukan teks, ignore
    if (!text) return;

    const state = userStates.get(chatId);
    if (!state) return;

    // Step 1: menunggu produk
    if (state.step === 'awaiting_product') {
        const found = findProduct(text);
        if (!found) {
            await bot.sendMessage(chatId, '❌ Produk tidak ditemukan. Silakan ketik ulang nama produk sesuai daftar.');
            return;
        }

        // Cek apakah produk tidak dijual
        if (found.product === 'Prompt JailBreak Premium' || found.product === 'Otax Tools APK') {
            await bot.sendMessage(chatId, '❌ Produk ini belum dijual. Pilih produk lain.');
            return;
        }

        state.product = found.product;
        state.price = found.price;
        state.step = 'awaiting_payment';
        userStates.set(chatId, state);

        // Tampilkan pilihan metode pembayaran
        const paymentKeyboard = {
            inline_keyboard: [
                [
                    { text: '📷 QRIS (Recommend)', callback_data: 'qris' },
                    { text: '💳 NOPE', callback_data: 'nope' }
                ]
            ]
        };
        await bot.sendMessage(chatId, '[ 🔽 ] Pilih Metode Pembayaran', { reply_markup: paymentKeyboard });
    }
    // Step 2: menunggu bukti foto
    else if (state.step === 'awaiting_proof') {
        // Hanya terima foto
        if (!msg.photo) {
            await bot.sendMessage(chatId, '❌ Harap kirim foto bukti pembayaran.');
            return;
        }

        // Dapatkan foto terbesar
        const photo = msg.photo[msg.photo.length - 1];
        const fileId = photo.file_id;

        // Kirim notifikasi ke user
        await bot.sendMessage(chatId, '[ 🔀 ] Bukti Pembayaran masih dikirim ke database untuk melakukan pengecekan');

        // Simpan order di pendingOrders (global)
        const orderId = Date.now() + '_' + chatId;
        const order = {
            userId: chatId,
            userName: user.first_name || user.username || 'Unknown',
            product: state.product,
            price: state.price,
            paymentMethod: state.paymentMethod,
            total: state.total,
            paymentId: state.paymentId,
            photoFileId: fileId,
        };
        pendingOrders.set(orderId, order);

        // Kirim ke semua developer
        for (const devId of developers) {
            try {
                await bot.sendPhoto(devId, fileId, {
                    caption: `Apakah kamu menyetujui bukti pembayaran ini? \nUser: t.me/${user.username || 'Unknown'}`,
                    reply_markup: {
                        inline_keyboard: [
                            [
                                { text: '✅ Setujui', callback_data: `approve_${orderId}` },
                                { text: '❎ Tidak Setuju', callback_data: `reject_${orderId}` }
                            ]
                        ]
                    }
                });
            } catch (err) {
                console.error(`Gagal kirim ke developer ${devId}:`, err.message);
            }
        }

        // Hapus state user karena pesanan sudah dikirim ke developer
        userStates.delete(chatId);
    }
});

// Global map untuk pending orders
const pendingOrders = new Map();

// Handle error polling
bot.on('polling_error', (err) => console.error('Polling error:', err));
