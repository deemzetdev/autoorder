#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import re
import datetime
import logging
import time
from pathlib import Path

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile

# ==================== Konfigurasi Warna Console ====================
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    BLUE = Fore.BLUE
    ORANGE = Fore.YELLOW  # using yellow as orange
    GREEN = Fore.GREEN
    RED = Fore.RED
    WHITE = Fore.WHITE
    MAGENTA = Fore.MAGENTA
    RESET = Style.RESET_ALL
except ImportError:
    BLUE = ORANGE = GREEN = RED = WHITE = MAGENTA = RESET = ""

# ==================== Baca Konfigurasi ====================
CONFIG_FILE = "./config.js"  # sesuai permintaan user
if not os.path.exists(CONFIG_FILE):
    # fallback ke config.json
    CONFIG_FILE = "./config.json"

def load_config():
    if CONFIG_FILE.endswith(".js"):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        # Ekstrak JSON dari module.exports = { ... }
        match = re.search(r"module\.exports\s*=\s*({.*?});", content, re.DOTALL)
        if match:
            json_str = match.group(1)
            # Hapus komentar (opsional)
            json_str = re.sub(r"//.*", "", json_str)
            config = json.loads(json_str)
        else:
            raise ValueError("Tidak bisa membaca config.js, format salah")
    else:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    return config

config = load_config()
BOT_TOKEN = config.get("BOT_TOKEN")
ALLOWED_DEVELOPERS = config.get("allowedDevelopers", [])
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN tidak ditemukan di config.")
    sys.exit(1)

# ==================== Inisialisasi Bot ====================
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== Folder Penyimpanan Media ====================
MEDIA_FOLDER = "lib"
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# ==================== Data Produk & Harga ====================
# Daftar produk berdasarkan teks yang ditampilkan di /order
PRODUCTS = {
    "Suntik Tiktok (Followers)": {"price": 5000, "desc": "100 Followers"},
    "Suntik Tiktok (Like + Views)": {"price": 5000, "desc": "1000 Like"},
    "Suntik Instagram (Followers)": {"price": 7000, "desc": "1000 Followers"},
    "Suntik Instagram (Likes)": {"price": 4000, "desc": "1000 Likes"},
    "WhatsApp (React Saluran)": {"price": 7000, "desc": "100 React"},
    "WhatsApp (Followers Saluran)": {"price": 12000, "desc": "100 Followers"},
    "Surya Panel RAT Control": {"price": 50000, "desc": "1 account"},
    "Prompt JailBreak Premium": {"price": 0, "desc": "blm dijual"},
    "Otax Tools APK": {"price": 0, "desc": "blm dijual"},
    "Jasa Bug": {"price": 4000, "desc": "per nomor"},
    "Pterodactyl Panel 1GB": {"price": 1000, "desc": "1 account"},
    "Pterodactyl Panel 2GB": {"price": 2000, "desc": "1 account"},
    "Pterodactyl Panel 3GB": {"price": 3000, "desc": "1 account"},
    "Pterodactyl Panel 4GB": {"price": 4000, "desc": "1 account"},
    "Pterodactyl Panel 5GB": {"price": 5000, "desc": "1 account"},
    "Pterodactyl Panel 6GB": {"price": 6000, "desc": "1 account"},
    "Pterodactyl Panel 7GB": {"price": 7000, "desc": "1 account"},
    "Pterodactyl Panel 8GB": {"price": 8000, "desc": "1 account"},
    "Pterodactyl Panel 9GB": {"price": 9000, "desc": "1 account"},
    "Pterodactyl Panel 10GB": {"price": 10000, "desc": "1 account"},
    "Pterodactyl Panel Unli": {"price": 12000, "desc": "1 account"},
}
# Produk yang belum dijual (harga 0) akan diabaikan saat order
ACTIVE_PRODUCTS = {k: v for k, v in PRODUCTS.items() if v["price"] > 0}

# ==================== State Management ====================
user_states = {}  # {user_id: {'state': 'waiting_product', 'order': {...}}}
pending_orders = {}  # {payment_id: {'user_id': int, 'product': str, 'price': int, 'method': str, 'chat_id': int, 'msg_id': int}}

# ==================== Fungsi Bantuan ====================
def save_media(message, file_type):
    """Simpan foto/audio/video ke folder lib"""
    try:
        if file_type == "photo":
            file_info = bot.get_file(message.photo[-1].file_id)
            ext = ".jpg"
        elif file_type == "audio":
            file_info = bot.get_file(message.audio.file_id)
            ext = ".mp3"
        elif file_type == "video":
            file_info = bot.get_file(message.video.file_id)
            ext = ".mp4"
        else:
            return None
        file_name = f"{file_type}_{message.from_user.id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(MEDIA_FOLDER, file_name)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        return file_path
    except Exception as e:
        print(f"Gagal simpan media: {e}")
        return None

def generate_payment_id():
    """Buat ID pembayaran format QRIS-DDMMYYYY"""
    return f"QRIS-{datetime.datetime.now().strftime('%d%m%Y')}"

def get_product_price(product_name):
    """Ambil harga produk dari nama"""
    for name, data in ACTIVE_PRODUCTS.items():
        if name.lower() in product_name.lower():
            return data["price"]
    return None

def format_price(price):
    """Format harga ke Rupiah"""
    return f"Rp. {price:,}".replace(",", ".")

def send_log(user):
    """Kirim log ke console dengan warna"""
    print(f"{BLUE}╭─────❒ {ORANGE}「 𝔑𝔢𝔴 ℭ𝔥𝔞𝔱! 」{RESET}")
    print(f"{BLUE}│{GREEN} Nama: {RED}{user.first_name} {user.last_name or ''}{RESET}")
    print(f"{BLUE}│{GREEN} ID: {RED}{user.id}{RESET}")
    print(f"{BLUE}│")
    print(f"{BLUE}│{WHITE} © {MAGENTA}Powered by Zetz{RESET}")
    print(f"{BLUE}└──────────❒{RESET}")

# ==================== Handler Command ====================
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    send_log(user)
    # Kirim video menu.mp4 (asumsi file ada)
    try:
        with open("menu.mp4", "rb") as video:
            bot.send_video(message.chat.id, video, caption=None)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Video menu.mp4 tidak ditemukan.")
    # Kirim audio menu.mp3 dengan judul
    try:
        with open("menu.mp3", "rb") as audio:
            bot.send_audio(message.chat.id, audio, title="Welcome To My BOTZ!")
    except FileNotFoundError:
        bot.send_message(message.chat.id, "Audio menu.mp3 tidak ditemukan.")
    # Buat tombol menu
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🛒 𝕺𝖗𝖉𝖊𝖗 𝕭𝖆𝖗𝖆𝖓𝖌", callback_data="order")
    btn2 = InlineKeyboardButton("🎮 𝕱𝖚𝖓 𝕸𝖊𝖓𝖚", callback_data="funmenu")
    btn3 = InlineKeyboardButton("🧐 𝕺𝕾𝕴𝕹𝕿 𝕸𝕰𝕹𝖀", callback_data="osintmenu")
    btn4 = InlineKeyboardButton("🦠 𝕽𝕬𝕿 𝕸𝕰𝕹𝖀", callback_data="ratmenu")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "( 👋 ) Halo! Saya adalah bot ZetzMD. Saya dibuat oleh DimzSelole. Terimakasih sudah menggunakan bot saya , silahkan pilih menu dibawah ini! 🔽", reply_markup=markup)

@bot.message_handler(commands=['order'])
def order_cmd(message):
    user = message.from_user
    # Kirim video menu.mp4
    try:
        with open("menu.mp4", "rb") as video:
            bot.send_video(message.chat.id, video, caption=None)
    except FileNotFoundError:
        pass
    # Kirim daftar produk
    text = """→ 𝕷𝕴𝕾𝕿 𝕭𝕬𝕽𝕬𝕹𝕲 ←

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

╭─────❒ 「 Host 」
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
Example: Hack/JasaBug"""
    bot.send_message(message.chat.id, text)
    # Set state waiting for product
    user_states[message.from_user.id] = {"state": "waiting_product", "order": {}}

@bot.message_handler(commands=['funmenu', 'osintmenu', 'ratmenu'])
def fun_menus(message):
    cmd = message.text[1:]
    # Kirim video
    try:
        with open("menu.mp4", "rb") as video:
            bot.send_video(message.chat.id, video, caption=None)
    except FileNotFoundError:
        pass
    if cmd == "funmenu":
        text = "\n╭─────❒ 「 𝕱𝖀𝕹 𝕸𝕰𝕹𝖀 」\n│Lom Rilis lgi cape\n└──────────❒"
    elif cmd == "osintmenu":
        text = "\n╭─────❒ 「 𝕺𝕾𝕴𝕹𝕿 𝕸𝕰𝕹𝖀 」\n│Lom Rilis lgi cape\n└──────────❒"
    else:
        text = "\n╭─────❒ 「 𝕽𝕬𝕿 𝕸𝕰𝕹𝖀 」\n│Lom Rilis lgi cape\n└──────────❒"
    bot.send_message(message.chat.id, text)

# ==================== Handler Pesan Teks (Product Input) ====================
@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get("state") == "waiting_product")
def handle_product_selection(message):
    user_id = message.from_user.id
    product_text = message.text.strip()
    # Cari produk yang cocok
    selected_product = None
    for name in ACTIVE_PRODUCTS.keys():
        if name.lower() in product_text.lower():
            selected_product = name
            break
    if not selected_product:
        bot.send_message(message.chat.id, "❌ Produk tidak ditemukan. Silakan ketik nama produk yang sesuai dari daftar.")
        return
    price = ACTIVE_PRODUCTS[selected_product]["price"]
    # Simpan sementara
    user_states[user_id]["order"] = {
        "product": selected_product,
        "price": price,
        "total": price + 1000  # admin fee 1000
    }
    # Tampilkan metode pembayaran
    markup = InlineKeyboardMarkup(row_width=2)
    btn_qris = InlineKeyboardButton("📷 QRIS (Recommend)", callback_data=f"pay_qris_{user_id}_{selected_product}_{price}")
    btn_nope = InlineKeyboardButton("💳 NOPE", callback_data=f"pay_nope_{user_id}_{selected_product}_{price}")
    markup.add(btn_qris, btn_nope)
    bot.send_message(message.chat.id, "[ 🔽 ] Pilih Metode Pembayaran", reply_markup=markup)
    # Hapus state waiting_product, nanti state akan di-set setelah pemilihan metode
    user_states[user_id]["state"] = "waiting_payment_method"

# ==================== Handler Callback Query ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    # Handle tombol menu dari start
    if data == "order":
        bot.answer_callback_query(call.id)
        order_cmd(call.message)
        return
    elif data == "funmenu":
        bot.answer_callback_query(call.id)
        fun_menus(call.message)
        return
    elif data == "osintmenu":
        bot.answer_callback_query(call.id)
        fun_menus(call.message)
        return
    elif data == "ratmenu":
        bot.answer_callback_query(call.id)
        fun_menus(call.message)
        return

    # Handle pembayaran
    if data.startswith("pay_qris_") or data.startswith("pay_nope_"):
        parts = data.split("_")
        method = parts[0].replace("pay_", "")  # qris atau nope
        # Ambil data dari callback
        # Format: pay_qris_<user_id>_<product>_<price>
        # Tapi product bisa mengandung spasi, jadi kita gabung kembali
        # Lebih aman menggunakan state yang sudah disimpan
        order_data = user_states.get(user_id, {}).get("order", {})
        if not order_data:
            bot.answer_callback_query(call.id, "Sesi order habis, silakan /order ulang.")
            return
        product = order_data["product"]
        price = order_data["price"]
        total = price + 1000
        payment_id = generate_payment_id()
        # Simpan pending order
        pending_orders[payment_id] = {
            "user_id": user_id,
            "product": product,
            "price": price,
            "method": method.upper(),
            "chat_id": chat_id,
            "msg_id": msg_id
        }
        # Kirim pesan sesuai metode
        if method == "qris":
            # Kirim gambar qris.png (asumsi file ada)
            try:
                with open("qris.png", "rb") as qr:
                    bot.send_photo(chat_id, qr, caption=f"""🏦 QRIS PAYMENT MANUAL 🏦
━━━━━━━━━━━━━━━━━━━━━
🧾 ID Pembayaran: {payment_id}
💰 Jumlah Harga: {format_price(price)}
🧾 Biaya Admin: Rp. 1000
💳 Total Pembayaran: {format_price(total)}
⏰ Status: Menunggu Bukti

• 🧩 Item: {product}

💡 Panduan Pembayaran:
1. Scan kode QR di atas
2. Bayar PAS sesuai nominal total
3. Kirim Foto Bukti Transfer ke bot ini
4. Admin akan memproses pesananmu segera

⚠️ Catatan:
• Simpan ID Pembayaran untuk referensi
• Transaksi diproses manual oleh Admin
• Klik tombol di bawah jika ingin membatalkan""")
            except FileNotFoundError:
                bot.send_message(chat_id, "Gambar QRIS tidak ditemukan.")
            # Tambah tombol batalkan
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❎ Batalkan Pesanan", callback_data=f"cancel_{payment_id}"))
            bot.send_message(chat_id, "Tekan tombol jika ingin membatalkan", reply_markup=markup)
        elif method == "nope":
            text = f"""💳 NOPE PAYMENT 💳
━━━━━━━━━━━━━━━━━━━━━
🧾 ID Pembayaran: {payment_id}
💰 Jumlah Harga: {format_price(price)}
🧾 Biaya Admin: Rp. 1000
💳 Total Pembayaran: {format_price(total)}
⏰ Status: Menunggu Bukti

• 🧩 Item: {product}

💰 List Nope:
1. 6285815977478 (Gopay)
2. 6285815977478 (Ovo)
3. 6285815977478 (Shopee Pay)

⚠️ Catatan:
• Simpan ID Pembayaran untuk referensi
• Transaksi diproses manual oleh Admin
• Klik tombol di bawah jika ingin membatalkan"""
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("❎ Batalkan Pesanan", callback_data=f"cancel_{payment_id}"))
            bot.send_message(chat_id, text, reply_markup=markup)
        # Set state waiting for proof
        user_states[user_id] = {"state": "waiting_proof", "order": order_data, "payment_id": payment_id}
        bot.answer_callback_query(call.id)
        return

    # Handle cancel order
    if data.startswith("cancel_"):
        payment_id = data.split("_")[1]
        # Hapus pending order dan state
        if payment_id in pending_orders:
            del pending_orders[payment_id]
        if user_id in user_states:
            del user_states[user_id]
        bot.send_message(chat_id, "❌ Pesanan dibatalkan.")
        bot.answer_callback_query(call.id)
        return

    # Handle approve/reject from developer
    if data.startswith("approve_") or data.startswith("reject_"):
        # Format: approve_<payment_id>_<user_id>
        parts = data.split("_")
        action = parts[0]
        payment_id = parts[1]
        target_user_id = int(parts[2])
        order = pending_orders.get(payment_id)
        if not order:
            bot.answer_callback_query(call.id, "Pesanan tidak ditemukan.")
            return
        if action == "approve":
            # Kirim sukses ke user
            bot.send_message(target_user_id, "[ ✅ ] Pembayaran telah berhasil, Cek pv lain untuk melihat hasil!")
            # Kirim ke group -1003620990124
            group_id = -1003620990124
            try:
                # Ambil nama user
                user_info = bot.get_chat(target_user_id)
                user_name = user_info.first_name
                # Kirim foto success.png (asumsi ada)
                with open("success.png", "rb") as img:
                    caption = f"""⚡ TRANSAKSI BERHASIL ⚡
──────────────────────

👤 𝗣𝗘𝗟𝗔𝗡𝗚𝗚𝗔𝗡
├ Nama : {user_name}
└ ID   : {target_user_id}

📦 𝗣𝗘𝗦𝗔𝗡𝗔𝗡
├ Item : {order['product']}
└ Via  : {order['method']}

💰 𝗣𝗘𝗠𝗕𝗔𝗬𝗔𝗥𝗔𝗡
├ Harga: {format_price(order['price'])}
├ Biaya Admin: Rp. 1000
└ Total: {format_price(order['price'] + 1000)}

✅ 𝗩𝗔𝗟𝗜𝗗𝗔𝗦𝗜
├ Waktu: {datetime.datetime.now().strftime('%d/%m/%Y | %H:%M')} WIB
└ Stat : BERHASIL (SUCCESS)

──────────────────────
Sistem Otomatis"""
                    bot.send_photo(group_id, img, caption=caption)
            except Exception as e:
                print(f"Gagal kirim ke grup: {e}")
            # Hapus order
            del pending_orders[payment_id]
            if target_user_id in user_states:
                del user_states[target_user_id]
            bot.answer_callback_query(call.id, "Pesanan disetujui")
        elif action == "reject":
            bot.send_message(target_user_id, "[ ❎ ] Pembayaran tidak diterima...")
            del pending_orders[payment_id]
            if target_user_id in user_states:
                del user_states[target_user_id]
            bot.answer_callback_query(call.id, "Pesanan ditolak")
        # Hapus pesan callback
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
        return

# ==================== Handler Bukti Pembayaran (Foto) ====================
@bot.message_handler(content_types=['photo'])
def handle_proof_photo(message):
    user_id = message.from_user.id
    if user_states.get(user_id, {}).get("state") != "waiting_proof":
        # Simpan foto tetap disimpan ke lib
        save_media(message, "photo")
        return
    # Simpan foto bukti
    file_path = save_media(message, "photo")
    if not file_path:
        bot.reply_to(message, "Gagal menyimpan bukti, coba lagi.")
        return
    order_data = user_states[user_id]["order"]
    payment_id = user_states[user_id]["payment_id"]
    # Kirim pesan pending ke user
    bot.send_message(user_id, "[ 🔀 ] Bukti Pembayaran masih dikirim ke database untuk melakukan pengecekan")
    # Forward ke semua allowed developers
    for dev_id in ALLOWED_DEVELOPERS:
        try:
            # Kirim foto bukti
            with open(file_path, "rb") as img:
                bot.send_photo(dev_id, img, caption=f"Apakah kamu menyetujui bukti pembayaran ini? \nUser: t.me/{message.from_user.username or message.from_user.id}")
            # Tambah inline buttons
            markup = InlineKeyboardMarkup()
            btn_yes = InlineKeyboardButton("✅ Setujui", callback_data=f"approve_{payment_id}_{user_id}")
            btn_no = InlineKeyboardButton("❎ Tidak Setuju", callback_data=f"reject_{payment_id}_{user_id}")
            markup.add(btn_yes, btn_no)
            bot.send_message(dev_id, "Pilih tindakan:", reply_markup=markup)
        except Exception as e:
            print(f"Gagal kirim ke developer {dev_id}: {e}")

# ==================== Handler Media Lain (Audio, Video) ====================
@bot.message_handler(content_types=['audio', 'video'])
def handle_media(message):
    # Simpan semua audio/video yang dikirim user ke folder lib
    if message.audio:
        save_media(message, "audio")
    elif message.video:
        save_media(message, "video")

# ==================== Main Loop ====================
if __name__ == "__main__":
    print("Bot ZetzMD started...")
    bot.infinity_polling()
