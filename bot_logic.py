# bot_logic.py
import os
import logging
import zipfile
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Storage ----------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- Global Stats ----------
bot_stats = {
    "status": "Starting",
    "hosted_bots": 0,
    "total_uploads": 0,
    "last_upload": None,
    "uploads": [],
}

# ---------- Auth Check ----------
def is_authorized(user_id: int) -> bool:
    allowed = os.environ.get("ALLOWED_USER_IDS", "").strip()
    if not allowed:
        return True
    ids = [x.strip() for x in allowed.split(",") if x.strip()]
    return str(user_id) in ids

# ---------- Commands ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text("❌ Aap authorized nahi ho. Admin se contact karo.")
        return

    await update.message.reply_text(
        "👋 *Bot Hoster* mein welcome!\n\n"
        "Apni bot file bhej do — `.py` ya `.zip` accept karta hoon.\n\n"
        "📤 Bas file attach karke send karo, main host kar dunga.",
        parse_mode="Markdown",
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        return
    await update.message.reply_text(
        f"📊 *Bot Hoster Status*\n\n"
        f"Hosted Bots: `{bot_stats['hosted_bots']}`\n"
        f"Total Uploads: `{bot_stats['total_uploads']}`\n"
        f"Last Upload: `{bot_stats['last_upload'] or '—'}`",
        parse_mode="Markdown",
    )

# ---------- File Handler ----------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user
    document = msg.document

    if not is_authorized(user.id):
        await msg.reply_text("❌ Aap authorized nahi ho.")
        return

    if not document:
        return

    filename = document.file_name or "unknown"
    if not (filename.endswith(".py") or filename.endswith(".zip")):
        await msg.reply_text("❌ Sirf `.py` ya `.zip` file bhejo bhai.")
        return

    try:
        tg_file = await document.get_file()
        save_path = os.path.join(UPLOAD_DIR, f"{user.id}_{filename}")
        await tg_file.download_to_drive(save_path)
    except Exception as e:
        logger.exception("Download failed")
        await msg.reply_text(f"⚠️ File download fail: {e}")
        return

    extracted_note = ""
    if filename.endswith(".zip"):
        try:
            extract_dir = os.path.join(UPLOAD_DIR, f"{user.id}_{filename[:-4]}")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(save_path, "r") as z:
                z.extractall(extract_dir)
            extracted_note = f"\n📂 Extract: `{extract_dir}`"
        except Exception as e:
            await msg.reply_text(f"⚠️ Zip extract fail: {e}")
            return

    bot_stats["hosted_bots"] += 1
    bot_stats["total_uploads"] += 1
    bot_stats["last_upload"] = filename
    bot_stats["uploads"].append({
        "name": filename,
        "size": document.file_size or 0,
        "user_id": user.id,
        "username": user.username or user.first_name or "unknown",
        "time": datetime.utcnow().isoformat(),
    })
    bot_stats["uploads"] = bot_stats["uploads"][-50:]

    await msg.reply_text(
        f"✅ *File received!*\n\n"
        f"📄 Name: `{filename}`\n"
        f"📦 Size: `{round((document.file_size or 0)/1024, 2)} KB`"
        f"{extracted_note}\n\n"
        f"🤖 Bot host kar diya gaya. Total hosted: *{bot_stats['hosted_bots']}*",
        parse_mode="Markdown",
    )

# ---------- Application Builder ----------
def get_bot_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    return application
